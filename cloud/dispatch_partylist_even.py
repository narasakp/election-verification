# -*- coding: utf-8 -*-
"""
Dispatch missing EVEN pages for บัญชีรายชื่อ multi-station PDFs to Cloud Function.

Problem: OCR pipeline only processed odd pages. For บัญชีรายชื่อ forms,
each station has 3 data pages + 1 back page (4pp/station). The even-numbered
data pages (p=6,10,14,...) were never OCR'd, causing n=23/24 instead of n=57.

This script:
  1. Finds all multi-station บัญชีรายชื่อ files (total_pages > 4)
  2. Identifies even pages that are missing from OCR data
  3. Also re-OCRs "back" pages with 0 candidates that may actually be data pages
  4. Dispatches to Cloud Function
  5. Results collected via cloud/collect.py --province X --merge

Usage:
  python cloud/dispatch_partylist_even.py --province chaiyaphum --dry-run
  python cloud/dispatch_partylist_even.py --province chaiyaphum --workers 20
  python cloud/dispatch_partylist_even.py --province all --dry-run
"""
import argparse
import json
import os
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

PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
}
ALL_SLUGS = ['chaiyaphum', 'tak', 'phetchabun']


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


def load_existing_ocr(slug):
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
    path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_label_from_entry(entry):
    p = entry.get('path', '')
    n = entry.get('name', '')
    return f"{p}/{n}" if p else n


def build_partylist_even_tasks(existing_items, drive_index):
    """Find missing even pages for บัญชีรายชื่อ multi-station files.

    Returns list of tasks: {file_id, file_label, page_num (0-indexed), total_pages}
    """
    # Build lookup from existing OCR
    done_pages = defaultdict(set)
    file_total = {}
    file_has_party = set()

    for item in existing_items:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp
        # Check if file contains บัญชีรายชื่อ data
        vt = item.get('vote_type') or ''
        fname = item.get('file') or ''
        if 'บัญชีรายชื่อ' in vt or 'บัญชีรายชื่อ' in fname:
            file_has_party.add(fl)

    # Build file_id lookup from drive index
    label_to_entry = {}
    for entry in drive_index:
        if not entry.get('name', '').lower().endswith('.pdf'):
            continue
        fl = file_label_from_entry(entry)
        label_to_entry[fl] = entry

    tasks = []
    files_targeted = 0

    for fl, entry in label_to_entry.items():
        tp = file_total.get(fl)
        done = done_pages.get(fl, set())

        # Only target multi-station บัญชีรายชื่อ files
        if tp is None or tp <= 4:
            continue
        if fl not in file_has_party:
            continue

        files_targeted += 1

        # Target even pages that are missing (these are the middle data pages)
        # For a 4pp/station layout: pages 2,6,10,14,... are middle data pages
        # Also target pages that exist but have 0 candidates (misclassified back pages)
        n_stations = tp // 4
        for stn_idx in range(n_stations):
            base = stn_idx * 4  # 0-indexed station start
            # Middle data page is the 2nd page of each station (0-indexed: base+1)
            middle_page_1idx = base + 2  # 1-indexed
            if middle_page_1idx <= tp and middle_page_1idx not in done:
                tasks.append({
                    'file_id': entry['file_id'],
                    'file_label': fl,
                    'page_num': middle_page_1idx - 1,  # 0-indexed for Cloud Function
                    'page_1idx': middle_page_1idx,
                    'total_pages': tp,
                    'station': stn_idx + 1,
                })

            # Also check: first page of station (base+1) might be marked back with 0 cands
            first_page_1idx = base + 1
            if first_page_1idx <= tp and first_page_1idx in done:
                # Check if it has 0 candidates (potential misclassified back page)
                for item in existing_items:
                    if item.get('file') == fl and item.get('page') == first_page_1idx:
                        if item.get('is_back_page') and len(item.get('candidates', [])) == 0:
                            # Re-OCR this page — it might be a data page
                            tasks.append({
                                'file_id': entry['file_id'],
                                'file_label': fl,
                                'page_num': first_page_1idx - 1,
                                'page_1idx': first_page_1idx,
                                'total_pages': tp,
                                'station': stn_idx + 1,
                                '_reocr_back': True,
                            })
                        break

    return tasks, files_targeted


def send_task(file_id, file_label, province, google_api_key, page_num):
    payload = {
        "file_id": file_id,
        "file_label": file_label,
        "province": province,
        "google_api_key": google_api_key,
        "max_pages": 1,
        "page_num": page_num,
    }
    try:
        resp = requests.post(FUNCTION_URL, json=payload, timeout=600)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                    "file_id": file_id, "page_num": page_num}
        return resp.json()
    except Exception as e:
        return {"error": str(e), "file_id": file_id, "page_num": page_num}


def run_province(slug, args, google_api_key):
    """Run dispatch for one province."""
    existing, done_set = load_existing_ocr(slug)
    drive_index = load_drive_index(slug)

    print(f"\n{'='*60}")
    print(f"[Province]  {slug}")
    print(f"[Existing]  {len(existing)} items, {len(done_set)} (file,page) pairs")
    print(f"[Drive]     {len(drive_index)} PDFs")

    tasks, files_targeted = build_partylist_even_tasks(existing, drive_index)
    reocr_back = sum(1 for t in tasks if t.get('_reocr_back'))
    new_pages = len(tasks) - reocr_back

    print(f"[Target]    {files_targeted} บัญชีรายชื่อ multi-station files")
    print(f"[Tasks]     {len(tasks)} pages ({new_pages} new + {reocr_back} re-OCR back)")

    if args.limit > 0:
        tasks = tasks[:args.limit]
        print(f"[Limit]     Processing first {args.limit} tasks")

    if args.dry_run:
        by_file = defaultdict(list)
        for t in tasks:
            by_file[t['file_label']].append(t['page_1idx'])
        print(f"\n  Would dispatch {len(tasks)} pages across {len(by_file)} files:")
        for fl, pages in sorted(by_file.items())[:10]:
            print(f"    ...{fl[-65:]}")
            print(f"      pages: {sorted(pages)}")
        if len(by_file) > 10:
            print(f"    ... and {len(by_file) - 10} more files")
        return len(tasks)

    if not tasks:
        print("  Nothing to dispatch!")
        return 0

    # Dispatch
    print(f"\n  Dispatching {len(tasks)} tasks with {args.workers} workers...")
    start = time.time()
    ok = 0
    errors = 0
    error_log = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(send_task, t['file_id'], t['file_label'],
                        slug, google_api_key, t['page_num']): t
            for t in tasks
        }
        for i, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            result = fut.result()
            p = t['page_num'] + 1
            label_short = t['file_label'][-55:]

            if "error" in result:
                errors += 1
                error_log.append({
                    "file": t['file_label'], "page": p,
                    "error": result['error'][:200]
                })
                if errors <= 5:
                    print(f"  X [{i}/{len(tasks)}] ...{label_short} p{p} -- {result['error'][:60]}")
            else:
                ok += 1

            if i % 50 == 0 or i == len(tasks):
                elapsed = time.time() - start
                rate = i / elapsed * 60
                print(f"  [{i}/{len(tasks)}] ok={ok} err={errors} rate={rate:.0f}/min")

    elapsed = time.time() - start
    print(f"\n  Done in {elapsed/60:.1f} min — ok={ok} errors={errors}")

    if error_log:
        err_path = os.path.join(DATA_DIR, f'dispatch_partylist_even_errors_{slug}.json')
        with open(err_path, 'w', encoding='utf-8') as f:
            json.dump(error_log, f, ensure_ascii=False, indent=2)
        print(f"  Error log: {err_path}")

    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Dispatch missing even pages for บัญชีรายชื่อ multi-station PDFs")
    parser.add_argument("--province", default="all",
                        help="Province slug or 'all' (default: all)")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = load_env()
    google_api_key = env.get('GOOGLE_CLOUD_API_KEY', '')
    if not google_api_key and not args.dry_run:
        print("ERROR: GOOGLE_CLOUD_API_KEY not found in .env")
        sys.exit(1)

    slugs = ALL_SLUGS if args.province == 'all' else [
        PROVINCE_SLUGS.get(args.province, args.province)]

    total_tasks = 0
    for slug in slugs:
        total_tasks += run_province(slug, args, google_api_key)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_tasks} page tasks across {len(slugs)} provinces")
    if not args.dry_run and total_tasks > 0:
        print(f"\nNext steps:")
        for slug in slugs:
            print(f"  python cloud/collect.py --province {slug} --merge")
        print(f"  python scripts/prepare_review_data.py")


if __name__ == '__main__':
    main()
