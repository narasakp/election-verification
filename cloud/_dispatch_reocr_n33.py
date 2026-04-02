# -*- coding: utf-8 -*-
"""
Dispatch n=33 re-OCR tasks to Cloud Function, then merge results.

Phase 44: OCR the missing middle pages for 1,719 บัญชีรายชื่อ records
that only have n=33 candidates (should be n=57).

Workflow:
  1. Read data/_reocr_n33_targets.json (1,719 targets, 274 unique PDFs)
  2. Deduplicate by (fid, page_num) → unique OCR tasks
  3. Dispatch to Cloud Function in parallel (20 workers)
  4. Download results from GCS
  5. Merge candidates into existing ocr_multimodel_{province}.json
  6. Save with backup

Usage:
  python cloud/_dispatch_reocr_n33.py --workers 20
  python cloud/_dispatch_reocr_n33.py --dry-run
  python cloud/_dispatch_reocr_n33.py --collect-only  # skip dispatch, just merge from GCS
"""
import argparse
import json
import os
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
    'phetchabun': os.path.join(DATA_DIR, 'ocr_multimodel_phetchabun.json'),
    'chaiyaphum': os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'),
    'tak':        os.path.join(DATA_DIR, 'ocr_multimodel_tak.json'),
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


def send_task(fid, file_label, prov_key, page_0idx, google_api_key, dry_run=False):
    """Send one page to Cloud Function. Returns (fid, page_0idx, status, blob_path)."""
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
    """Download a GCS blob and return parsed JSON. gcs_bucket = bucket object (reused)."""
    try:
        blob = gcs_bucket.blob(blob_path)
        if not blob.exists():
            return None
        data = json.loads(blob.download_as_text())
        return data
    except Exception as e:
        print(f'  GCS err {blob_path}: {e}')
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=20)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--collect-only', action='store_true',
                        help='Skip dispatch, just collect from GCS and merge')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    env = load_env()
    google_api_key = env.get('GOOGLE_CLOUD_API_KEY', '')

    # ── Load targets ────────────────────────────────────────────────────
    targets = json.load(open(os.path.join(DATA_DIR, '_reocr_n33_targets.json'),
                             encoding='utf-8'))
    print(f'Targets: {len(targets)}')

    # Deduplicate tasks by (fid, page_1indexed) — multiple targets may share a page
    tasks = {}  # (fid, page_1idx) -> {fid, file_label, prov_key, page_0idx, targets:[]}
    for t in targets:
        key = (t['fid'], t['missing_page'])
        if key not in tasks:
            tasks[key] = {
                'fid': t['fid'],
                'file_label': t['file'],
                'prov_key': t['prov_key'],
                'page_0idx': t['missing_page'] - 1,
                'page_1idx': t['missing_page'],
                'targets': [],
            }
        tasks[key]['targets'].append(t)

    task_list = list(tasks.values())
    if args.limit:
        task_list = task_list[:args.limit]
    print(f'Unique (fid, page) tasks: {len(task_list)}')

    # ── Dispatch ────────────────────────────────────────────────────────
    blob_map = {}   # (fid, page_0idx) -> blob_path
    ok_count = 0
    empty_count = 0
    fail_count = 0

    if not args.collect_only:
        print(f'\nDispatching {len(task_list)} tasks with {args.workers} workers...')
        start = time.time()

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(send_task,
                            t['fid'], t['file_label'], t['prov_key'],
                            t['page_0idx'], google_api_key, args.dry_run): t
                for t in task_list
            }
            for i, fut in enumerate(as_completed(futs), 1):
                t = futs[fut]
                fid, page_0idx, status, blob = fut.result()
                key = (fid, page_0idx)
                if status == 'ok':
                    ok_count += 1
                    blob_map[key] = blob
                elif status == 'empty':
                    empty_count += 1
                    blob_map[key] = blob  # still save blob, might have data
                else:
                    fail_count += 1

                if i % 50 == 0 or i == len(task_list):
                    elapsed = time.time() - start
                    rate = i / elapsed * 60
                    print(f'  [{i}/{len(task_list)}] ok={ok_count} empty={empty_count} '
                          f'fail={fail_count} rate={rate:.0f}/min')

        elapsed = time.time() - start
        print(f'\nDispatch done in {elapsed/60:.1f} min')
        print(f'ok={ok_count} empty={empty_count} fail={fail_count}')
    else:
        # Build blob_map from expected paths
        print('Collect-only mode — building blob paths from targets...')
        for t in task_list:
            fid = t['fid']
            page_0idx = t['page_0idx']
            prov = t['prov_key']
            blob_map[(fid, page_0idx)] = f"{prov}/{fid}_p{page_0idx}.json"
        print(f'Expected blobs: {len(blob_map)}')

    if args.dry_run:
        print('Dry run complete.')
        return

    # ── Load OCR data ───────────────────────────────────────────────────
    print('\nLoading OCR data...')
    ocr_data = {k: json.load(open(v, encoding='utf-8')) for k, v in OCR_FILES.items()}

    # Build source lookup: (file, page) -> (prov_key, list_index)
    src_lookup = {}
    for prov, records in ocr_data.items():
        for idx, r in enumerate(records):
            src_lookup[(r.get('file', ''), r.get('page', 0))] = (prov, idx)

    # ── Collect & Merge ─────────────────────────────────────────────────
    print(f'\nCollecting {len(blob_map)} blobs from GCS and merging...')
    from google.cloud import storage as gcs_storage
    _gcs_client = gcs_storage.Client()
    _gcs_bucket = _gcs_client.bucket(GCS_BUCKET)

    updated = 0
    no_cands = 0
    merge_fail = 0
    done_count = 0

    for (fid, page_0idx), blob_path in blob_map.items():
        if not blob_path:
            continue
        done_count += 1
        if done_count % 200 == 0:
            print(f'  collect [{done_count}/{len(blob_map)}] updated={updated}')

        gcs_data = download_gcs_blob(_gcs_bucket, blob_path)
        if not gcs_data:
            continue

        # GCS data is a list of page records
        if isinstance(gcs_data, list):
            page_records = gcs_data
        else:
            page_records = [gcs_data]

        if not page_records:
            no_cands += 1
            continue

        new_cands = page_records[0].get('candidates', [])
        if not new_cands:
            no_cands += 1
            continue

        # Find all targets that use this (fid, page_0idx)
        page_1idx = page_0idx + 1
        key = (fid, page_1idx)
        if key not in tasks:
            continue

        page_targets = tasks[key]['targets']
        for t in page_targets:
            fl = t['file']
            first_page = min(t['known_pages'])
            entry = src_lookup.get((fl, first_page))
            if not entry:
                merge_fail += 1
                continue

            prov, idx = entry
            src_rec = ocr_data[prov][idx]
            existing_cands = src_rec.get('candidates', [])
            existing_nums = {c.get('number') for c in existing_cands}
            to_add = [c for c in new_cands if c.get('number') not in existing_nums]

            if to_add:
                merged = sorted(existing_cands + to_add, key=lambda c: (c.get('number') is None, c.get('number') or 999))
                src_rec['candidates'] = merged
                src_rec['_reocr_n33'] = True
                updated += 1
            else:
                merge_fail += 1

    print(f'\nMerge results: updated={updated} no_cands={no_cands} fail={merge_fail}')

    # ── Save ────────────────────────────────────────────────────────────
    if updated > 0:
        prov_updated = set()
        for prov, records in ocr_data.items():
            if any(r.get('_reocr_n33') for r in records):
                prov_updated.add(prov)

        for prov in prov_updated:
            path = OCR_FILES[prov]
            backup = path + '.pre_reocr_n33'
            if not os.path.exists(backup):
                shutil.copy2(path, backup)
                print(f'Backup: {backup}')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ocr_data[prov], f, ensure_ascii=False, indent=2)
            n_fixed = sum(1 for r in ocr_data[prov] if r.get('_reocr_n33'))
            print(f'Saved {prov}: {n_fixed} records updated')
    else:
        print('No updates — OCR files unchanged')

    print('\nDone.')


if __name__ == '__main__':
    main()
