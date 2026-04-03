#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split multi-page PDFs into single-page files and upload to Google Drive.

Pipeline (per PDF):
  1. Download original PDF from Drive (API key, public)
  2. Extract only the pages needed by review items (PyMuPDF)
  3. Upload each single-page PDF immediately to Drive (OAuth)
  4. Record new file ID for updating review_data.json

Folder structure on Drive:
  สส.5_18_หน้าเดี่ยว/
    ชัยภูมิ/
      เขต_1/
        filename_p001.pdf
        filename_p005.pdf
    ตาก/
      เขต_1/
        ...

Usage:
  python scripts/split_and_upload.py                  # ทั้งหมด
  python scripts/split_and_upload.py --province ชัยภูมิ  # เฉพาะจังหวัด
  python scripts/split_and_upload.py --dry-run          # ดูแผนอย่างเดียว
  python scripts/split_and_upload.py --workers 2        # จำนวน upload threads
"""
import argparse
import json
import os
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF
import requests as http_req

# Google API
try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload
except ImportError:
    print("pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token_full.json"
PROGRESS_FILE = PROJECT_ROOT / "_split_progress.json"
REVIEW_DATA = PROJECT_ROOT / "review-app" / "public" / "data" / "review_data.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
SPLIT_ROOT_FOLDER = "สส.5_18_หน้าเดี่ยว"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def get_api_key():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in open(env_path):
            line = line.strip()
            if line.startswith("GOOGLE_CLOUD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_CLOUD_API_KEY")


def authenticate_drive():
    """OAuth2 auth for writing to user's Drive."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
            except Exception:
                creds = None
        if not creds:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ ไม่พบ {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _retry(func, max_retries=6, base_delay=5, label=""):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e)
            retryable = any(c in err_str for c in [
                "500", "503", "429", "Internal Error", "Rate Limit",
                "SSL", "10053", "10054", "timed out", "timeout",
                "Connection aborted", "Connection reset", "BrokenPipe",
                "Errno 0", "BadStatusLine",
            ])
            if not retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"    retry {attempt+1}/{max_retries} in {delay}s ({label}): {err_str[:60]}", flush=True)
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------
def find_or_create_folder(service, name, parent_id=None):
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    results = _retry(lambda: service.files().list(q=q, fields="files(id)", pageSize=1).execute())
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = _retry(lambda: service.files().create(body=meta, fields="id").execute())
    return folder["id"]


def upload_pdf_bytes(service, pdf_bytes, filename, parent_id):
    """Upload PDF bytes to Drive using in-memory upload with retry."""
    meta = {"name": filename, "parents": [parent_id]}
    def _do_upload():
        media = MediaInMemoryUpload(pdf_bytes, mimetype="application/pdf", resumable=False)
        return service.files().create(body=meta, media_body=media, fields="id").execute()
    result = _retry(_do_upload, label=filename)
    return result["id"]


def download_pdf(file_id, api_key, service=None):
    """Download PDF from Drive using multiple strategies."""
    strategies = []
    # Strategy 0: OAuth service (separate quota from API key)
    if service:
        strategies.append(lambda: _download_oauth(file_id, service))
    strategies += [
        # Strategy 1: Direct download URL (no API quota)
        lambda: _download_direct(file_id),
        # Strategy 2: API key download
        lambda: _download_api(file_id, api_key),
    ]
    last_err = None
    for strat in strategies:
        try:
            return strat()
        except Exception as e:
            last_err = e
            continue
    raise last_err


def _download_oauth(file_id, service):
    """Download via authenticated OAuth service (different quota)."""
    import io
    from googleapiclient.http import MediaIoBaseDownload
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = _retry(lambda: downloader.next_chunk(), label=f"oauth-dl-{file_id[:8]}")
    data = buf.getvalue()
    if not _is_valid_pdf(data):
        raise Exception(f"OAuth DL got {len(data)}b, not PDF")
    return data


def _is_valid_pdf(data):
    """Quick check if bytes look like a PDF."""
    return data and len(data) > 100 and data[:5] == b'%PDF-'


def _download_direct(file_id):
    """Download via direct URL (no API key needed, different quota)."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    sess = http_req.Session()
    for attempt in range(5):
        try:
            resp = sess.get(url, timeout=120, allow_redirects=True)
            if resp.status_code == 200:
                # Happy path: got PDF directly
                if _is_valid_pdf(resp.content):
                    return resp.content
                # Large file: virus scan confirmation page
                # Try confirm=t with cookies from first request
                resp2 = sess.get(f"{url}&confirm=t", timeout=180)
                if resp2.status_code == 200 and _is_valid_pdf(resp2.content):
                    return resp2.content
                # Try extracting token from HTML
                import re
                for pat in [r'confirm=([0-9A-Za-z_-]+)', r'&confirm=([^&"]+)', r'uuid=([0-9A-Za-z_-]+)']:
                    m = re.search(pat, resp.text)
                    if m:
                        token = m.group(1)
                        resp3 = sess.get(f"{url}&confirm={token}", timeout=180)
                        if resp3.status_code == 200 and _is_valid_pdf(resp3.content):
                            return resp3.content
                # All attempts failed for this large file
                raise Exception(f"Direct DL got HTML ({len(resp.content)}b), not PDF")
            if resp.status_code in (403, 429):
                delay = min(15 * (2 ** attempt), 300)
                print(f"    DL direct rate limit ({resp.status_code}), wait {delay}s", flush=True)
                time.sleep(delay)
                continue
            raise Exception(f"Direct DL HTTP {resp.status_code}")
        except http_req.exceptions.RequestException as e:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise Exception("Direct download failed")


def _download_api(file_id, api_key):
    """Download via Drive API (uses API key quota)."""
    url = f"{DRIVE_API_BASE}/files/{file_id}?alt=media&key={api_key}"
    for attempt in range(5):
        try:
            resp = http_req.get(url, timeout=120)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code in (403, 429):
                delay = min(30 * (2 ** attempt), 600)
                print(f"    DL API rate limit ({resp.status_code}), wait {delay}s", flush=True)
                time.sleep(delay)
                continue
            raise Exception(f"API DL HTTP {resp.status_code}")
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise Exception("API download failed")


def extract_single_page(pdf_bytes, page_0based):
    """Extract a single page from PDF bytes, return new PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=page_0based, to_page=page_0based)
    result = new_doc.tobytes()
    new_doc.close()
    doc.close()
    return result


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------
def load_progress():
    if PROGRESS_FILE.exists():
        return json.load(open(PROGRESS_FILE, 'r', encoding='utf-8'))
    return {}  # key: "fid_page" -> {"new_fid": "...", "folder": "..."}


def save_progress(progress, lock):
    with lock:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Build work plan
# ---------------------------------------------------------------------------
def build_plan(review_data, province_filter=None):
    """
    Returns:
      work_items: list of {fid, page, province, constituency, items, upload_name}
      grouped by fid for efficient downloading
    """
    def get_fid(url):
        if not url or '/d/' not in url:
            return None
        return url.split('/d/')[1].split('/')[0]

    # Group items by (fid, page) where total_pages > 2
    combos = defaultdict(lambda: {"items": [], "province": "", "constituency": "", "file": ""})

    for item in review_data:
        tp = item.get('total_pages') or 1
        if tp <= 2:
            continue
        fid = get_fid(item.get('pdf_url', ''))
        if not fid:
            continue
        page = item.get('page', 1)
        province = item.get('province', '')
        constituency = item.get('constituency', '')

        if province_filter and province != province_filter:
            continue

        key = f"{fid}_{page}"
        combos[key]["items"].append(item['id'])
        combos[key]["province"] = province
        combos[key]["constituency"] = str(constituency)
        combos[key]["file"] = item.get('file', '')
        combos[key]["fid"] = fid
        combos[key]["page"] = page

    # Group by fid for batch downloading
    by_fid = defaultdict(list)
    for key, info in combos.items():
        by_fid[info["fid"]].append(info)

    # Sort by_fid: ชัยภูมิ เขต 1→7 first, then ตาก, then เพชรบูรณ์
    PROVINCE_ORDER = {"ชัยภูมิ": 0, "ตาก": 1, "เพชรบูรณ์": 2}

    def _sort_key(fid):
        infos = by_fid[fid]
        prov = infos[0]["province"]
        const = infos[0]["constituency"]
        try:
            const_num = int(const)
        except (ValueError, TypeError):
            const_num = 999
        return (PROVINCE_ORDER.get(prov, 99), const_num, fid)

    sorted_fids = sorted(by_fid.keys(), key=_sort_key)
    by_fid_ordered = {fid: by_fid[fid] for fid in sorted_fids}

    return combos, by_fid_ordered


UPLOAD_DELAY = 0.5  # seconds between uploads to avoid rate limiting
DOWNLOAD_DELAY = 2.0  # seconds between PDF downloads to avoid 403 rate limits


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def do_upload_one(service, key, page_bytes, info, progress, folder_cache, root_folder_id, stats):
    """Upload a single page PDF. Returns True on success."""
    province = info["province"]
    constituency = info["constituency"]

    # Get/create folder: root/province/const_N
    folder_key = f"{province}/{constituency}"
    if folder_key not in folder_cache:
        prov_folder = find_or_create_folder(service, province, root_folder_id)
        const_folder = find_or_create_folder(service, f"เขต_{constituency}", prov_folder)
        folder_cache[folder_key] = const_folder
    target_folder = folder_cache[folder_key]

    # Build filename
    file_path = info["file"].replace('\\', '/')
    orig_name = file_path.split('/')[-1] if '/' in file_path else file_path
    base = os.path.splitext(orig_name)[0]
    upload_name = f"{base}_p{info['page']:03d}.pdf"

    # Upload
    new_fid = upload_pdf_bytes(service, page_bytes, upload_name, target_folder)

    # Record
    progress[key] = {"new_fid": new_fid, "province": province, "constituency": constituency}
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False)

    stats["uploaded"] += 1
    stats["items"] += len(info["items"])
    return True


def main():
    parser = argparse.ArgumentParser(description="Split multi-page PDFs and upload to Drive")
    parser.add_argument("--province", type=str, help="Process only this province")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from progress file")
    args = parser.parse_args()

    print("=" * 60)
    print("Split & Upload: single-page PDF -> Google Drive")
    print("=" * 60)

    # Load review data
    review_data = json.load(open(REVIEW_DATA, 'r', encoding='utf-8'))
    print(f"Review items: {len(review_data)}")

    # Build plan
    combos, by_fid = build_plan(review_data, args.province)
    print(f"Pages to split: {len(combos)}")
    print(f"PDFs to download: {len(by_fid)}")

    prov_summary = defaultdict(int)
    for info in combos.values():
        prov_summary[info["province"]] += 1
    for prov, count in sorted(prov_summary.items()):
        print(f"   {prov}: {count} pages")

    if args.dry_run:
        print("\nDry run -- no downloads or uploads")
        return

    # Load progress for resume
    progress = load_progress() if args.resume else {}
    already_done = set(progress.keys())
    remaining_combos = {k: v for k, v in combos.items() if k not in already_done}
    _remaining_fids = defaultdict(list)
    for key, info in remaining_combos.items():
        _remaining_fids[info["fid"]].append(info)

    # Keep same sort order as by_fid (ชัยภูมิ→ตาก→เพชรบูรณ์)
    remaining_fids = {fid: _remaining_fids[fid] for fid in by_fid if fid in _remaining_fids}

    if already_done:
        print(f"Resume: {len(already_done)} done, {len(remaining_combos)} remaining")
    else:
        print(f"Starting fresh: {len(remaining_combos)} pages")

    if not remaining_combos:
        print("All pages already processed!")
        update_review_data(review_data, progress)
        return

    # Auth
    api_key = get_api_key()
    if not api_key:
        print("No GOOGLE_CLOUD_API_KEY in .env")
        sys.exit(1)
    print(f"API Key: {api_key[:15]}...")

    print("Authenticating Google Drive (OAuth)...")
    service = authenticate_drive()
    print("Authenticated!")

    root_folder_id = find_or_create_folder(service, SPLIT_ROOT_FOLDER)
    print(f"Root folder: {SPLIT_ROOT_FOLDER} ({root_folder_id})")

    folder_cache = {}
    stats = {"uploaded": 0, "errors": 0, "items": 0,
             "total": len(remaining_combos), "start": time.time()}

    print(f"\n{'='*60}")
    print(f"Processing {len(remaining_fids)} PDFs (sequential)...")
    print(f"{'='*60}\n")

    for pdf_idx, (fid, page_infos) in enumerate(remaining_fids.items()):
        pages_needed = sorted(set(info["page"] for info in page_infos))
        sample_file = page_infos[0]["file"]
        prov = page_infos[0]["province"]

        print(f"[{pdf_idx+1}/{len(remaining_fids)}] {prov} | {len(pages_needed)} pages | {os.path.basename(sample_file)}", flush=True)

        # Download
        try:
            pdf_bytes = download_pdf(fid, api_key, service=service)
        except Exception as e:
            print(f"  DL FAIL: {e}", flush=True)
            stats["errors"] += len(pages_needed)
            continue

        # Validate PDF
        if not pdf_bytes or len(pdf_bytes) < 100 or pdf_bytes[:5] != b'%PDF-':
            print(f"  SKIP: not a valid PDF ({len(pdf_bytes)} bytes)", flush=True)
            stats["errors"] += len(pages_needed)
            del pdf_bytes
            continue

        # Open PDF
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
        except Exception as e:
            print(f"  SKIP: broken PDF: {e}", flush=True)
            stats["errors"] += len(pages_needed)
            del pdf_bytes
            continue

        for info in page_infos:
            page = info["page"]
            key = f"{fid}_{page}"

            if key in already_done:
                continue

            page_0based = page - 1
            if page_0based < 0 or page_0based >= total_pages:
                print(f"  SKIP p{page} (out of range, total={total_pages})", flush=True)
                continue

            # Extract single page
            try:
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=page_0based, to_page=page_0based)
                page_bytes = new_doc.tobytes()
                new_doc.close()
            except Exception as e:
                print(f"  SPLIT ERR p{page}: {e}", flush=True)
                stats["errors"] += 1
                continue

            # Upload (sequential, with retry built into upload_pdf_bytes)
            try:
                do_upload_one(service, key, page_bytes, info, progress,
                              folder_cache, root_folder_id, stats)
            except Exception as e:
                stats["errors"] += 1
                print(f"  UPLOAD FAIL p{page}: {e}", flush=True)
                # If connection is broken, re-auth and retry once
                try:
                    print("  Re-authenticating...", flush=True)
                    service = authenticate_drive()
                    do_upload_one(service, key, page_bytes, info, progress,
                                  folder_cache, root_folder_id, stats)
                    stats["errors"] -= 1  # undo the error count
                    print("  Recovered!", flush=True)
                except Exception as e2:
                    print(f"  RETRY ALSO FAILED: {e2}", flush=True)

            # Progress report
            if stats["uploaded"] % 100 == 0 or stats["uploaded"] <= 5:
                elapsed = time.time() - stats["start"]
                rate = stats["uploaded"] / elapsed * 60 if elapsed > 0 else 0
                remaining = (stats["total"] - stats["uploaded"]) / rate if rate > 0 else 999
                print(f"  >> {stats['uploaded']}/{stats['total']} "
                      f"[{rate:.0f}/min, ~{remaining:.0f} min left]", flush=True)

            # Delay between uploads
            time.sleep(UPLOAD_DELAY)

        doc.close()
        del pdf_bytes
        time.sleep(DOWNLOAD_DELAY)  # delay between PDFs to avoid rate limiting

    elapsed = time.time() - stats["start"]
    print(f"\n{'='*60}")
    print(f"Done! Uploaded: {stats['uploaded']}, Errors: {stats['errors']}")
    print(f"Time: {elapsed/60:.1f} min")
    print(f"{'='*60}")

    update_review_data(review_data, progress)


def update_review_data(review_data, progress):
    """Update review_data.json with new single-page pdf_urls."""
    if not progress:
        print("No progress data to apply")
        return

    fid_page_to_new = {}
    for key, val in progress.items():
        parts = key.rsplit('_', 1)
        if len(parts) == 2:
            orig_fid, page_str = parts
            try:
                page = int(page_str)
                fid_page_to_new[(orig_fid, page)] = val["new_fid"]
            except ValueError:
                pass

    def get_fid(url):
        if not url or '/d/' not in url:
            return None
        return url.split('/d/')[1].split('/')[0]

    updated = 0
    for item in review_data:
        tp = item.get('total_pages') or 1
        if tp <= 2:
            continue
        fid = get_fid(item.get('pdf_url', ''))
        if not fid:
            continue
        page = item.get('page', 1)
        lookup_key = (fid, page)

        if lookup_key in fid_page_to_new:
            new_fid = fid_page_to_new[lookup_key]
            item['pdf_url'] = f"https://drive.google.com/file/d/{new_fid}/preview"
            item['drive_view_url'] = f"https://drive.google.com/file/d/{new_fid}/view"
            item['total_pages'] = 1
            updated += 1

    with open(REVIEW_DATA, 'w', encoding='utf-8') as f:
        json.dump(review_data, f, ensure_ascii=False)

    size_mb = REVIEW_DATA.stat().st_size / 1024 / 1024
    print(f"\nUpdated {updated} items in review_data.json ({size_mb:.1f} MB)")

    remaining = sum(1 for x in review_data if (x.get('total_pages') or 1) > 2)
    print(f"Remaining items with total_pages > 2: {remaining}")


if __name__ == "__main__":
    main()
