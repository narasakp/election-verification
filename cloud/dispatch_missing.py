# -*- coding: utf-8 -*-
"""
Dispatch MISSING pages to Cloud Function workers in parallel.

Unlike dispatch.py (which sends whole files), this script:
  1. Finds all pages not yet OCR'd in ocr_multimodel_{province}.json
  2. Only sends front pages (odd pages = station data, skips back pages)
  3. Sends one Cloud Function call per page for maximum parallelism

Usage:
  python cloud/dispatch_missing.py --province chaiyaphum --function-url <URL> --dry-run
  python cloud/dispatch_missing.py --province chaiyaphum --function-url <URL> --workers 30
  python cloud/dispatch_missing.py --province chaiyaphum --function-url <URL> --workers 30 --limit 50
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
}


def load_env():
    """Load .env file and return dict."""
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
    """Load existing OCR data. Returns (items, done_set of (file,page))."""
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
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_label_from_entry(entry):
    p = entry.get('path', '')
    n = entry.get('name', '')
    return f"{p}/{n}" if p else n


def build_missing_page_tasks(existing_items, drive_index, skip_back=True):
    """Build list of per-page tasks for all missing pages.
    
    Returns list of dicts: {file_id, file_label, page_num (0-indexed), total_pages}
    """
    # Build lookup: file_label -> set of pages already done (1-indexed)
    done_pages = defaultdict(set)
    file_total = {}
    for item in existing_items:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    # Build file_id lookup
    label_to_entry = {}
    for entry in drive_index:
        if not entry.get('name', '').lower().endswith('.pdf'):
            continue
        fl = file_label_from_entry(entry)
        label_to_entry[fl] = entry

    tasks = []
    for fl, entry in label_to_entry.items():
        tp = file_total.get(fl)
        done = done_pages.get(fl, set())

        if tp is None or tp <= 4:
            # Unknown total or small file — skip (already fully processed)
            if tp and len(done) >= tp // 2:
                continue
            if tp is None:
                continue

        # Determine which pages to process
        if skip_back:
            # Front pages only: 1, 3, 5, ... (1-indexed odd)
            all_target = set(range(1, tp + 1, 2))
        else:
            all_target = set(range(1, tp + 1))

        missing = sorted(all_target - done)
        if not missing:
            continue

        for page_1indexed in missing:
            tasks.append({
                'file_id': entry['file_id'],
                'file_label': fl,
                'page_num': page_1indexed - 1,  # Cloud Function uses 0-indexed
                'total_pages': tp,
            })

    return tasks


def send_task(function_url, file_id, file_label, province, google_api_key, page_num):
    """POST a single page OCR task to the Cloud Function."""
    payload = {
        "file_id": file_id,
        "file_label": file_label,
        "province": province,
        "google_api_key": google_api_key,
        "max_pages": 1,
        "page_num": page_num,
    }
    try:
        resp = requests.post(function_url, json=payload, timeout=600)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                    "file_id": file_id, "file_label": file_label}
        return resp.json()
    except Exception as e:
        return {"error": str(e), "file_id": file_id, "file_label": file_label}


def main():
    parser = argparse.ArgumentParser(description="Dispatch missing OCR pages to Cloud Function")
    parser.add_argument("--province", required=True, help="Province (Thai or slug)")
    parser.add_argument("--function-url", required=True,
                        help="Cloud Function URL")
    parser.add_argument("--workers", type=int, default=30,
                        help="Parallel workers (default: 30)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of page tasks (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be dispatched")
    args = parser.parse_args()

    # Resolve province slug
    slug = PROVINCE_SLUGS.get(args.province) or args.province
    for name, s in PROVINCE_SLUGS.items():
        if s == args.province:
            slug = s
            break

    # Load data
    existing, done_set = load_existing_ocr(slug)
    drive_index = load_drive_index(slug)

    print(f"[Province]  {slug}")
    print(f"[Existing]  {len(existing)} items, {len(done_set)} (file,page) pairs")
    print(f"[Drive]     {len(drive_index)} PDFs")

    # Build tasks
    tasks = build_missing_page_tasks(existing, drive_index, skip_back=True)
    print(f"[Missing]   {len(tasks)} front pages to OCR")

    # Group by file for summary
    files_with_missing = defaultdict(int)
    for t in tasks:
        files_with_missing[t['file_label']] += 1
    print(f"[Files]     {len(files_with_missing)} PDFs have missing pages")

    if args.limit > 0:
        tasks = tasks[:args.limit]
        print(f"[Limit]     Processing first {args.limit} tasks")

    if args.dry_run:
        print(f"\n=== DRY RUN — would dispatch {len(tasks)} page tasks ===")
        # Show summary per file
        by_file = defaultdict(list)
        for t in tasks:
            by_file[t['file_label']].append(t['page_num'] + 1)
        for fl, pages in sorted(by_file.items())[:20]:
            print(f"  {fl}")
            print(f"    pages: {pages}")
        if len(by_file) > 20:
            print(f"  ... and {len(by_file) - 20} more files")
        print(f"\nTotal: {len(tasks)} page tasks across {len(by_file)} PDFs")
        return

    if not tasks:
        print("Nothing to do — all pages already processed!")
        return

    # Load API keys
    env = load_env()
    google_api_key = env.get('GOOGLE_CLOUD_API_KEY', '')

    print(f"[Function]  {args.function_url}")
    print(f"[Workers]   {args.workers}")
    print(f"\nDispatching {len(tasks)} page tasks...\n")

    done_count = 0
    errors = 0
    success = 0
    start_time = time.time()
    error_log = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for task in tasks:
            f = pool.submit(
                send_task,
                args.function_url,
                task['file_id'],
                task['file_label'],
                slug,
                google_api_key,
                task['page_num'],
            )
            futures[f] = task

        for future in as_completed(futures):
            task = futures[future]
            done_count += 1
            try:
                result = future.result()
                p = task['page_num'] + 1
                label_short = task['file_label'][-60:]

                if "error" in result:
                    errors += 1
                    error_log.append({
                        "file": task['file_label'],
                        "page": p,
                        "error": result['error'][:200]
                    })
                    print(f"  X [{done_count}/{len(tasks)}] ...{label_short} p{p} -- {result['error'][:60]}")
                elif result.get('status') == 'skip':
                    print(f"  - [{done_count}/{len(tasks)}] ...{label_short} p{p} -- skip")
                else:
                    success += 1
                    pages_proc = result.get('pages_processed', '?')
                    print(f"  OK [{done_count}/{len(tasks)}] ...{label_short} p{p} -- {pages_proc} page(s)")
            except Exception as e:
                errors += 1
                print(f"  X [{done_count}/{len(tasks)}] ...{task['file_label'][-50:]} -- {e}")

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {success}/{len(tasks)}")
    print(f"  Errors:  {errors}")
    if tasks:
        print(f"  Speed:   {elapsed/len(tasks):.1f}s per page (wall clock)")
        print(f"  Throughput: {len(tasks)/elapsed*60:.0f} pages/min (with {args.workers} workers)")

    if error_log:
        err_path = os.path.join(DATA_DIR, f'dispatch_missing_errors_{slug}.json')
        with open(err_path, 'w', encoding='utf-8') as f:
            json.dump(error_log, f, ensure_ascii=False, indent=2)
        print(f"  Error log: {err_path}")

    print(f"\nNext steps:")
    print(f"  1. python cloud/collect.py --province {slug} --merge")
    print(f"  2. python scripts/prepare_review_data.py")


if __name__ == '__main__':
    main()
