# -*- coding: utf-8 -*-
"""
Copy quota-blocked PDFs in Google Drive -> download copies -> cache in GCS.

Bypasses per-file download quota by creating Drive copies (new file_id
with fresh quota), downloading the copies, uploading to GCS cache,
then deleting the copies.

Requires: gcloud auth login --enable-gdrive-access
Usage:
  python cloud/copy_and_cache.py --province chaiyaphum --test 1
  python cloud/copy_and_cache.py --province chaiyaphum
  python cloud/copy_and_cache.py --province chaiyaphum --workers 5
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from google.cloud import storage

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
GCS_BUCKET = 'election69-ocr-results-th'


def get_access_token():
    """Get OAuth2 access token from gcloud CLI."""
    result = subprocess.run(
        ['gcloud', 'auth', 'print-access-token'],
        capture_output=True, text=True, shell=True
    )
    token = result.stdout.strip()
    if not token or 'ERROR' in token:
        print("[ERROR] Could not get access token. Run: gcloud auth login --enable-gdrive-access")
        sys.exit(1)
    return token


def find_pdfs_with_missing_pages(slug):
    """Find all PDFs that have missing pages."""
    ocr_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if not os.path.exists(ocr_path):
        print(f"No OCR data: {ocr_path}")
        return []
    items = json.load(open(ocr_path, 'r', encoding='utf-8'))

    done_pages = defaultdict(set)
    file_total = {}
    for item in items:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    idx_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    drive_index = json.load(open(idx_path, 'r', encoding='utf-8'))

    results = []
    for entry in drive_index:
        if not entry.get('name', '').lower().endswith('.pdf'):
            continue
        p = entry.get('path', '')
        n = entry.get('name', '')
        fl = f"{p}/{n}" if p else n
        fid = entry['file_id']

        tp = file_total.get(fl)
        done = done_pages.get(fl, set())
        if tp is None or tp <= 4:
            if tp and len(done) >= tp // 2:
                continue
            if tp is None:
                continue

        all_target = set(range(1, tp + 1, 2))
        missing = all_target - done
        if not missing:
            continue

        results.append((fid, fl, len(missing)))

    return results


def process_one(file_id, file_label, token, bucket):
    """Copy -> download -> cache -> delete for one file.
    
    Returns (ok: bool, msg: str, size_kb: int)
    """
    cache_path = f"_pdf_cache/{file_id}.pdf"
    headers = {'Authorization': f'Bearer {token}'}

    # Check GCS cache first
    blob = bucket.blob(cache_path)
    if blob.exists():
        return True, "cached", 0

    copy_id = None
    try:
        # 1) Copy file in Drive
        copy_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/copy"
        cr = requests.post(copy_url,
                           headers={**headers, 'Content-Type': 'application/json'},
                           json={"name": f"_tmp_{file_id}.pdf"},
                           timeout=30)
        if cr.status_code != 200:
            err = cr.json().get('error', {}).get('message', cr.text[:80])
            return False, f"copy_err({cr.status_code}): {err}", 0
        copy_id = cr.json()['id']

        # 2) Download the copy (fresh quota) — retry once
        dl_url = f"https://www.googleapis.com/drive/v3/files/{copy_id}?alt=media"
        pdf_bytes = None
        for attempt in range(2):
            try:
                dr = requests.get(dl_url, headers=headers, timeout=300)
                if dr.status_code == 200 and dr.content[:4] == b'%PDF':
                    pdf_bytes = dr.content
                    break
            except Exception:
                if attempt == 0:
                    time.sleep(2)
        if not pdf_bytes:
            return False, "download_failed", 0
        size_kb = len(pdf_bytes) // 1024

        # 3) Upload to GCS cache
        blob.upload_from_string(pdf_bytes, content_type='application/pdf')

        return True, "ok", size_kb

    except Exception as e:
        return False, str(e)[:80], 0

    finally:
        # 4) Delete copy from Drive (cleanup)
        if copy_id:
            try:
                del_url = f"https://www.googleapis.com/drive/v3/files/{copy_id}"
                requests.delete(del_url, headers=headers, timeout=10)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Copy+cache quota-blocked PDFs via Drive copy")
    parser.add_argument("--province", default="chaiyaphum")
    parser.add_argument("--test", type=int, default=0, help="Test with N files only")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slug = args.province
    pdfs = find_pdfs_with_missing_pages(slug)
    total_pages = sum(c for _, _, c in pdfs)
    print(f"PDFs with missing pages: {len(pdfs)} ({total_pages} page tasks)")

    if args.test > 0:
        pdfs = pdfs[:args.test]
        print(f"Test mode: {len(pdfs)} files")

    if args.dry_run:
        for fid, fl, cnt in pdfs[:20]:
            print(f"  {fid[:20]}... ({cnt}p) ...{fl[-50:]}")
        return

    token = get_access_token()
    print(f"Token: {token[:15]}...")

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    ok = 0
    cached = 0
    failed = 0
    total_kb = 0
    start = time.time()

    if args.workers <= 1:
        # Sequential
        for i, (fid, fl, cnt) in enumerate(pdfs):
            success, msg, size = process_one(fid, fl, token, bucket)
            tag = f"[{i+1}/{len(pdfs)}]"
            short = fl[-55:] if len(fl) > 55 else fl
            if msg == "cached":
                cached += 1
                print(f"  {tag} CACHED ({cnt}p): ...{short}")
            elif success:
                ok += 1
                total_kb += size
                print(f"  {tag} OK ({cnt}p, {size}KB): ...{short}")
            else:
                failed += 1
                print(f"  {tag} FAIL ({cnt}p): {msg} ...{short}")
    else:
        # Parallel
        futures = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for fid, fl, cnt in pdfs:
                f = pool.submit(process_one, fid, fl, token, bucket)
                futures[f] = (fid, fl, cnt)

            done_count = 0
            for f in as_completed(futures):
                done_count += 1
                fid, fl, cnt = futures[f]
                tag = f"[{done_count}/{len(pdfs)}]"
                short = fl[-55:] if len(fl) > 55 else fl
                try:
                    success, msg, size = f.result()
                    if msg == "cached":
                        cached += 1
                        print(f"  {tag} CACHED ({cnt}p): ...{short}")
                    elif success:
                        ok += 1
                        total_kb += size
                        print(f"  {tag} OK ({cnt}p, {size}KB): ...{short}")
                    else:
                        failed += 1
                        print(f"  {tag} FAIL ({cnt}p): {msg}")
                except Exception as e:
                    failed += 1
                    print(f"  {tag} ERROR: {e}")

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"Done in {elapsed:.0f}s")
    print(f"  Uploaded:  {ok} ({total_kb//1024}MB)")
    print(f"  Cached:    {cached}")
    print(f"  Failed:    {failed}")
    print(f"  Total:     {ok+cached+failed}/{len(pdfs)}")

    if failed:
        print(f"\n  {failed} files failed. Check errors above.")
    if ok + cached == len(pdfs):
        print(f"\nAll PDFs cached! Next steps:")
        print(f"  python cloud/dispatch_missing.py --province {slug} \\")
        print(f"    --function-url https://asia-southeast1-election-ocr.cloudfunctions.net/ocr-worker \\")
        print(f"    --workers 20")


if __name__ == '__main__':
    main()
