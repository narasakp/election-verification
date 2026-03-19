#!/usr/bin/env python3
"""
Backup เอกสาร สส.5/18 จากเว็บ กกต. → Google Drive ของผู้ใช้
ทีละจังหวัด ตามลำดับความผิดปกติ

ขั้นตอน:
1. Scrape หน้ากลาง กกต. ด้วย Playwright → หา Google Drive folder ทุกจังหวัด
2. จับคู่ชื่อจังหวัดทางการ (จาก ECT API) กับ Drive folder
3. Copy ไฟล์จาก Drive กกต. → Drive ผม (ผ่าน API: download → upload)
4. เรียงตามลำดับ anomaly score (จังหวัดน่าสงสัยก่อน)

Usage:
  python scripts/backup_to_drive.py                     # ทุกจังหวัด
  python scripts/backup_to_drive.py --start-from 5      # เริ่มจากลำดับที่ 5
  python scripts/backup_to_drive.py --province บุรีรัมย์  # เฉพาะจังหวัด
  python scripts/backup_to_drive.py --scan-only          # สแกนเท่านั้น
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import threading
from pathlib import Path
from queue import Queue

import requests as http_req

# Google API
try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# Playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ pip install playwright && python -m playwright install chromium")
    sys.exit(1)

# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
ECT_URL = "https://www.ect.go.th/ect_th/th/election-2026"
DRIVE_ROOT_FOLDER = "สส.5_18_ข้อมูลเลือกตั้ง_2569"

# Anomaly ranking order (from province_ranking.txt)
RANKING_ORDER = [
    "บุรีรัมย์", "ตาก", "ชัยภูมิ", "เพชรบูรณ์", "เพชรบุรี",
    "นครราชสีมา", "อุบลราชธานี", "พะเยา", "นครสวรรค์", "อ่างทอง",
    "อุทัยธานี", "สุรินทร์", "เลย", "สุพรรณบุรี", "ระยอง",
    "ศรีสะเกษ", "เชียงใหม่", "แพร่", "เชียงราย", "นครศรีธรรมราช",
    "สระแก้ว", "ชัยนาท", "สุโขทัย", "ระนอง", "ขอนแก่น",
    "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "ลำปาง",
    "แม่ฮ่องสอน", "กาญจนบุรี", "สตูล", "นราธิวาส",
    # No flags (score=0) — still important to backup
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

# All 77 official province names
ALL_PROVINCES = set(RANKING_ORDER)


# ---------------------------------------------------------------------------
# Google Drive auth
# ---------------------------------------------------------------------------
def get_api_key():
    """Get API key from .env for reading public Drive folders."""
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
            creds.refresh(GoogleRequest())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ ไม่พบ {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _retry(func, max_retries=5, base_delay=5):
    """Retry wrapper for transient Google API errors (500, 503, rate limit)."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e)
            retryable = any(code in err_str for code in ["500", "503", "429", "Internal Error", "Rate Limit"])
            if not retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"      ⚠️ API error, retry {attempt+1}/{max_retries} in {delay}s: {err_str[:80]}", flush=True)
            time.sleep(delay)


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
    return _retry(lambda: service.files().create(body=meta, fields="id").execute())["id"]


def file_exists_on_drive(service, name, parent_id):
    q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = _retry(lambda: service.files().list(q=q, fields="files(id,size)", pageSize=1).execute())
    files = results.get("files", [])
    return files[0] if files else None


def upload_file(service, local_path, filename, parent_id):
    meta = {"name": filename, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), mimetype="application/pdf", resumable=True)
    return _retry(lambda: service.files().create(body=meta, media_body=media, fields="id,size").execute())


# ---------------------------------------------------------------------------
# ECT Drive reading (using API key for public read)
# ---------------------------------------------------------------------------
def list_ect_folder(folder_id, api_key):
    """List all files/folders in an ECT shared Drive folder using API key."""
    all_files = []
    page_token = None
    page_num = 0
    while True:
        page_num += 1
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "key": api_key,
            "fields": "nextPageToken, files(id, name, mimeType, size)",
            "pageSize": 1000,
        }
        if page_token:
            params["pageToken"] = page_token
        resp = http_req.get(f"{DRIVE_API_BASE}/files", params=params, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        batch = data.get("files", [])
        all_files.extend(batch)
        print(f"      📂 page {page_num}: +{len(batch)} items (total {len(all_files)})", flush=True)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return all_files


def walk_ect_folder(folder_id, api_key, path="", depth=0):
    """Recursively list all PDFs in an ECT Drive folder."""
    indent = "      " + "  " * depth
    if path:
        print(f"{indent}📁 {path}", flush=True)
    results = []
    items = list_ect_folder(folder_id, api_key)
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    pdfs = [f for f in items if f.get("name", "").lower().endswith(".pdf")]

    if pdfs:
        print(f"{indent}   → {len(pdfs)} PDFs", flush=True)
    for pdf in pdfs:
        results.append({"path": path, "file": pdf})

    for folder in sorted(folders, key=lambda f: f["name"]):
        sub_path = f"{path}/{folder['name']}" if path else folder["name"]
        results.extend(walk_ect_folder(folder["id"], api_key, sub_path, depth + 1))
        time.sleep(0.1)

    return results


def walk_ect_folder_streaming(folder_id, api_key, queue, counter, path="", depth=0):
    """Recursively scan ECT Drive folder, pushing PDFs to queue immediately."""
    try:
        items = list_ect_folder(folder_id, api_key)
    except Exception as e:
        print(f"      ⚠️ scan error at {path}: {e}", flush=True)
        return
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    pdfs = [f for f in items if f.get("name", "").lower().endswith(".pdf")]

    for pdf in pdfs:
        counter["found"] += 1
        queue.put({"path": path, "file": pdf})

    if pdfs and depth <= 3:
        print(f"      📁 {path} → {len(pdfs)} PDFs (total found: {counter['found']})", flush=True)

    for folder in sorted(folders, key=lambda f: f["name"]):
        sub_path = f"{path}/{folder['name']}" if path else folder["name"]
        walk_ect_folder_streaming(folder["id"], api_key, queue, counter, sub_path, depth + 1)
        time.sleep(0.05)


def download_from_drive(file_id, api_key, dest_path, max_retries=4):
    """Download a file from a public Drive folder with retry for SSL errors."""
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


# ---------------------------------------------------------------------------
# Scrape ECT central page for province → Drive folder mapping
# ---------------------------------------------------------------------------
def scrape_ect_mapping():
    """Use Playwright to extract province → Drive folder mapping."""
    cache_path = DATA_DIR / "ect_drive_mapping_verified.json"
    if cache_path.exists():
        data = json.load(open(cache_path, encoding="utf-8"))
        if len(data) >= 75:
            print(f"📋 ใช้ mapping ที่ cache ไว้ ({len(data)} จังหวัด)")
            return data

    print(f"🌐 กำลังสแกนหน้า กกต. ด้วย Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(ECT_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        cells = page.eval_on_selector_all("td", """
            cells => cells.map(td => {
                const link = td.querySelector('a[href*="drive.google.com"]');
                if (!link) return null;
                return { text: td.innerText.trim(), href: link.href };
            }).filter(x => x !== null)
        """)
        browser.close()

    mapping = []
    for cell in cells:
        folder_match = re.search(r'folders/([a-zA-Z0-9_-]+)', cell["href"])
        if not folder_match:
            continue
        folder_id = folder_match.group(1)
        text = cell["text"].strip()

        # Match to official province name
        province = None
        for prov in ALL_PROVINCES:
            if prov in text:
                province = prov
                break
        if not province:
            # Try partial match (for truncated names)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                if len(line) < 2:
                    continue
                for prov in ALL_PROVINCES:
                    if line in prov and len(line) >= 2:
                        province = prov
                        break
                if province:
                    break

        if province and not any(m["folder_id"] == folder_id for m in mapping):
            mapping.append({
                "province": province,
                "folder_id": folder_id,
                "drive_url": cell["href"].split("?")[0],
            })

    # Report
    found = {m["province"] for m in mapping}
    missing = [p for p in ALL_PROVINCES if p not in found]

    print(f"✅ พบ {len(mapping)} จังหวัด")
    if missing:
        print(f"❌ ไม่พบ {len(missing)} จังหวัด: {', '.join(missing)}")

    # Save verified mapping
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    return mapping


# ---------------------------------------------------------------------------
# Main backup logic
# ---------------------------------------------------------------------------
def count_my_drive_pdfs(service, folder_id, depth=0):
    """Recursively count PDFs in user's Drive folder."""
    count = 0
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        items = results.get("files", [])
        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                count += count_my_drive_pdfs(service, item["id"], depth + 1)
            elif item["name"].lower().endswith(".pdf"):
                count += 1
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return count


def verify_province(service, province_name, my_folder_id, expected_count):
    """Verify that all PDFs were copied to user's Drive."""
    print(f"   🔍 ตรวจสอบความครบถ้วน...", flush=True)
    actual = count_my_drive_pdfs(service, my_folder_id)
    match = actual >= expected_count
    pct = (actual / expected_count * 100) if expected_count > 0 else 100
    if match:
        print(f"   ✅ ยืนยัน: {actual}/{expected_count} ไฟล์ ({pct:.0f}%) — ครบถ้วน", flush=True)
    else:
        print(f"   ⚠️ ยังไม่ครบ: {actual}/{expected_count} ไฟล์ ({pct:.1f}%)", flush=True)
    return {"expected": expected_count, "actual": actual, "complete": match, "percent": round(pct, 1)}


def _uploader_worker(service, api_key, queue, prov_folder_id, stats, lock, stop_event):
    """Worker thread: take PDFs from queue, download → upload."""
    folder_cache = {}  # path → folder_id cache

    while not (stop_event.is_set() and queue.empty()):
        try:
            item = queue.get(timeout=2)
        except Exception:
            continue

        pdf = item["file"]
        sub_path = item["path"]
        fname = pdf["name"]

        try:
            # Resolve target folder (with cache)
            target_folder = prov_folder_id
            if sub_path:
                with lock:
                    if sub_path in folder_cache:
                        target_folder = folder_cache[sub_path]
                    else:
                        for part in sub_path.split("/"):
                            cache_key = f"{target_folder}/{part}"
                            if cache_key in folder_cache:
                                target_folder = folder_cache[cache_key]
                            else:
                                target_folder = find_or_create_folder(service, part, target_folder)
                                folder_cache[cache_key] = target_folder
                        folder_cache[sub_path] = target_folder

            # Check if already exists
            existing = file_exists_on_drive(service, fname, target_folder)
            if existing and int(existing.get("size", 0)) > 0:
                with lock:
                    stats["skipped"] += 1
                    n = stats["uploaded"] + stats["skipped"] + stats["failed"]
                queue.task_done()
                continue

            # Download → upload → delete
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(tmp_fd)
            try:
                download_from_drive(pdf["id"], api_key, tmp_path)
                upload_file(service, tmp_path, fname, target_folder)
                size = os.path.getsize(tmp_path)
                with lock:
                    stats["uploaded"] += 1
                    n = stats["uploaded"] + stats["skipped"] + stats["failed"]
                    if stats["uploaded"] % 5 == 1 or n <= 10:
                        print(f"   ✅ [{n}/{stats['found']}] {fname} ({size:,} bytes)", flush=True)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            with lock:
                stats["failed"] += 1
                n = stats["uploaded"] + stats["skipped"] + stats["failed"]
                print(f"   ❌ [{n}] {fname}: {e}", flush=True)

        queue.task_done()
        time.sleep(0.1)


def backup_province(service, api_key, province_name, ect_folder_id, my_root_id, rank, num_workers=1):
    """Backup one province with parallel scan + upload."""
    print(f"\n{'='*60}", flush=True)
    print(f"📍 #{rank} {province_name} (workers={num_workers})", flush=True)
    print(f"   ECT folder: {ect_folder_id}", flush=True)

    prov_folder_id = find_or_create_folder(service, province_name, my_root_id)

    # Shared state
    pdf_queue = Queue(maxsize=100)
    stats = {"found": 0, "uploaded": 0, "skipped": 0, "failed": 0}
    lock = threading.Lock()
    stop_event = threading.Event()

    # Start uploader workers
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(
            target=_uploader_worker,
            args=(service, api_key, pdf_queue, prov_folder_id, stats, lock, stop_event),
            daemon=True,
        )
        t.start()
        workers.append(t)

    # Scanner runs in main thread — feeds queue
    scan_start = time.time()
    counter = {"found": 0}
    try:
        walk_ect_folder_streaming(ect_folder_id, api_key, pdf_queue, counter)
    except Exception as e:
        print(f"   ❌ สแกนล้มเหลว: {e}", flush=True)

    stats["found"] = counter["found"]
    scan_time = time.time() - scan_start
    print(f"   📄 สแกนเสร็จ: {counter['found']} PDFs ({scan_time:.0f}s) — รออัปโหลดที่เหลือ...", flush=True)

    # Signal workers to stop after queue is drained
    stop_event.set()
    pdf_queue.join()
    for t in workers:
        t.join(timeout=10)

    total = stats["found"]
    uploaded = stats["uploaded"]
    skipped = stats["skipped"]
    failed = stats["failed"]

    print(f"   📊 รอบ 1: อัปโหลด {uploaded}, ข้าม {skipped}, ล้มเหลว {failed}", flush=True)

    if total == 0:
        return {"province": province_name, "status": "empty", "pdf_count": 0}

    # ---- Retry rounds: re-scan + upload missing until fail=0 ----
    MAX_RETRY_ROUNDS = 3
    retry_round = 0
    total_uploaded = uploaded
    total_failed = failed

    while failed > 0 and retry_round < MAX_RETRY_ROUNDS:
        retry_round += 1
        delay = 30 * retry_round  # 30s, 60s, 90s
        print(f"\n   🔄 Retry รอบ {retry_round}/{MAX_RETRY_ROUNDS} — รอ {delay}s ก่อน retry {failed} ไฟล์ที่ fail...", flush=True)
        time.sleep(delay)

        # Re-scan + upload (will skip already-uploaded files)
        pdf_queue2 = Queue(maxsize=100)
        stats2 = {"found": 0, "uploaded": 0, "skipped": 0, "failed": 0}
        lock2 = threading.Lock()
        stop_event2 = threading.Event()

        workers2 = []
        for _ in range(num_workers):
            t = threading.Thread(
                target=_uploader_worker,
                args=(service, api_key, pdf_queue2, prov_folder_id, stats2, lock2, stop_event2),
                daemon=True,
            )
            t.start()
            workers2.append(t)

        counter2 = {"found": 0}
        try:
            walk_ect_folder_streaming(ect_folder_id, api_key, pdf_queue2, counter2)
        except Exception as e:
            print(f"   ❌ สแกนล้มเหลว (retry): {e}", flush=True)

        stats2["found"] = counter2["found"]
        stop_event2.set()
        pdf_queue2.join()
        for t in workers2:
            t.join(timeout=10)

        print(f"   📊 Retry รอบ {retry_round}: อัปโหลดเพิ่ม {stats2['uploaded']}, ข้าม {stats2['skipped']}, ล้มเหลว {stats2['failed']}", flush=True)

        total_uploaded += stats2["uploaded"]

        # No progress — stop retrying (files truly unavailable)
        if stats2["uploaded"] == 0 and stats2["failed"] >= failed:
            print(f"   ⛔ ไม่มีความคืบหน้า — หยุด retry (ไฟล์ {stats2['failed']} ชิ้น โหลดไม่ได้จริง ๆ)", flush=True)
            failed = stats2["failed"]
            break

        failed = stats2["failed"]
        if failed == 0:
            print(f"   🎉 Retry สำเร็จ! ไม่มีไฟล์ fail เหลือแล้ว", flush=True)

    # ---- Final verify ----
    verify = verify_province(service, province_name, prov_folder_id, total)

    return {
        "province": province_name,
        "status": "ok" if verify["complete"] else "incomplete",
        "pdf_count": total,
        "uploaded": total_uploaded,
        "skipped": skipped,
        "failed": failed,
        "retry_rounds": retry_round,
        "verify": verify,
    }


def main():
    parser = argparse.ArgumentParser(description="Backup เอกสาร กกต. → Google Drive")
    parser.add_argument("--start-from", type=int, default=1, help="เริ่มจากลำดับที่ N")
    parser.add_argument("--province", help="เฉพาะจังหวัด (ชื่อไทย)")
    parser.add_argument("--scan-only", action="store_true", help="สแกนเท่านั้น ไม่ copy")
    parser.add_argument("--folder-name", default=DRIVE_ROOT_FOLDER, help="ชื่อโฟลเดอร์หลัก")
    args = parser.parse_args()

    print("=" * 60)
    print(" 📦 Backup เอกสาร สส.5/18 กกต. → Google Drive")
    print("=" * 60)

    # 1. Get API key (for reading ECT public folders)
    api_key = get_api_key()
    if not api_key:
        print("❌ ต้องตั้งค่า GOOGLE_CLOUD_API_KEY ใน .env")
        sys.exit(1)
    print(f"🔑 API Key: {api_key[:15]}...")

    # 2. OAuth2 auth (for writing to user's Drive)
    if not args.scan_only:
        service = authenticate_drive()
        root_id = find_or_create_folder(service, args.folder_name)
        print(f"📁 My Drive root: {args.folder_name}/")
    else:
        service = None
        root_id = None

    # 3. Scrape ECT page for province → Drive folder mapping
    mapping = scrape_ect_mapping()
    folder_map = {m["province"]: m["folder_id"] for m in mapping}

    # 4. Build ordered list
    if args.province:
        ordered = [args.province]
    else:
        ordered = RANKING_ORDER

    # Filter to those with Drive folders
    available = [(i + 1, prov) for i, prov in enumerate(ordered) if prov in folder_map]
    missing = [prov for prov in ordered if prov not in folder_map]

    print(f"\n📊 สรุป:")
    print(f"   จังหวัดใน ranking: {len(ordered)}")
    print(f"   มี Drive folder: {len(available)}")
    if missing:
        print(f"   ❌ ไม่พบ Drive folder: {', '.join(missing)}")

    # Apply start-from filter
    if args.start_from > 1:
        available = [(rank, prov) for rank, prov in available if rank >= args.start_from]
        print(f"   เริ่มจากลำดับที่: {args.start_from}")

    print(f"   จะดำเนินการ: {len(available)} จังหวัด")
    print("=" * 60)

    if args.scan_only:
        print("\n🔍 โหมดสแกน — แสดงจำนวน PDF ในแต่ละจังหวัด:")
        for rank, prov in available:
            fid = folder_map[prov]
            try:
                pdfs = walk_ect_folder(fid, api_key)
                print(f"  #{rank:2d} {prov:20s} → {len(pdfs)} PDFs")
            except Exception as e:
                print(f"  #{rank:2d} {prov:20s} → ❌ {e}")
            time.sleep(0.2)
        return

    # 5. Backup each province
    results = []
    start_time = time.time()

    for rank, prov in available:
        fid = folder_map[prov]
        result = backup_province(service, api_key, prov, fid, root_id, rank)
        results.append(result)

        # Save progress
        progress_path = DATA_DIR / "backup_progress.json"
        elapsed = time.time() - start_time
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump({
                "drive_folder": args.folder_name,
                "total_planned": len(available),
                "completed": len(results),
                "elapsed_seconds": round(elapsed),
                "results": results,
            }, f, ensure_ascii=False, indent=2)

        time.sleep(1)  # Rate limit between provinces

    # Summary
    elapsed = time.time() - start_time
    total_pdfs = sum(r.get("pdf_count", 0) for r in results)
    total_uploaded = sum(r.get("uploaded", 0) for r in results)
    total_skipped = sum(r.get("skipped", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)

    print(f"\n{'='*60}")
    print(f" สรุปผล Backup → Google Drive")
    print(f"{'='*60}")
    print(f"  จังหวัด: {len(results)}")
    print(f"  PDF ทั้งหมด: {total_pdfs}")
    print(f"  อัปโหลดใหม่: {total_uploaded}")
    print(f"  ข้ามไฟล์ซ้ำ: {total_skipped}")
    print(f"  ล้มเหลว: {total_failed}")
    print(f"  เวลา: {int(elapsed//60)} นาที {int(elapsed%60)} วินาที")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
