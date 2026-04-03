#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dispatch re-OCR for 115 vision-only multi-station PDFs via Cloud Function.

These PDFs were OCR'd by Cloud Vision but only page 1 was processed.
We need to OCR ALL front pages via the multimodel pipeline.

Workflow:
  1. Identify 115 vision-only multi-station files from review_data.json
  2. Match to Drive index entries (file_id needed for Cloud Function)
  3. Dispatch all front pages to Cloud Function
  4. Collect results from GCS
  5. Merge into ocr_multimodel_{province}.json

Usage:
  python cloud/_dispatch_reocr_vision_multistation.py --dry-run
  python cloud/_dispatch_reocr_vision_multistation.py --workers 20
  python cloud/_dispatch_reocr_vision_multistation.py --collect-only
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

FUNCTION_URL = 'https://asia-southeast1-election-ocr.cloudfunctions.net/ocr-worker'
GCS_BUCKET = 'election69-ocr-results-th'

OCR_FILES = {
    'chaiyaphum': os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'),
    'tak':        os.path.join(DATA_DIR, 'ocr_multimodel_tak.json'),
    'phetchabun': os.path.join(DATA_DIR, 'ocr_multimodel_phetchabun.json'),
}

PROVINCE_SLUG_MAP = {
    'ชัยภูมิ': 'chaiyaphum',
    'ตาก': 'tak',
    'เพชรบูรณ์': 'phetchabun',
}


def load_env():
    env = {}
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def identify_vision_multistation_files():
    """Find vision-only multi-station files from review_data.json."""
    review_path = os.path.join(PROJECT_ROOT, 'review-app', 'public', 'data', 'review_data.json')
    review = json.load(open(review_path, encoding='utf-8'))

    # Find แบ่งเขต items from vision source with total_pages > 4 and only 1 item per file
    vision_multi = [r for r in review
                    if r.get('_source_type') == 'vision'
                    and r.get('vote_type') in ('แบ่งเขต', 'บัญชีรายชื่อ')
                    and (r.get('total_pages') or 0) > 4]

    # Group by file — only keep files with few review items relative to expected
    by_file = defaultdict(list)
    for r in vision_multi:
        by_file[r.get('file', '')].append(r)

    targets = []
    for f, recs in by_file.items():
        tp = max(r.get('total_pages', 0) or 0 for r in recs)
        vt = recs[0].get('vote_type', '')
        pps = 2 if 'แบ่งเขต' in vt else 4  # pages per station
        expected = tp // pps
        if len(recs) < expected:
            # Extract province from file path
            prov = recs[0].get('province', '')
            cons_match = re.search(r'เขตเลือกตั้งที่\s*(\d+)', f)
            cons = int(cons_match.group(1)) if cons_match else None
            targets.append({
                'file': f,
                'province': prov,
                'province_slug': PROVINCE_SLUG_MAP.get(prov, ''),
                'constituency': cons,
                'vote_type': vt,
                'total_pages': tp,
                'existing_pages': sorted(r.get('page') for r in recs if r.get('page')),
                'expected_stations': expected,
                'existing_items': len(recs),
            })

    return targets


def match_drive_index(targets):
    """Match vision files to Drive index entries by content similarity."""
    # Load all drive indexes
    drive_indexes = {}
    for slug in ['chaiyaphum', 'tak', 'phetchabun']:
        path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
        if os.path.exists(path):
            drive_indexes[slug] = json.load(open(path, encoding='utf-8'))

    # Build lookup: normalize subdistrict name → drive entries
    drive_lookup = {}  # (slug, cons, subdistrict_norm, vote_type_norm) → entry
    for slug, entries in drive_indexes.items():
        for entry in entries:
            name = entry.get('name', '')
            path = entry.get('path', '')
            # Extract subdistrict + vote type from path or name
            # Drive paths: จังหวัดX/เขตเลือกตั้งที่ Y/อำเภอ.../ตำบล.../...
            file_label = f"{path}/{name}" if path else name
            drive_lookup_key = file_label.lower()
            drive_lookup[drive_lookup_key] = entry

    matched = []
    unmatched = []

    for t in targets:
        slug = t['province_slug']
        if slug not in drive_indexes:
            unmatched.append(t)
            continue

        # Try to find matching Drive entry
        # Vision file: เขตเลือกตั้งที่ 1\อำเภอเมืองชัยภูมิ\โคกสูง-001-แบ่งเขต.PDF
        # Drive file: จังหวัดชัยภูมิ/เขตเลือกตั้งที่ 1/อำเภอ.../แบ่งเขต/ต.XXX-แบ่งเขต-หน่วยที่ 1-N.pdf
        #
        # Match strategy: find Drive entries with same constituency, similar subdistrict,
        # and similar total_pages
        cons = t['constituency']
        vt = t['vote_type']
        tp = t['total_pages']

        # Extract subdistrict from vision filename
        vfile = t['file']
        # Pattern: อำเภอX\ตำบลY-NNN-แบ่งเขต.PDF or อำเภอX\Y-NNN-แบ่งเขต.PDF
        parts = vfile.replace('\\', '/').split('/')
        subdistrict_part = ''
        for p in parts:
            if re.match(r'.+-\d+-', p):
                subdistrict_part = re.sub(r'-\d+-.*', '', p)
                break

        best_match = None
        best_score = 0

        for entry in drive_indexes[slug]:
            name = entry.get('name', '')
            epath = entry.get('path', '')
            file_label = f"{epath}/{name}" if epath else name

            # Must be same constituency
            econs_m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', file_label)
            if not econs_m or int(econs_m.group(1)) != cons:
                continue

            # Must be same vote type
            if vt == 'แบ่งเขต' and 'แบ่งเขต' not in file_label:
                continue
            if vt == 'บัญชีรายชื่อ' and 'บัญชีรายชื่อ' not in file_label:
                continue

            # Must be PDF
            if not name.lower().endswith('.pdf'):
                continue

            # Check total_pages match (from existing OCR)
            etp = entry.get('total_pages', 0)

            # Score: subdistrict name similarity
            score = 0
            if subdistrict_part and subdistrict_part in file_label:
                score += 100
            elif subdistrict_part:
                # Try partial match
                for char_count in range(min(4, len(subdistrict_part)), 0, -1):
                    if subdistrict_part[:char_count] in file_label:
                        score += char_count * 10
                        break

            # Prefer matching total_pages
            if etp == tp:
                score += 50
            elif etp and abs(etp - tp) <= 2:
                score += 20

            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score >= 50:
            t['drive_entry'] = best_match
            t['drive_file_id'] = best_match['file_id']
            t['drive_file_label'] = f"{best_match.get('path','')}/{best_match['name']}"
            t['match_score'] = best_score
            matched.append(t)
        else:
            unmatched.append(t)

    return matched, unmatched


def build_page_tasks(matched_targets):
    """Build per-page dispatch tasks for all matched targets."""
    tasks = []
    for t in matched_targets:
        tp = t['total_pages']
        existing = set(t['existing_pages'])

        # Determine pages to OCR: all front pages (odd, 1-indexed)
        vt = t['vote_type']
        if 'แบ่งเขต' in vt:
            # Front pages: 1, 3, 5, ... 
            target_pages = list(range(1, tp + 1, 2))
        elif 'บัญชีรายชื่อ' in vt:
            # For party list: pages 1,2,3, 5,6,7, 9,10,11, ...
            target_pages = [p for p in range(1, tp + 1) if (p - 1) % 4 != 3]
        else:
            target_pages = list(range(1, tp + 1, 2))

        for page_1idx in target_pages:
            tasks.append({
                'file_id': t['drive_file_id'],
                'file_label': t['drive_file_label'],
                'province_slug': t['province_slug'],
                'page_0idx': page_1idx - 1,
                'page_1idx': page_1idx,
                'total_pages': tp,
                'vision_file': t['file'],
            })

    return tasks


def send_task(fid, file_label, prov_key, page_0idx, google_api_key, dry_run=False):
    """Send one page to Cloud Function."""
    if dry_run:
        return (fid, page_0idx, 'dry_run', None)
    payload = {
        'file_id': fid,
        'file_label': file_label,
        'province': prov_key,
        'google_api_key': google_api_key,
        'max_pages': 1,
        'page_num': page_0idx,
    }
    try:
        resp = requests.post(FUNCTION_URL, json=payload, timeout=600)
        d = resp.json()
        if resp.status_code == 200 and d.get('status') == 'ok':
            pages = d.get('pages_processed', 0)
            blob = d.get('blob_path', '')
            return (fid, page_0idx, 'ok' if pages > 0 else 'empty', blob)
        else:
            return (fid, page_0idx, f'http_{resp.status_code}', None)
    except Exception as e:
        return (fid, page_0idx, f'err:{e}', None)


def download_gcs_blob(gcs_bucket, blob_path):
    try:
        blob = gcs_bucket.blob(blob_path)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    except Exception as e:
        print(f'  GCS err {blob_path}: {e}')
        return None


def main():
    parser = argparse.ArgumentParser(description="Re-OCR vision multi-station PDFs via Cloud Function")
    parser.add_argument('--workers', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    env = load_env()
    google_api_key = env.get('GOOGLE_CLOUD_API_KEY', '')
    if not google_api_key and not args.dry_run and not args.collect_only:
        print("ERROR: GOOGLE_CLOUD_API_KEY not found in .env")
        sys.exit(1)

    # ── Step 1: Identify targets ──────────────────────────────────────
    print("Step 1: Identifying vision-only multi-station files...")
    targets = identify_vision_multistation_files()
    print(f"  Found {len(targets)} vision multi-station files")

    by_prov = defaultdict(int)
    total_pages_needed = 0
    for t in targets:
        by_prov[t['province']] += 1
        total_pages_needed += t['expected_stations']
    for p, c in sorted(by_prov.items()):
        print(f"    {p}: {c} files")
    print(f"  Total expected stations: {total_pages_needed}")

    # ── Step 2: Match to Drive index ──────────────────────────────────
    print("\nStep 2: Matching to Drive index...")
    matched, unmatched = match_drive_index(targets)
    print(f"  Matched: {len(matched)} files")
    print(f"  Unmatched: {len(unmatched)} files")

    if unmatched:
        print(f"\n  ⚠️  Unmatched files (no Drive entry found):")
        for t in unmatched[:10]:
            print(f"    {t['file'][-70:]}")
        if len(unmatched) > 10:
            print(f"    ... and {len(unmatched) - 10} more")

    # Save targets for reference
    targets_path = os.path.join(DATA_DIR, '_reocr_vision_multistation_targets.json')
    with open(targets_path, 'w', encoding='utf-8') as f:
        json.dump({'matched': matched, 'unmatched': [
            {k: v for k, v in t.items() if k != 'drive_entry'} for t in unmatched
        ]}, f, ensure_ascii=False, indent=2)
    print(f"  Saved targets to {os.path.basename(targets_path)}")

    # ── Step 3: Build page tasks ──────────────────────────────────────
    print("\nStep 3: Building page tasks...")
    tasks = build_page_tasks(matched)
    print(f"  Total page tasks: {len(tasks)}")
    by_prov_tasks = defaultdict(int)
    for t in tasks:
        by_prov_tasks[t['province_slug']] += 1
    for p, c in sorted(by_prov_tasks.items()):
        print(f"    {p}: {c} pages")

    if args.limit:
        tasks = tasks[:args.limit]
        print(f"  Limited to {args.limit} tasks")

    if args.dry_run:
        print(f"\n=== DRY RUN — would dispatch {len(tasks)} page tasks ===")
        by_file = defaultdict(list)
        for t in tasks:
            by_file[t['file_label']].append(t['page_1idx'])
        for fl, pages in sorted(by_file.items())[:15]:
            print(f"  {fl[-80:]}")
            print(f"    pages: {pages}")
        if len(by_file) > 15:
            print(f"  ... and {len(by_file) - 15} more files")
        return

    # ── Step 4: Dispatch ──────────────────────────────────────────────
    blob_map = {}  # (fid, page_0idx) -> blob_path
    ok_count = 0
    empty_count = 0
    fail_count = 0

    if not args.collect_only:
        print(f"\nStep 4: Dispatching {len(tasks)} tasks with {args.workers} workers...")
        start = time.time()

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(send_task,
                            t['file_id'], t['file_label'], t['province_slug'],
                            t['page_0idx'], google_api_key): t
                for t in tasks
            }
            for i, fut in enumerate(as_completed(futs), 1):
                t = futs[fut]
                fid, page_0idx, status, blob = fut.result()
                if status == 'ok':
                    ok_count += 1
                    blob_map[(fid, page_0idx)] = blob
                elif status == 'empty':
                    empty_count += 1
                    if blob:
                        blob_map[(fid, page_0idx)] = blob
                else:
                    fail_count += 1
                    if i <= 5 or fail_count <= 3:
                        print(f'  FAIL: {status} — {t["file_label"][-60:]} p{page_0idx}')

                if i % 50 == 0 or i == len(tasks):
                    elapsed = time.time() - start
                    rate = i / elapsed * 60
                    print(f'  [{i}/{len(tasks)}] ok={ok_count} empty={empty_count} '
                          f'fail={fail_count} rate={rate:.0f}/min')

        elapsed = time.time() - start
        print(f'\nDispatch done in {elapsed/60:.1f} min')
        print(f'ok={ok_count} empty={empty_count} fail={fail_count}')
    else:
        # Collect-only: build blob map from expected paths
        print("Step 4: Collect-only mode — building expected blob paths...")
        for t in tasks:
            fid = t['file_id']
            page_0idx = t['page_0idx']
            prov = t['province_slug']
            blob_map[(fid, page_0idx)] = f"{prov}/{fid}_p{page_0idx}.json"
        print(f'  Expected blobs: {len(blob_map)}')

    # ── Step 5: Collect from GCS & Add to OCR files ───────────────────
    print(f'\nStep 5: Collecting {len(blob_map)} blobs from GCS...')
    from google.cloud import storage as gcs_storage
    _gcs_client = gcs_storage.Client()
    _gcs_bucket = _gcs_client.bucket(GCS_BUCKET)

    # Load existing OCR data
    ocr_data = {}
    for slug, path in OCR_FILES.items():
        if os.path.exists(path):
            ocr_data[slug] = json.load(open(path, encoding='utf-8'))
        else:
            ocr_data[slug] = []

    # Track existing (file, page) to avoid duplicates
    existing_keys = {}
    for slug, records in ocr_data.items():
        for r in records:
            existing_keys[(slug, r.get('file', ''), r.get('page', 0))] = True

    added = 0
    no_data = 0
    skipped = 0
    collected = 0

    for (fid, page_0idx), blob_path in sorted(blob_map.items()):
        if not blob_path:
            continue
        collected += 1
        if collected % 100 == 0:
            print(f'  collect [{collected}/{len(blob_map)}] added={added}')

        gcs_data = download_gcs_blob(_gcs_bucket, blob_path)
        if not gcs_data:
            no_data += 1
            continue

        # GCS data is list or single record
        if isinstance(gcs_data, list):
            page_records = gcs_data
        else:
            page_records = [gcs_data]

        for rec in page_records:
            prov = rec.get('province', '')
            slug = PROVINCE_SLUG_MAP.get(prov, '')
            if not slug:
                # Try to determine from blob path
                for s in ['chaiyaphum', 'tak', 'phetchabun']:
                    if s in blob_path:
                        slug = s
                        break
            if not slug:
                continue

            fl = rec.get('file', '')
            pg = rec.get('page', 0)

            # Skip if already exists
            if (slug, fl, pg) in existing_keys:
                skipped += 1
                continue

            rec['_reocr_vision_multistation'] = True
            ocr_data[slug].append(rec)
            existing_keys[(slug, fl, pg)] = True
            added += 1

    print(f'\nCollect results: added={added} no_data={no_data} skipped={skipped}')

    # ── Step 6: Save ──────────────────────────────────────────────────
    if added > 0:
        for slug in ocr_data:
            n_new = sum(1 for r in ocr_data[slug] if r.get('_reocr_vision_multistation'))
            if n_new == 0:
                continue
            path = OCR_FILES[slug]
            backup = path + '.pre_reocr_vision'
            if not os.path.exists(backup):
                shutil.copy2(path, backup)
                print(f'  Backup: {os.path.basename(backup)}')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ocr_data[slug], f, ensure_ascii=False, indent=2)
            print(f'  Saved {slug}: +{n_new} new records (total {len(ocr_data[slug])})')
    else:
        print('No new records — OCR files unchanged')

    print('\nDone!')


if __name__ == '__main__':
    main()
