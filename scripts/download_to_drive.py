#!/usr/bin/env python3
"""
ดาวน์โหลดเอกสาร สส.5/18 จากเว็บจังหวัด กกต. ทั้ง 77 จังหวัด
→ อัปโหลดตรงไปยัง Google Drive (ไม่เก็บใน local disk)

ข้อกำหนด:
  1. เปิด Google Drive API ใน Cloud Console
  2. สร้าง OAuth2 credentials (Desktop app) → บันทึกเป็น credentials.json ใน project root
  3. ครั้งแรกจะเปิดเบราว์เซอร์ให้ login Google → หลังจากนั้นจะจำ token ไว้

Usage:
  python scripts/download_to_drive.py                     # ทุกจังหวัด
  python scripts/download_to_drive.py --province bangkok   # เฉพาะจังหวัด
  python scripts/download_to_drive.py --index-only         # สแกนลิงก์เท่านั้น ไม่ดาวน์โหลด
  python scripts/download_to_drive.py --resume             # ข้ามไฟล์ที่อัปโหลดแล้ว (default)
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests

# Google API libraries
try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ ต้องติดตั้ง Google API libraries ก่อน:")
    print("   pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

# Google Drive scope — drive.file allows managing files created by this app
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Root folder name on Google Drive
DRIVE_ROOT_FOLDER = "สส.5_18_ข้อมูลเลือกตั้ง_2569"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

PROVINCE_SLUGS = [
    "amnatcharoen", "angthong", "bangkok", "buengkan", "buriram",
    "chachoengsao", "chainat", "chaiyaphum", "chanthaburi", "chiangmai",
    "chiangrai", "chonburi", "chumphon", "kalasin", "kamphaengphet",
    "kanchanaburi", "khonkaen", "krabi", "lampang", "lamphun",
    "loei", "lopburi", "maehongson", "mahasarakham", "mukdahan",
    "nakhonnayok", "nakhonpathom", "nakhonphanom", "nakhonratchasima",
    "nakhonsawan", "nakhonsithammarat", "nan", "narathiwat", "nongbualamphu",
    "nongkhai", "nonthaburi", "pathumthani", "pattani", "phangnga",
    "phatthalung", "phayao", "phetchabun", "phetchaburi", "phichit",
    "phitsanulok", "phranakhonsiayutthaya", "phrae", "phuket",
    "prachinburi", "prachuapkhirikhan", "ranong", "ratchaburi", "rayong",
    "roiet", "sakaeo", "sakonnakhon", "samutprakan", "samutsakhon",
    "samutsongkhram", "saraburi", "satun", "singburi", "sisaket",
    "songkhla", "sukhothai", "suphanburi", "suratthani", "surin",
    "tak", "trang", "trat", "ubonratchathani", "udonthani",
    "uthaithani", "uttaradit", "yala", "yasothon",
]

RATE_LIMIT_SECONDS = 0.5
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Google Drive helpers
# ---------------------------------------------------------------------------

def authenticate_drive():
    """Authenticate with Google Drive via OAuth2. Opens browser on first run."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing token...")
            creds.refresh(GoogleRequest())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ ไม่พบ {CREDENTIALS_FILE}")
                print("   กรุณาสร้าง OAuth2 credentials ใน Google Cloud Console")
                print("   → Credentials → Create Credentials → OAuth client ID → Desktop app")
                print("   → Download JSON → บันทึกเป็น credentials.json ใน project root")
                sys.exit(1)

            print("🔐 เปิดเบราว์เซอร์เพื่อ login Google...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("✅ Token saved → ครั้งถัดไปไม่ต้อง login ใหม่")

    service = build("drive", "v3", credentials=creds)
    return service


def find_or_create_folder(service, name, parent_id=None):
    """Find an existing folder or create a new one on Google Drive."""
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"

    results = service.files().list(q=q, fields="files(id, name)", pageSize=1).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create folder
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def file_exists_on_drive(service, name, parent_id):
    """Check if a file with the given name already exists in the folder."""
    q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = service.files().list(q=q, fields="files(id, name, size)", pageSize=1).execute()
    files = results.get("files", [])
    if files:
        return files[0]
    return None


def upload_to_drive(service, local_path, filename, parent_id):
    """Upload a file to Google Drive."""
    metadata = {
        "name": filename,
        "parents": [parent_id],
    }
    media = MediaFileUpload(str(local_path), mimetype="application/pdf", resumable=True)
    file = service.files().create(body=metadata, media_body=media, fields="id,size").execute()
    return file


# ---------------------------------------------------------------------------
# ECT crawling (reused from download_ss518.py)
# ---------------------------------------------------------------------------

def fetch(url, timeout=30, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            return r
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    ⚠️ Failed after {retries} attempts: {e}")
                return None


def extract_pdf_links(html, base_url):
    """Extract all PDF/document download links from page HTML."""
    urls = set()
    for m in re.findall(r'(?:href|src|url)[\s=:]*["\']([^"\']+)["\']', html, re.IGNORECASE):
        urls.add(urljoin(base_url, m))
    for m in re.findall(r'https?://[^\s"\'<>\]\)\\]+', html):
        urls.add(m)
    for m in re.findall(r'/(?:web-upload|mini/+web-upload)/[^\s"\'<>\]\)\\]+', html):
        urls.add(urljoin(base_url, m))

    pdfs = []
    for u in urls:
        lower = u.lower()
        if any(skip in lower for skip in [
            'favicon', 'logo', 'banner', 'thumbnail', '.css', '.js',
            '.woff', 'recaptcha', 'google', 'cloudflare', 'cloudwise'
        ]):
            continue
        if lower.endswith('.pdf') or (
            'file_download' in lower and not lower.endswith(('.js', '.css', '.png', '.jpg'))
        ):
            pdfs.append(u)
    return sorted(set(pdfs))


def safe_filename(url):
    """Create a safe filename from a URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    match = re.search(r'file_download/([a-f0-9]+)', path)
    if match:
        return match.group(1) + ".pdf"
    name = path.split("/")[-1]
    if not name or name == "":
        name = re.sub(r'[^\w.-]', '_', path[-40:]) + ".pdf"
    return name


def download_temp(url, retries=MAX_RETRIES):
    """Download a file to a temp location. Returns (temp_path, size) or (None, error)."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            if r.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                size = 0
                for chunk in r.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                    size += len(chunk)
                tmp.close()
                return tmp.name, size
            elif r.status_code == 404:
                return None, "not_found"
            else:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None, f"error: {e}"
    return None, "failed"


# ---------------------------------------------------------------------------
# Main crawl + upload flow
# ---------------------------------------------------------------------------

def crawl_and_upload_province(service, slug, root_folder_id, do_upload=True, resume=True):
    """Crawl one province → upload PDFs to Google Drive."""
    url = f"https://www.ect.go.th/{slug}/th/election-2026"
    print(f"\n{'='*50}")
    print(f"📍 {slug}: {url}")

    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  ❌ Page failed: {r.status_code if r else 'timeout'}")
        return {"slug": slug, "status": "page_failed", "pdfs": [], "pdf_count": 0}

    html = r.text
    pdfs = extract_pdf_links(html, url)
    print(f"  📄 Found {len(pdfs)} PDF links")

    result = {
        "slug": slug,
        "status": "ok",
        "pdf_count": len(pdfs),
        "pdfs": pdfs,
    }

    if not do_upload or not pdfs:
        if not pdfs:
            print(f"  ⚠️ No PDFs found")
        return result

    # Create province folder on Drive
    province_folder_id = find_or_create_folder(service, slug, root_folder_id)
    print(f"  📁 Drive folder: {slug}/")

    uploaded = 0
    skipped = 0
    failed = 0

    for i, pdf_url in enumerate(pdfs):
        fname = safe_filename(pdf_url)

        # Check if already uploaded (resume support)
        if resume:
            existing = file_exists_on_drive(service, fname, province_folder_id)
            if existing and int(existing.get("size", 0)) > 0:
                skipped += 1
                if skipped <= 3 or (i + 1) == len(pdfs):
                    print(f"  ⏭️  [{i+1}/{len(pdfs)}] {fname} (มีอยู่แล้ว)")
                elif skipped == 4:
                    print(f"  ⏭️  ... (skipping existing files)")
                continue

        # Download to temp
        tmp_path, size_or_err = download_temp(pdf_url)
        if not tmp_path:
            failed += 1
            print(f"  ❌ [{i+1}/{len(pdfs)}] {fname}: {size_or_err}")
            continue

        try:
            # Upload to Drive
            upload_to_drive(service, tmp_path, fname, province_folder_id)
            uploaded += 1
            print(f"  ✅ [{i+1}/{len(pdfs)}] {fname} ({size_or_err:,} bytes)")
        except Exception as e:
            failed += 1
            print(f"  ⚠️ [{i+1}/{len(pdfs)}] Upload failed {fname}: {e}")
        finally:
            # Always delete temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        time.sleep(RATE_LIMIT_SECONDS)

    result["uploaded"] = uploaded
    result["skipped"] = skipped
    result["failed"] = failed
    print(f"  📊 Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ดาวน์โหลดเอกสาร สส.5/18 จากเว็บ กกต. → อัปโหลดไป Google Drive"
    )
    parser.add_argument("--province", nargs="+", help="ระบุจังหวัด (slug)")
    parser.add_argument("--index-only", action="store_true", help="สแกนลิงก์เท่านั้น")
    parser.add_argument("--no-resume", action="store_true", help="อัปโหลดทับไฟล์ที่มีอยู่แล้ว")
    parser.add_argument("--rate-limit", type=float, default=0.5, help="หน่วงเวลา (วินาที)")
    parser.add_argument("--folder-name", default=DRIVE_ROOT_FOLDER,
                        help=f"ชื่อโฟลเดอร์หลักบน Drive (default: {DRIVE_ROOT_FOLDER})")
    args = parser.parse_args()

    global RATE_LIMIT_SECONDS
    RATE_LIMIT_SECONDS = args.rate_limit

    slugs = args.province if args.province else PROVINCE_SLUGS
    do_upload = not args.index_only
    resume = not args.no_resume

    # Authenticate with Google Drive
    print("=" * 60)
    print(" ดาวน์โหลดเอกสาร สส.5/18 → Google Drive")
    print("=" * 60)

    if do_upload:
        service = authenticate_drive()
        root_folder_id = find_or_create_folder(service, args.folder_name)
        print(f"📁 Drive root folder: {args.folder_name}/")
        # Get shareable link
        try:
            meta = service.files().get(fileId=root_folder_id, fields="webViewLink").execute()
            print(f"🔗 {meta.get('webViewLink', '')}")
        except Exception:
            pass
    else:
        service = None
        root_folder_id = None

    print(f"📊 จังหวัด: {len(slugs)}")
    print(f"📦 โหมด: {'สแกนลิงก์เท่านั้น' if not do_upload else 'ดาวน์โหลด + อัปโหลด Drive'}")
    print(f"⏱️  Rate limit: {RATE_LIMIT_SECONDS}s")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    total_pdfs = 0
    total_uploaded = 0
    total_skipped = 0
    total_failed = 0

    start_time = time.time()

    for i, slug in enumerate(slugs):
        print(f"\n[{i+1}/{len(slugs)}]", end="")
        result = crawl_and_upload_province(service, slug, root_folder_id, do_upload, resume)
        all_results.append(result)
        total_pdfs += result.get("pdf_count", 0)
        total_uploaded += result.get("uploaded", 0)
        total_skipped += result.get("skipped", 0)
        total_failed += result.get("failed", 0)

        # Save progress
        index_path = DATA_DIR / "ss518_drive_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            elapsed = time.time() - start_time
            json.dump({
                "drive_folder": args.folder_name,
                "total_provinces": len(slugs),
                "completed": i + 1,
                "total_pdfs": total_pdfs,
                "total_uploaded": total_uploaded,
                "total_skipped": total_skipped,
                "total_failed": total_failed,
                "elapsed_seconds": round(elapsed),
                "provinces": all_results,
            }, f, ensure_ascii=False, indent=2)

        time.sleep(1)

    elapsed = time.time() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    print("\n" + "=" * 60)
    print(" สรุปผลการดาวน์โหลด → Google Drive")
    print("=" * 60)
    print(f"  จังหวัดทั้งหมด: {len(slugs)}")
    print(f"  PDF ทั้งหมด: {total_pdfs}")
    if do_upload:
        print(f"  อัปโหลดใหม่: {total_uploaded}")
        print(f"  ข้ามไฟล์ซ้ำ: {total_skipped}")
        print(f"  ล้มเหลว: {total_failed}")
    print(f"  ใช้เวลา: {mins} นาที {secs} วินาที")
    print(f"\n  📁 Index: {index_path}")
    if do_upload:
        print(f"  📁 Drive: {args.folder_name}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
