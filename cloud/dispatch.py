# -*- coding: utf-8 -*-
"""
Dispatch OCR tasks to Cloud Function workers in parallel.

Usage:
  python cloud/dispatch.py --province tak --workers 20
  python cloud/dispatch.py --province phetchabun --workers 30 --dry-run

Reads drive_index_{province}.json, skips already-done files,
sends concurrent HTTP POST requests to the Cloud Function.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Province name → slug mapping
PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
}

# ── Load API keys from .env ───────────────────────────────────────────

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


# ── Send one task to Cloud Function ───────────────────────────────────

def send_task(function_url, file_id, file_label, province, google_api_key,
              max_pages=4, page_num=None):
    """POST a single OCR task to the Cloud Function. Returns response dict."""
    payload = {
        "file_id": file_id,
        "file_label": file_label,
        "province": province,
        "google_api_key": google_api_key,
        "max_pages": max_pages,
    }
    if page_num is not None:
        payload["page_num"] = page_num
    try:
        resp = requests.post(function_url, json=payload, timeout=600)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "file_id": file_id, "file_label": file_label}


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dispatch OCR tasks to Cloud Function")
    parser.add_argument("--province", required=True, help="Province (Thai or slug)")
    parser.add_argument("--function-url", required=True,
                        help="Cloud Function URL (from deploy output)")
    parser.add_argument("--workers", type=int, default=20,
                        help="Number of parallel workers (default: 20)")
    parser.add_argument("--max-pages", type=int, default=4,
                        help="Max pages per PDF to process (default: 4)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of files to dispatch (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be dispatched without running")
    parser.add_argument("--retry-split", action="store_true",
                        help="Retry failed files with per-page split (1 page per task)")
    args = parser.parse_args()

    # Resolve province
    province = args.province
    slug = PROVINCE_SLUGS.get(province) or province
    for name, s in PROVINCE_SLUGS.items():
        if s == province:
            slug = s
            break

    # Load drive index
    idx_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    if not os.path.exists(idx_path):
        print(f"ERROR: {idx_path} not found")
        sys.exit(1)
    with open(idx_path, 'r', encoding='utf-8') as f:
        drive_index = json.load(f)

    # Load existing results to skip done files
    ocr_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    done_files = set()
    if os.path.exists(ocr_path):
        with open(ocr_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        done_files = set(r.get('file') for r in existing)
        print(f"[Resume] {len(done_files)} files already done")

    # Build task list
    tasks = []
    if args.retry_split:
        # Read error log and create per-page tasks for failed files
        err_path = os.path.join(DATA_DIR, f'dispatch_errors_{slug}.json')
        if not os.path.exists(err_path):
            print(f"ERROR: No error log found at {err_path}")
            sys.exit(1)
        with open(err_path, 'r', encoding='utf-8') as f:
            error_log = json.load(f)
        # Build file_id lookup from drive index
        label_to_id = {}
        for entry in drive_index:
            p = entry.get('path', '')
            n = entry.get('name', '')
            label = f"{p}/{n}" if p else n
            label_to_id[label] = entry['file_id']
        # Create per-page tasks (pages 0-3) for each failed file
        seen = set()
        for err in error_log:
            label = err.get('file', '')
            fid = label_to_id.get(label)
            if not fid or label in seen:
                continue
            seen.add(label)
            for pg in range(args.max_pages):
                tasks.append({
                    "file_id": fid,
                    "file_label": label,
                    "page_num": pg,
                })
        print(f"[Retry-Split] {len(seen)} failed files → {len(tasks)} page tasks")
    else:
        for entry in drive_index:
            if not entry.get('name', '').lower().endswith('.pdf'):
                continue
            p = entry.get('path', '')
            n = entry.get('name', '')
            label = f"{p}/{n}" if p else n
            if label in done_files:
                continue
            tasks.append({
                "file_id": entry['file_id'],
                "file_label": label,
            })

    if args.limit > 0:
        tasks = tasks[:args.limit]

    print(f"[Province] {slug}")
    print(f"[Tasks] {len(tasks)} files to process")
    print(f"[Workers] {args.workers} parallel")
    print(f"[Function] {args.function_url}")

    if args.dry_run:
        print("\n[DRY RUN] Would dispatch:")
        for t in tasks[:10]:
            print(f"  {t['file_label']}")
        if len(tasks) > 10:
            print(f"  ... and {len(tasks)-10} more")
        return

    if not tasks:
        print("Nothing to do!")
        return

    # Load API keys
    env = load_env()
    google_api_key = env.get('GOOGLE_CLOUD_API_KEY', '')

    # Dispatch in parallel
    print(f"\nDispatching {len(tasks)} tasks...\n")
    done = 0
    errors = 0
    start_time = time.time()
    error_log = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for task in tasks:
            f = pool.submit(
                send_task,
                args.function_url,
                task["file_id"],
                task["file_label"],
                slug,
                google_api_key,
                args.max_pages,
                task.get("page_num"),
            )
            futures[f] = task

        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
                done += 1
                if "error" in result:
                    errors += 1
                    error_log.append({
                        "file": task["file_label"],
                        "error": result["error"]
                    })
                    pg_info = f" p{task['page_num']}" if 'page_num' in task else ''
                    print(f"  ✗ [{done}/{len(tasks)}] {task['file_label'][:55]}{pg_info} "
                          f"— {result['error'][:80]}")
                elif result.get('status') == 'skip':
                    print(f"  ⊘ [{done}/{len(tasks)}] {task['file_label'][:55]} p{task.get('page_num','')} "
                          f"— skip (page out of range)")
                else:
                    pages = result.get("pages_processed", "?")
                    pg_info = f" p{task['page_num']}" if 'page_num' in task else ''
                    print(f"  ✓ [{done}/{len(tasks)}] {task['file_label'][:55]}{pg_info} "
                          f"— {pages} pages")
            except Exception as e:
                done += 1
                errors += 1
                print(f"  ✗ [{done}/{len(tasks)}] {task['file_label'][:60]} — {e}")

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {done - errors}/{len(tasks)}")
    print(f"  Errors:  {errors}")
    print(f"  Speed:   {elapsed/len(tasks):.1f}s per file")

    if error_log:
        err_path = os.path.join(DATA_DIR, f'dispatch_errors_{slug}.json')
        with open(err_path, 'w', encoding='utf-8') as f:
            json.dump(error_log, f, ensure_ascii=False, indent=2)
        print(f"  Error log: {err_path}")

    print(f"\nNext step: python cloud/collect.py --province {slug}")


if __name__ == '__main__':
    main()
