#!/usr/bin/env python3
"""
ตรวจสอบ + retry จังหวัดที่ backup ไปแล้ว
ใช้แยกจาก backup_to_drive.py ที่กำลังรันอยู่
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import requests as http_req
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_ROOT_FOLDER = "สส.5_18_ข้อมูลเลือกตั้ง_2569"


def get_api_key():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in open(env_path):
            line = line.strip()
            if line.startswith("GOOGLE_CLOUD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GOOGLE_CLOUD_API_KEY")


def authenticate_drive():
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _retry(func, max_retries=5, base_delay=5):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e)
            retryable = any(code in err_str for code in ["500", "503", "429", "Internal Error", "Rate Limit"])
            if not retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"   ⚠️ retry {attempt+1}/{max_retries} in {delay}s: {err_str[:80]}", flush=True)
            time.sleep(delay)


def find_folder(service, name, parent_id):
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and '{parent_id}' in parents"
    results = _retry(lambda: service.files().list(q=q, fields="files(id)", pageSize=1).execute())
    files = results.get("files", [])
    return files[0]["id"] if files else None


def find_or_create_folder(service, name, parent_id):
    existing = find_folder(service, name, parent_id)
    if existing:
        return existing
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    return _retry(lambda: service.files().create(body=meta, fields="id").execute())["id"]


_pdf_counter = {"total": 0, "folders": 0}

def count_my_drive_pdfs(service, folder_id, depth=0):
    count = 0
    page_token = None
    while True:
        pt = page_token
        results = _retry(lambda: service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1000, pageToken=pt,
        ).execute())
        for item in results.get("files", []):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                _pdf_counter["folders"] += 1
                count += count_my_drive_pdfs(service, item["id"], depth + 1)
            elif item["name"].lower().endswith(".pdf"):
                count += 1
                _pdf_counter["total"] += 1
                if _pdf_counter["total"] % 200 == 0:
                    print(f"      ... นับได้ {_pdf_counter['total']} PDFs ({_pdf_counter['folders']} folders)", flush=True)
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return count


def list_ect_folder(folder_id, api_key):
    all_files = []
    page_token = None
    while True:
        url = f"{DRIVE_API_BASE}/files"
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "key": api_key, "pageSize": 1000,
            "fields": "nextPageToken, files(id, name, mimeType, size)",
        }
        if page_token:
            params["pageToken"] = page_token
        resp = http_req.get(url, params=params, timeout=30)
        data = resp.json()
        all_files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.1)
    return all_files


def walk_ect_folder(folder_id, api_key, path="", depth=0):
    results = []
    items = list_ect_folder(folder_id, api_key)
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    pdfs = [f for f in items if f.get("name", "").lower().endswith(".pdf")]
    for pdf in pdfs:
        results.append({"path": path, "file": pdf})
    for folder in sorted(folders, key=lambda f: f["name"]):
        sub_path = f"{path}/{folder['name']}" if path else folder["name"]
        results.extend(walk_ect_folder(folder["id"], api_key, sub_path, depth + 1))
        time.sleep(0.05)
    return results


def file_exists_on_drive(service, name, parent_id):
    q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = _retry(lambda: service.files().list(q=q, fields="files(id,size)", pageSize=1).execute())
    files = results.get("files", [])
    return files[0] if files else None


def download_from_drive(file_id, api_key, dest_path, max_retries=4):
    url = f"{DRIVE_API_BASE}/files/{file_id}?alt=media&key={api_key}"
    for attempt in range(max_retries):
        try:
            resp = http_req.get(url, stream=True, timeout=120)
            if resp.status_code != 200:
                raise Exception(f"Download failed {resp.status_code}")
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    f.write(chunk)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def upload_file(service, local_path, filename, parent_id):
    meta = {"name": filename, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), mimetype="application/pdf", resumable=True)
    return _retry(lambda: service.files().create(body=meta, media_body=media, fields="id,size").execute())


def get_mapping():
    cache = DATA_DIR / "ect_drive_mapping_verified.json"
    data = json.load(open(cache, encoding="utf-8"))
    return {item["province"]: item["folder_id"] for item in data}


def get_root_folder_id(service):
    q = f"name = '{DRIVE_ROOT_FOLDER}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and 'root' in parents"
    results = _retry(lambda: service.files().list(q=q, fields="files(id)", pageSize=1).execute())
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    return None


def verify_province(service, province_name, root_id, ect_count):
    prov_folder = find_folder(service, province_name, root_id)
    if not prov_folder:
        print(f"   ❌ ไม่พบโฟลเดอร์ {province_name} ใน Drive ของคุณ", flush=True)
        return None
    actual = count_my_drive_pdfs(service, prov_folder)
    pct = (actual / ect_count * 100) if ect_count > 0 else 100
    if actual >= ect_count:
        print(f"   ✅ {province_name}: {actual}/{ect_count} ({pct:.0f}%) — ครบ!", flush=True)
    else:
        print(f"   ⚠️ {province_name}: {actual}/{ect_count} ({pct:.1f}%) — ขาด {ect_count - actual} ไฟล์", flush=True)
    return {"province": province_name, "actual": actual, "expected": ect_count, "complete": actual >= ect_count}


def retry_province(service, api_key, province_name, ect_folder_id, root_id):
    """Re-scan ECT folder and upload only missing files."""
    print(f"\n🔄 Retry: {province_name}", flush=True)

    prov_folder_id = find_or_create_folder(service, province_name, root_id)

    # Scan all PDFs from ECT source
    print(f"   📡 สแกน ECT folder...", flush=True)
    all_pdfs = walk_ect_folder(ect_folder_id, api_key)
    total = len(all_pdfs)
    print(f"   📄 พบ {total} PDFs จาก ECT", flush=True)

    uploaded = 0
    skipped = 0
    failed = 0

    for i, item in enumerate(all_pdfs):
        pdf = item["file"]
        sub_path = item["path"]
        fname = pdf["name"]

        # Create subfolder if needed
        target_folder = prov_folder_id
        if sub_path:
            for part in sub_path.split("/"):
                target_folder = find_or_create_folder(service, part, target_folder)

        # Check if already exists
        existing = file_exists_on_drive(service, fname, target_folder)
        if existing and int(existing.get("size", 0)) > 0:
            skipped += 1
            continue

        # Download → upload → delete
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(tmp_fd)
            download_from_drive(pdf["id"], api_key, tmp_path)
            upload_file(service, tmp_path, fname, target_folder)
            uploaded += 1
            size = os.path.getsize(tmp_path)
            print(f"   ✅ [{uploaded}] {fname} ({size:,} bytes)", flush=True)
        except Exception as e:
            failed += 1
            print(f"   ❌ {fname}: {e}", flush=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        time.sleep(0.3)

    print(f"\n   📊 สรุป: อัปโหลดเพิ่ม {uploaded}, ข้าม {skipped}, ล้มเหลว {failed}", flush=True)

    # Verify
    actual = count_my_drive_pdfs(service, prov_folder_id)
    pct = (actual / total * 100) if total > 0 else 100
    status = "✅ ครบ!" if actual >= total else f"⚠️ {actual}/{total} ({pct:.1f}%)"
    print(f"   🔍 ยืนยัน: {actual}/{total} — {status}", flush=True)
    return {"uploaded": uploaded, "skipped": skipped, "failed": failed, "actual": actual, "expected": total}


RANKING_ORDER = [
    "บุรีรัมย์", "ตาก", "ชัยภูมิ", "เพชรบูรณ์", "เพชรบุรี",
    "นครราชสีมา", "อุบลราชธานี", "พะเยา", "นครสวรรค์", "อ่างทอง",
    "อุทัยธานี", "สุรินทร์", "เลย", "สุพรรณบุรี", "ระยอง",
    "ศรีสะเกษ", "เชียงใหม่", "แพร่", "เชียงราย", "นครศรีธรรมราช",
    "สระแก้ว", "ชัยนาท", "สุโขทัย", "ระนอง", "ขอนแก่น",
    "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "ลำปาง",
    "แม่ฮ่องสอน", "กาญจนบุรี", "สตูล", "นราธิวาส",
    "กรุงเทพมหานคร", "พิจิตร", "สมุทรปราการ", "หนองบัวลำภู", "ปัตตานี",
    "พระนครศรีอยุธยา", "ลพบุรี", "สระบุรี", "ชลบุรี", "จันทบุรี",
    "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "นครนายก", "สงขลา",
    "ยโสธร", "อำนาจเจริญ", "บึงกาฬ", "นนทบุรี", "อุดรธานี",
    "หนองคาย", "มหาสารคาม", "มุกดาหาร", "ลำพูน", "อุตรดิตถ์",
    "น่าน", "กำแพงเพชร", "พิษณุโลก", "ประจวบคีรีขันธ์", "ราชบุรี",
    "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "ปทุมธานี", "กระบี่",
    "พังงา", "ภูเก็ต", "สิงห์บุรี", "ชุมพร", "ตรัง",
    "พัทลุง", "ยะลา", "สุราษฎร์ธานี",
]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, default=1, help="ลำดับจังหวัด (1=บุรีรัมย์, 2=ตาก, ...)")
    parser.add_argument("--max-rounds", type=int, default=3, help="จำนวนรอบ retry สูงสุด")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("❌ ไม่พบ API key")
        sys.exit(1)

    service = authenticate_drive()
    mapping = get_mapping()
    root_id = get_root_folder_id(service)
    if not root_id:
        print("❌ ไม่พบ root folder บน Drive")
        sys.exit(1)

    print(f"🗂️ Root folder: {DRIVE_ROOT_FOLDER} ({root_id})\n", flush=True)

    province = RANKING_ORDER[args.index - 1]
    print(f"🎯 จังหวัด: #{args.index} {province}", flush=True)
    ect_fid = mapping.get(province)
    if not ect_fid:
        print(f"❌ ไม่พบ mapping สำหรับ {province}")
        sys.exit(1)

    # Retry multiple rounds until fail=0 or no progress
    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'='*50}", flush=True)
        print(f"� รอบ {round_num}/{args.max_rounds}: {province}", flush=True)
        print(f"{'='*50}", flush=True)

        result = retry_province(service, api_key, province, ect_fid, root_id)

        if result["failed"] == 0:
            print(f"\n🎉 สำเร็จ! {province} ครบทุกไฟล์แล้ว", flush=True)
            break

        if result["uploaded"] == 0 and result["failed"] > 0:
            print(f"\n⛔ ไม่มีความคืบหน้า — ไฟล์ {result['failed']} ชิ้นโหลดไม่ได้จริง ๆ", flush=True)
            break

        if round_num < args.max_rounds:
            delay = 60 * round_num
            print(f"\n⏳ รอ {delay}s ก่อน retry รอบถัดไป...", flush=True)
            time.sleep(delay)


if __name__ == "__main__":
    main()
