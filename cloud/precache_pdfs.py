# -*- coding: utf-8 -*-
"""
Pre-cache PDFs to GCS so Cloud Function can use cached copies
instead of downloading from Google Drive (which has per-file quota limits).

Identifies PDFs with missing pages (same logic as dispatch_missing.py),
downloads from Drive, and uploads to GCS _pdf_cache/{file_id}.pdf.

Usage:
  python cloud/precache_pdfs.py --province chaiyaphum --dry-run
  python cloud/precache_pdfs.py --province chaiyaphum
  python cloud/precache_pdfs.py --province chaiyaphum --limit 20

Two-phase approach:
  Phase 1: Download PDFs from Drive (OAuth2) -> local temp dir
  Phase 2: Upload all to GCS via gsutil (reliable for large files)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


def get_access_token():
    """Get OAuth2 access token from gcloud CLI."""
    result = subprocess.run(
        ['gcloud', 'auth', 'print-access-token'],
        capture_output=True, text=True, shell=True
    )
    token = result.stdout.strip()
    if not token or 'ERROR' in token:
        print("[ERROR] Run: gcloud auth login --enable-gdrive-access")
        sys.exit(1)
    return token


def download_pdf_oauth(file_id, token):
    """Download PDF from Drive using OAuth2 token (bypasses per-file quota)."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        resp = requests.get(url, headers=headers, timeout=180)
        if resp.status_code == 200 and resp.content[:4] == b'%PDF':
            return resp.content, None
        if resp.status_code == 403:
            return None, "forbidden"
        if resp.status_code == 404:
            return None, "not_found"
        return None, f"http_{resp.status_code}"
    except Exception as e:
        return None, str(e)[:80]


def find_pdfs_with_missing_pages(slug):
    """Find all PDFs that have missing pages. Returns list of (file_id, file_label, missing_count)."""
    # Load existing OCR data
    ocr_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if not os.path.exists(ocr_path):
        print(f"No OCR data: {ocr_path}")
        return []
    items = json.load(open(ocr_path, 'r', encoding='utf-8'))

    # Build done_pages and file_total
    done_pages = defaultdict(set)
    file_total = {}
    for item in items:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    # Load drive index
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

        # Front pages only: 1, 3, 5, ...
        all_target = set(range(1, tp + 1, 2))
        missing = all_target - done
        if not missing:
            continue

        results.append((fid, fl, len(missing)))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--province", default="chaiyaphum")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slug = args.province
    pdfs = find_pdfs_with_missing_pages(slug)
    print(f"PDFs with missing pages: {len(pdfs)}")
    total_missing = sum(c for _, _, c in pdfs)
    print(f"Total missing page tasks: {total_missing}")

    if args.limit > 0:
        pdfs = pdfs[:args.limit]
        print(f"Limited to: {len(pdfs)}")

    if args.dry_run:
        for fid, fl, cnt in pdfs[:20]:
            print(f"  {fid[:20]}... ({cnt} pages) -> ...{fl[-50:]}")
        return

    token = get_access_token()
    print(f"Token: {token[:15]}...")

    # Check which files are already cached in GCS
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket('election69-ocr-results-th')

    to_download = []
    cached = 0
    for fid, fl, cnt in pdfs:
        blob = bucket.blob(f"_pdf_cache/{fid}.pdf")
        if blob.exists():
            cached += 1
        else:
            to_download.append((fid, fl, cnt))
    print(f"Already cached: {cached}, Need download: {len(to_download)}")

    if not to_download:
        print("All PDFs already cached!")
        return

    # Phase 1: Download PDFs from Drive -> local temp dir
    import tempfile
    tmp_dir = os.path.join(PROJECT_ROOT, 'data', '_pdf_cache_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    start = time.time()
    downloaded = 0
    failed = 0

    for i, (fid, fl, cnt) in enumerate(to_download):
        local_path = os.path.join(tmp_dir, f"{fid}.pdf")
        if os.path.exists(local_path) and os.path.getsize(local_path) > 100:
            downloaded += 1
            print(f"  [{i+1}/{len(to_download)}] LOCAL ({cnt}p): ...{fl[-50:]}")
            continue

        print(f"  [{i+1}/{len(to_download)}] Downloading ({cnt}p): ...{fl[-50:]}", end="", flush=True)
        pdf_bytes, err = download_pdf_oauth(fid, token)

        if pdf_bytes:
            with open(local_path, 'wb') as f:
                f.write(pdf_bytes)
            downloaded += 1
            print(f" -> {len(pdf_bytes)//1024}KB")
        else:
            failed += 1
            print(f" -> FAILED: {err}")

        time.sleep(0.2)

    dl_elapsed = time.time() - start
    print(f"\nPhase 1 done in {dl_elapsed:.0f}s: {downloaded} downloaded, {failed} failed")

    # Phase 2: Upload all local PDFs to GCS via gsutil
    local_files = [f for f in os.listdir(tmp_dir) if f.endswith('.pdf')]
    if not local_files:
        print("No files to upload.")
        return

    print(f"\nPhase 2: Uploading {len(local_files)} files to GCS via gsutil...")
    gcs_dest = f"gs://{bucket.name}/_pdf_cache/"

    # gsutil -m cp for parallel upload
    cmd = f'gsutil -m cp "{tmp_dir}/*.pdf" {gcs_dest}'
    print(f"  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=1800)  # 30 min max
    if result.returncode == 0:
        print(f"  Upload complete!")
        # Cleanup local files
        for f in local_files:
            os.remove(os.path.join(tmp_dir, f))
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
    else:
        print(f"  Upload error (exit {result.returncode}):")
        print(f"  {result.stderr[:500]}")

    total_elapsed = time.time() - start
    print(f"\nTotal: {total_elapsed:.0f}s")
    print(f"  Cached:     {cached}")
    print(f"  Downloaded: {downloaded}")
    print(f"  Failed:     {failed}")


if __name__ == '__main__':
    main()
