# -*- coding: utf-8 -*-
"""
Dispatch vision-only pages to Gemini OCR via Cloud Function.
These are pages that Vision OCR captured but Gemini missed.

Usage:
  python cloud/dispatch_vision_batch.py
  python cloud/dispatch_vision_batch.py --delay 3 --limit 10
  python cloud/dispatch_vision_batch.py --dry-run
"""
import argparse
import json
import os
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

FUNCTION_URL = "https://asia-southeast1-election-ocr.cloudfunctions.net/ocr-worker"
DISPATCH_LIST = os.path.join(DATA_DIR, '_dispatch_vision_batch.json')


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
    parser = argparse.ArgumentParser(description="Dispatch vision-only pages to Gemini OCR")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between requests (default: 2)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max pages to dispatch (0 = all)")
    parser.add_argument("--retries", type=int, default=3,
                        help="Max retries per page on 503 (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show tasks without dispatching")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get('GOOGLE_CLOUD_API_KEY', '')
    if not api_key and not args.dry_run:
        print("[ERROR] GOOGLE_CLOUD_API_KEY not found in .env")
        sys.exit(1)

    # Load dispatch list
    if not os.path.exists(DISPATCH_LIST):
        print(f"[ERROR] Dispatch list not found: {DISPATCH_LIST}")
        print("Run scripts/_check_unmatched.py first to generate it.")
        sys.exit(1)

    tasks = json.load(open(DISPATCH_LIST, encoding='utf-8'))
    print(f"[Tasks]     {len(tasks)} vision-only pages to OCR")

    if args.limit > 0:
        tasks = tasks[:args.limit]
        print(f"[Limit]     Processing first {args.limit} tasks")

    if args.dry_run:
        print(f"\n[DRY RUN] Would dispatch {len(tasks)} pages:")
        for i, t in enumerate(tasks[:20]):
            print(f"  {i+1}. {t['file_label'][-60:]} p{t['page_num']+1}")
        if len(tasks) > 20:
            print(f"  ... and {len(tasks)-20} more")
        return

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
            'province': 'chaiyaphum',
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
                    wait = args.delay * (2 ** (attempt - 1))
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

        if i < len(tasks) - 1:
            time.sleep(args.delay)

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {success}/{len(tasks)}")
    print(f"  Failed:  {failed}")

    if errors_out:
        err_path = os.path.join(DATA_DIR, 'dispatch_vision_errors.json')
        with open(err_path, 'w', encoding='utf-8') as f:
            json.dump(errors_out, f, ensure_ascii=False, indent=2)
        print(f"  Errors:  {err_path}")

    if success > 0:
        print(f"\n[NEXT] Run 'python cloud/collect.py --province chaiyaphum' to collect results")
        print(f"       Then 'python scripts/prepare_review_data.py' to rebuild review data")


if __name__ == '__main__':
    main()
