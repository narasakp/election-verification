# -*- coding: utf-8 -*-
"""
Re-OCR problematic Chaiyaphum pages using the improved context-aware prompt.

Targets:
  - Records where OCR constituency != file path constituency
  - Records where candidate count != ECT expected count
  - Records with no ballot data in multi-station PDFs

Uses local PDF cache + Gemini API. Merges results back into the main JSON.

Usage:
  python scripts/reocr_problem_pages.py --dry-run        # list targets only
  python scripts/reocr_problem_pages.py --limit 10       # process 10 pages
  python scripts/reocr_problem_pages.py                   # process all cached
  python scripts/reocr_problem_pages.py --delay 3         # 3s between calls
"""
import argparse
import base64
import json
import os
import re
import sys
import time
from collections import defaultdict

import fitz  # PyMuPDF

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PDF_CACHE_DIR = os.path.join(DATA_DIR, '_pdf_cache_tmp')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'cloud'))
from ocr_local import (
    load_env, build_prompt, extract_metadata,
    pdf_bytes_to_png, _call_gemini_once,
    GEMINI_MODELS,
)


def load_ect_reference():
    path = os.path.join(DATA_DIR, 'ect_candidates_reference.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def identify_problem_pages(records, ect_ref):
    """Identify pages that need re-OCR."""
    prov_ref = ect_ref.get('ชัยภูมิ', {})

    problems = []  # list of (record_index, reason)
    seen = set()   # (file, page) dedup

    for i, r in enumerate(records):
        if r.get('is_back_page'):
            continue

        fl = r.get('file', '')
        pg = r.get('page', 0)
        key = (fl, pg)
        if key in seen:
            continue

        reasons = []

        # 1. Wrong constituency
        m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', fl)
        if m:
            file_cons = int(m.group(1))
            ocr_cons = r.get('constituency')
            if ocr_cons is not None and ocr_cons != file_cons:
                reasons.append('wrong_cons(%d->%d)' % (ocr_cons, file_cons))

        # 2. Candidate count mismatch (แบ่งเขต only)
        if r.get('vote_type') == 'แบ่งเขต' or 'แบ่งเขต' in fl:
            if m:
                cons = m.group(1)
                if cons in prov_ref:
                    ect_count = len(prov_ref[cons])
                    ocr_count = len(r.get('candidates', []))
                    if ocr_count != ect_count and ocr_count > 0:
                        reasons.append('cand_count(%d!=%d)' % (ocr_count, ect_count))

        # 3. No ballot data but has candidates (multi-station bleed)
        if (r.get('valid_ballots') is None and
                r.get('ballots_received') is None and
                r.get('candidates') and
                (r.get('total_pages') or 0) > 4):
            reasons.append('no_ballot_data')

        if reasons:
            seen.add(key)
            problems.append({
                'index': i,
                'file': fl,
                'page': pg,
                'page_0idx': pg - 1,  # 0-indexed for PDF
                'drive_file_id': r.get('drive_file_id', ''),
                'total_pages': r.get('total_pages', 0),
                'reasons': reasons,
            })

    return problems


def ocr_single_page(pdf_bytes, page_num, total_pages, meta, gemini_key):
    """OCR a single page with the new context-aware prompt."""
    # Convert to PNG
    png_bytes = None
    for dpi in [150, 100]:
        try:
            result = pdf_bytes_to_png(pdf_bytes, page_num, dpi=dpi)
            if result and result[0]:
                png_bytes = result[0]
                break
        except Exception:
            continue

    if not png_bytes:
        return None

    # Build prompt with context
    prompt = build_prompt(meta=meta, page_num=page_num, total_pages=total_pages)

    # OCR with multi-model fallback
    b64 = base64.b64encode(png_bytes).decode('utf-8')
    for cycle in range(3):
        if cycle > 0:
            time.sleep(10 * cycle)
        for model in GEMINI_MODELS:
            result = _call_gemini_once(b64, gemini_key, model, prompt=prompt)
            if result == 'retry':
                continue
            if result is not None:
                return result
    return None


def main():
    parser = argparse.ArgumentParser(description="Re-OCR problem pages")
    parser.add_argument('--dry-run', action='store_true', help='List targets only')
    parser.add_argument('--limit', type=int, default=0, help='Max pages to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between API calls')
    parser.add_argument('--include-no-ballot', action='store_true',
                        help='Also re-OCR no_ballot_data pages (slow, usually not needed)')
    args = parser.parse_args()

    # Load data
    src = os.path.join(DATA_DIR, 'backup_chaiyaphum_pre_postprocess.json')
    with open(src, encoding='utf-8') as f:
        records = json.load(f)
    print("Loaded %d records from backup" % len(records))

    ect_ref = load_ect_reference()
    problems = identify_problem_pages(records, ect_ref)
    print("Identified %d problem pages (all types)" % len(problems))

    # Filter out no_ballot_data unless explicitly included
    if not args.include_no_ballot:
        before = len(problems)
        problems = [p for p in problems if not all(
            r == 'no_ballot_data' for r in p['reasons']
        )]
        skipped_nb = before - len(problems)
        if skipped_nb:
            print("  Skipped %d no_ballot_data-only pages (use --include-no-ballot)" % skipped_nb)
    print("Targeted: %d pages" % len(problems))

    # Check cache
    cached_fids = set()
    if os.path.exists(PDF_CACHE_DIR):
        for f in os.listdir(PDF_CACHE_DIR):
            if f.endswith('.pdf'):
                cached_fids.add(f[:-4])

    # Filter to cached only
    cached_problems = [p for p in problems if p['drive_file_id'] in cached_fids]
    uncached = len(problems) - len(cached_problems)
    print("  With local cache: %d" % len(cached_problems))
    print("  Without cache (skipped): %d" % uncached)

    if args.dry_run:
        # Show summary by reason
        reason_counts = defaultdict(int)
        for p in problems:
            for r in p['reasons']:
                reason_counts[r.split('(')[0]] += 1
        print("\nProblem breakdown:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print("  %s: %d" % (reason, count))

        # Show per-file summary
        file_counts = defaultdict(int)
        for p in cached_problems:
            file_counts[p['drive_file_id']] += 1
        print("\nTop files by problem page count:")
        for fid, count in sorted(file_counts.items(), key=lambda x: -x[1])[:10]:
            fl = next((p['file'] for p in cached_problems if p['drive_file_id'] == fid), '')
            print("  %d pages: ...%s" % (count, fl[-60:]))
        return

    # Load API key
    env = load_env()
    gemini_key = env.get('GEMINI_API_KEY', '')
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY not found in .env")
        sys.exit(1)

    tasks = cached_problems
    if args.limit > 0:
        tasks = tasks[:args.limit]
    print("\nProcessing %d pages (delay=%.1fs)" % (len(tasks), args.delay))

    # Group by file_id for efficiency (load PDF once per file)
    by_fid = defaultdict(list)
    for t in tasks:
        by_fid[t['drive_file_id']].append(t)

    success = 0
    failed = 0
    results = []  # (record_index, new_record)
    start = time.time()

    file_num = 0
    for fid, file_tasks in by_fid.items():
        file_num += 1
        fl = file_tasks[0]['file']
        total_pages = file_tasks[0].get('total_pages', 0)

        # Load PDF
        pdf_path = os.path.join(PDF_CACHE_DIR, '%s.pdf' % fid)
        if not os.path.exists(pdf_path):
            print("  [%d/%d] SKIP (no PDF): ...%s" % (file_num, len(by_fid), fl[-50:]))
            failed += len(file_tasks)
            continue

        pdf_bytes = open(pdf_path, 'rb').read()
        meta = extract_metadata(fl)

        for t in file_tasks:
            pg = t['page_0idx']
            reasons = ', '.join(t['reasons'])
            label = '...%s p%d' % (fl[-45:], t['page'])
            print("  [%d/%d] %s (%s)" % (
                success + failed + 1, len(tasks), label, reasons), end='', flush=True)

            ocr_result = ocr_single_page(pdf_bytes, pg, total_pages, meta, gemini_key)
            if not ocr_result:
                print(" -> FAILED")
                failed += 1
                continue

            # Build output record
            record = ocr_result.get('result', {})
            # Always override with file metadata
            if meta.get('province'):
                record['province'] = meta['province']
            if meta.get('constituency'):
                record['constituency'] = meta['constituency']
            if meta.get('vote_type'):
                record['vote_type'] = meta['vote_type']

            new_record = {
                'file': fl,
                'page': t['page'],
                'total_pages': total_pages,
                'drive_file_id': fid,
                'model': ocr_result.get('model'),
                'model_variant': ocr_result.get('model_variant'),
                '_reocr': True,
                '_reocr_reasons': t['reasons'],
                **record,
            }

            results.append((t['index'], new_record))
            success += 1
            print(" -> OK (%s)" % ocr_result.get('model_variant', '?')[:20])

            # Delay between calls
            if success + failed < len(tasks):
                time.sleep(args.delay)

    elapsed = time.time() - start
    print("\n" + "=" * 50)
    print("DONE in %.0fs (%.1f min)" % (elapsed, elapsed / 60))
    print("  Success: %d/%d" % (success, len(tasks)))
    print("  Failed:  %d" % failed)

    if not results:
        print("No results to merge.")
        return

    # Merge results back into records
    for idx, new_rec in results:
        old = records[idx]
        new_rec['_reocr_old'] = {
            'constituency': old.get('constituency'),
            'candidates_count': len(old.get('candidates', [])),
            'valid_ballots': old.get('valid_ballots'),
            'total_votes': old.get('total_votes'),
        }
        records[idx] = new_rec

    # Save merged result
    out_path = os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print("  Saved merged data: %s (%d records, %d re-OCR'd)" % (
        os.path.basename(out_path), len(records), len(results)))

    print("\nNext: python scripts/postprocess_chaiyaphum.py")


if __name__ == '__main__':
    main()
