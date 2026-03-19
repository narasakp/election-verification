# -*- coding: utf-8 -*-
"""
Slow sequential dispatcher for stubborn 503 pages.
Sends ONE request at a time with configurable delay between requests.
This avoids overwhelming the Cloud Function which causes 503 cascades.

Usage:
  python cloud/dispatch_slow.py --province chaiyaphum --delay 5
  python cloud/dispatch_slow.py --province chaiyaphum --delay 3 --limit 10
"""
import argparse
import json
import os
import sys
import time

from collections import defaultdict
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

FUNCTION_URL = "https://asia-southeast1-election-ocr.cloudfunctions.net/ocr-worker"

PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
    "tak": "tak", "chaiyaphum": "chaiyaphum", "phetchabun": "phetchabun",
}


def load_env():
    env = {}
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def main():
    parser = argparse.ArgumentParser(description="Slow sequential OCR dispatcher")
    parser.add_argument("--province", required=True)
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Seconds between requests (default: 5)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retries", type=int, default=3,
                        help="Max retries per page on 503 (default: 3)")
    args = parser.parse_args()

    slug = PROVINCE_SLUGS.get(args.province, args.province)
    env = load_env()
    api_key = env.get('GOOGLE_CLOUD_API_KEY', '')

    # Load existing OCR
    ocr_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    existing = json.load(open(ocr_path, encoding='utf-8'))
    done_set = set()
    for rec in existing:
        fid = rec.get('file_id', '')
        pn = rec.get('page_number', rec.get('page_num', -1))
        if fid and pn >= 0:
            done_set.add((fid, pn))

    # Load drive index
    idx_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    drive_index = json.load(open(idx_path, encoding='utf-8'))

    # Build done_pages lookup from existing OCR (page numbers are 1-indexed in data)
    done_pages = defaultdict(set)
    file_total = {}
    for item in existing:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    # Build file_label -> entry map from drive index
    label_to_entry = {}
    for fi in drive_index:
        if not fi.get('name', '').lower().endswith('.pdf'):
            continue
        fl = fi['path'] + '/' + fi['name']
        label_to_entry[fl] = fi

    # Find missing front pages
    tasks = []
    for fl, entry in label_to_entry.items():
        tp = file_total.get(fl)
        done = done_pages.get(fl, set())
        if tp is None or tp <= 4:
            if tp and len(done) >= tp // 2:
                continue
            if tp is None:
                continue
        all_target = set(range(1, tp + 1, 2))  # front pages only (1-indexed odd)
        missing = sorted(all_target - done)
        for page_1indexed in missing:
            tasks.append({
                'file_id': entry['file_id'],
                'file_label': fl,
                'page_num': page_1indexed - 1,  # CF uses 0-indexed
            })

    err_path = os.path.join(DATA_DIR, f'dispatch_missing_errors_{slug}.json')
    print(f"[Missing]   {len(tasks)} front pages to OCR")

    if args.limit > 0:
        tasks = tasks[:args.limit]

    print(f"[Province]  {slug}")
    print(f"[Tasks]     {len(tasks)} pages")
    print(f"[Delay]     {args.delay}s between requests")
    print(f"[Retries]   {args.retries} per page on 503")
    print()

    success = 0
    failed = 0
    errors_out = []
    start = time.time()

    for i, task in enumerate(tasks):
        fid = task['file_id']
        fl = task['file_label']
        pn = task['page_num']
        label = fl[-55:]

        payload = {
            'file_id': fid,
            'file_label': fl,
            'province': slug,
            'google_api_key': api_key,
            'max_pages': 1,
            'page_num': pn,
        }

        ok = False
        for attempt in range(1, args.retries + 1):
            print(f"  [{i+1}/{len(tasks)}] p{pn+1} ...{label}", end="", flush=True)
            if attempt > 1:
                print(f" (retry {attempt})", end="", flush=True)

            try:
                resp = requests.post(FUNCTION_URL, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    pages = data.get('pages_processed', '?')
                    print(f" -> OK ({pages}p)")
                    success += 1
                    ok = True
                    break
                elif resp.status_code == 503:
                    wait = args.delay * (2 ** (attempt - 1))  # exponential backoff
                    print(f" -> 503, wait {wait:.0f}s")
                    time.sleep(wait)
                else:
                    print(f" -> HTTP {resp.status_code}")
                    break
            except Exception as e:
                print(f" -> ERR: {str(e)[:60]}")
                break

        if not ok:
            failed += 1
            errors_out.append({'file': fl, 'page': pn, 'error': 'failed_after_retries'})

        # Delay between requests
        if i < len(tasks) - 1:
            time.sleep(args.delay)

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {success}/{len(tasks)}")
    print(f"  Failed:  {failed}")

    if errors_out:
        with open(err_path, 'w', encoding='utf-8') as f:
            json.dump(errors_out, f, ensure_ascii=False, indent=2)
        print(f"  Errors:  {err_path}")


if __name__ == '__main__':
    main()
