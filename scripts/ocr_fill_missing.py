# -*- coding: utf-8 -*-
"""
Fill missing pages in OCR data — process only un-OCR'd front pages.

Targets multi-station PDFs where --max-pages limited processing to 3 pages.
Reuses the existing ocr_multimodel pipeline (Gemini + Cloud Vision).

Usage:
  python scripts/ocr_fill_missing.py --province chaiyaphum
  python scripts/ocr_fill_missing.py --province chaiyaphum --dry-run
  python scripts/ocr_fill_missing.py --province chaiyaphum --models gemini
  python scripts/ocr_fill_missing.py --province chaiyaphum --limit 5
"""
import argparse
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

sys.path.insert(0, SCRIPT_DIR)
from ocr_multimodel import (
    load_api_keys, process_page, cross_validate,
)
from ocr_cloud_vision import (
    pdf_bytes_to_png, download_pdf_from_drive,
    extract_metadata_from_drive_entry, PROVINCE_SLUGS,
)
from ocr_preprocess import preprocess_png


def load_existing_ocr(slug):
    """Load existing OCR results and build a set of (file, page) already done."""
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if not os.path.exists(path):
        return [], set()
    with open(path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    done = set()
    for item in items:
        done.add((item.get('file', ''), item.get('page', 0)))
    return items, done


def load_drive_index(slug):
    """Load Drive index for province."""
    path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    if not os.path.exists(path):
        print(f"ERROR: Drive index not found: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_label_from_entry(entry):
    """Build file label (path/name) from Drive index entry."""
    p = entry.get('path', '')
    n = entry.get('name', '')
    return f"{p}/{n}" if p else n


def find_missing_pages(existing_items, drive_index):
    """Find all (entry, page_nums_to_process) for under-processed PDFs.
    
    Strategy:
    - For each PDF in drive_index, check how many pages were OCR'd
    - Each station has 2 pages: front (data) + back (signatures)
    - We only need to OCR front pages (odd page numbers: 1, 3, 5, ...)
    - Skip pages already in existing OCR data
    """
    # Build lookup: file_label -> set of pages already done
    done_pages = {}
    for item in existing_items:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages.setdefault(fl, set()).add(pg)

    # Also track total_pages from existing data
    file_total = {}
    for item in existing_items:
        fl = item.get('file', '')
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    missing = []
    total_missing_pages = 0

    for entry in drive_index:
        if not entry.get('name', '').lower().endswith('.pdf'):
            continue
        fl = file_label_from_entry(entry)
        tp = file_total.get(fl)
        done = done_pages.get(fl, set())

        if tp is None or tp <= len(done):
            # Fully processed or unknown total pages — skip
            # (we'll discover total_pages when downloading)
            if tp and tp <= 4:
                continue  # Small PDFs are likely already fully processed

        # Determine which front pages are missing
        # Front pages: 1, 3, 5, ... (1-indexed, odd)
        if tp:
            all_front_pages = set(range(1, tp + 1, 2))
        else:
            # Don't know total — will check after download
            all_front_pages = None

        pages_to_do = (all_front_pages - done) if all_front_pages else None

        if pages_to_do and len(pages_to_do) == 0:
            continue

        missing.append({
            'entry': entry,
            'file_label': fl,
            'total_pages': tp,
            'done_pages': done,
            'pages_to_do': sorted(pages_to_do) if pages_to_do else None,
        })
        if pages_to_do:
            total_missing_pages += len(pages_to_do)

    return missing, total_missing_pages


def main():
    parser = argparse.ArgumentParser(description="Fill missing OCR pages")
    parser.add_argument("--province", required=True, help="Province slug (e.g. chaiyaphum)")
    parser.add_argument("--models", default="gemini", help="Models: gemini,cloud_vision,claude")
    parser.add_argument("--limit", type=int, help="Max PDFs to process")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be processed")
    parser.add_argument("--skip-back", action="store_true", default=True,
                        help="Skip back pages (default: True)")
    args = parser.parse_args()

    slug = args.province
    # Resolve slug if Thai name given
    for prov_name, prov_slug in PROVINCE_SLUGS.items():
        if prov_slug == slug or prov_name == slug:
            slug = prov_slug
            break

    print(f"[Province] {slug}")

    # Load existing data
    existing_items, done_set = load_existing_ocr(slug)
    print(f"[Existing] {len(existing_items)} items, {len(done_set)} unique (file,page) pairs")

    # Load Drive index
    drive_index = load_drive_index(slug)
    print(f"[Drive Index] {len(drive_index)} PDFs")

    # Find missing pages
    missing, total_missing = find_missing_pages(existing_items, drive_index)
    print(f"\n[Missing] {len(missing)} PDFs with unprocessed pages")
    print(f"[Missing] ~{total_missing} front pages to OCR")

    if args.limit:
        missing = missing[:args.limit]
        print(f"[Limit] Processing first {args.limit} PDFs")

    if args.dry_run:
        print("\n=== DRY RUN — would process: ===")
        for m in missing:
            pages = m['pages_to_do'] or '(unknown until download)'
            print(f"  {m['file_label']}")
            print(f"    total_pages={m['total_pages']} done={len(m['done_pages'])} todo={pages}")
        print(f"\nTotal: {len(missing)} PDFs, ~{total_missing} pages")
        return

    # Load API keys
    keys = load_api_keys()
    models_to_use = [m.strip() for m in args.models.split(',')]

    # Check keys
    model_key_map = {
        'gemini': 'GEMINI_API_KEY',
        'cloud_vision': 'GOOGLE_CLOUD_API_KEY',
        'claude': 'ANTHROPIC_API_KEY',
    }
    active_models = []
    for m in models_to_use:
        rk = model_key_map.get(m)
        if rk and rk in keys:
            active_models.append(m)
        else:
            print(f"  WARN: Skipping {m} (no {rk})")
    models_to_use = active_models

    if not models_to_use:
        print("ERROR: No models available! Add API keys to .env")
        sys.exit(1)

    print(f"[Models] {', '.join(models_to_use)}")

    # Output file (same as existing)
    out_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    results = list(existing_items)
    new_count = 0
    api_calls = 0
    errors = 0

    for idx, m in enumerate(missing):
        entry = m['entry']
        fl = m['file_label']
        file_id = entry['file_id']
        meta = extract_metadata_from_drive_entry(entry)

        print(f"\n[{idx+1}/{len(missing)}] {fl}")

        # Download PDF
        try:
            api_key = keys.get('GOOGLE_CLOUD_API_KEY', '')
            pdf_bytes = download_pdf_from_drive(file_id, api_key)
            if not pdf_bytes:
                print("  ERR: Download failed")
                errors += 1
                continue
        except Exception as e:
            print(f"  ERR: Download error: {e}")
            errors += 1
            continue

        # Count actual pages
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            doc.close()
        except Exception:
            total_pages = m['total_pages'] or 1

        # Determine which front pages to process
        done_pages = m['done_pages']
        if args.skip_back:
            # Front pages only: 1, 3, 5, ... (1-indexed)
            all_target = list(range(1, total_pages + 1, 2))
        else:
            all_target = list(range(1, total_pages + 1))

        pages_to_do = [p for p in all_target if p not in done_pages]

        if not pages_to_do:
            print(f"  All {total_pages} pages already done — skip")
            continue

        # Adaptive DPI
        base_dpi = 200 if total_pages > 20 else 300

        print(f"  Pages: {total_pages}, already done: {len(done_pages)}, "
              f"to process: {len(pages_to_do)}, dpi: {base_dpi}")

        for page_1indexed in pages_to_do:
            page_0indexed = page_1indexed - 1

            # Check if already in results (double-check)
            if (fl, page_1indexed) in done_set:
                continue

            # Convert page to PNG
            png_bytes_page = None
            for dpi in [base_dpi, 150, 100]:
                try:
                    png_result = pdf_bytes_to_png(pdf_bytes, page_0indexed, dpi=dpi)
                    if png_result is not None and png_result[0] is not None:
                        png_bytes_page = png_result[0]
                        break
                except Exception as e:
                    if dpi == 100:
                        print(f"  p{page_1indexed}: ERR {e}")

            if png_bytes_page is None:
                print(f"  p{page_1indexed}: ERR PNG conversion failed")
                errors += 1
                continue

            # Rate limit for large PDFs
            if total_pages > 20 and page_1indexed > 1:
                time.sleep(2)

            print(f"  p{page_1indexed}:", end='')
            result = process_page(
                png_bytes_page, keys, models_to_use,
                page_0indexed, meta, fl,
                self_consistency=0
            )
            api_calls += len(models_to_use)

            if result:
                result['total_pages'] = total_pages
                result['drive_file_id'] = file_id
                result['drive_view_url'] = entry.get('view_url')
                results.append(result)
                done_set.add((fl, page_1indexed))
                new_count += 1

                station = result.get('station_no')
                voters = result.get('registered_voters')
                n_cands = len(result.get('candidates', []))
                is_back = result.get('is_back_page', False)
                print(f"    → station={station} voters={voters} "
                      f"cands={n_cands} back={is_back}")
            else:
                print(f"    → no result")
                errors += 1

            # Brief pause between pages
            time.sleep(1)

        # Save incrementally after each PDF
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved ({len(results)} total items, +{new_count} new)")

    # Final summary
    print(f"\n{'='*60}")
    print(f"=== FILL MISSING COMPLETE ===")
    print(f"{'='*60}")
    print(f"  New pages processed: {new_count}")
    print(f"  API calls: ~{api_calls}")
    print(f"  Errors: {errors}")
    print(f"  Total items now: {len(results)}")
    print(f"  Output: {out_path}")
    print(f"\n  Next step: python scripts/prepare_review_data.py")


if __name__ == '__main__':
    main()
