#!/usr/bin/env python3
"""
Copy โฟลเดอร์ที่คนอื่นแชร์ → เข้า Drive ของเรา (server-side copy, ไม่ต้อง download)

Usage:
  python scripts/copy_shared_drive.py
"""
import json
import os
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE_FULL = PROJECT_ROOT / "token_full.json"  # separate token for broader scope

# Need full drive scope to read shared files + write to own drive
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Source: shared folder
SOURCE_FOLDER_ID = "1elYwd_ATWpm8q_ZxoxKcXO1TaVF7MElj"

# Destination: My Drive > เลือกตั้ง69
DEST_FOLDER_NAME = "เลือกตั้ง69"


def authenticate():
    """OAuth2 with full Drive scope."""
    creds = None
    if TOKEN_FILE_FULL.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE_FULL), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ ไม่พบ {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE_FULL, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _retry(func, max_retries=5, base_delay=5):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e)
            retryable = any(code in err_str for code in ["500", "503", "429", "Internal Error", "Rate Limit", "userRateLimitExceeded"])
            if not retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"   ⚠️ retry {attempt+1}/{max_retries} in {delay}s: {err_str[:80]}", flush=True)
            time.sleep(delay)


def find_or_create_folder(service, name, parent_id):
    """Find existing folder or create new one."""
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


def get_or_create_dest_folder(service):
    """Get or create 'เลือกตั้ง69' in My Drive root."""
    q = f"name = '{DEST_FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false and 'root' in parents"
    results = _retry(lambda: service.files().list(q=q, fields="files(id)", pageSize=1).execute())
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": DEST_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    return _retry(lambda: service.files().create(body=meta, fields="id").execute())["id"]


def file_exists(service, name, parent_id):
    """Check if a file/folder already exists in destination."""
    q = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    results = _retry(lambda: service.files().list(q=q, fields="files(id, size, mimeType)", pageSize=1).execute())
    files = results.get("files", [])
    return files[0] if files else None


def list_folder(service, folder_id):
    """List all items in a folder."""
    all_files = []
    page_token = None
    while True:
        pt = page_token
        results = _retry(lambda: service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=pt,
        ).execute())
        all_files.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return all_files


def copy_file(service, file_id, name, dest_parent_id):
    """Server-side copy a file to destination folder."""
    body = {"name": name, "parents": [dest_parent_id]}
    return _retry(lambda: service.files().copy(fileId=file_id, body=body, fields="id, size").execute())


def copy_folder_recursive(service, src_folder_id, dest_parent_id, path="", stats=None):
    """Recursively copy folder contents."""
    if stats is None:
        stats = {"files": 0, "folders": 0, "skipped": 0, "failed": 0, "bytes": 0}

    items = list_folder(service, src_folder_id)
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    files = [f for f in items if f["mimeType"] != "application/vnd.google-apps.folder"]

    # Copy files first
    for f in files:
        name = f["name"]
        size = int(f.get("size", 0))

        # Check if already copied
        existing = file_exists(service, name, dest_parent_id)
        if existing:
            stats["skipped"] += 1
            continue

        try:
            copy_file(service, f["id"], name, dest_parent_id)
            stats["files"] += 1
            stats["bytes"] += size
            total = stats["files"] + stats["skipped"]
            if stats["files"] % 10 == 1 or total <= 5:
                size_mb = stats["bytes"] / 1024 / 1024
                print(f"   ✅ [{total}] {path}/{name} ({size:,} bytes) — total: {size_mb:.0f} MB", flush=True)
        except Exception as e:
            stats["failed"] += 1
            print(f"   ❌ {path}/{name}: {e}", flush=True)

        time.sleep(0.1)  # rate limit

    # Then recurse into subfolders
    for folder in sorted(folders, key=lambda f: f["name"]):
        sub_name = folder["name"]
        sub_path = f"{path}/{sub_name}" if path else sub_name
        stats["folders"] += 1
        print(f"   📁 [{stats['folders']}] {sub_path}", flush=True)

        # Create matching folder in destination
        dest_sub = find_or_create_folder(service, sub_name, dest_parent_id)
        copy_folder_recursive(service, folder["id"], dest_sub, sub_path, stats)

    return stats


def count_items(service, folder_id):
    """Quick count of items in a folder (recursive)."""
    count = 0
    items = list_folder(service, folder_id)
    for item in items:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            count += count_items(service, item["id"])
        else:
            count += 1
    return count


def main():
    print("🔐 Authenticating (full Drive scope)...", flush=True)
    service = authenticate()

    # Get source folder info
    src_info = _retry(lambda: service.files().get(fileId=SOURCE_FOLDER_ID, fields="name").execute())
    print(f"📂 Source: {src_info['name']} ({SOURCE_FOLDER_ID})", flush=True)

    # Get/create destination
    dest_id = get_or_create_dest_folder(service)
    print(f"📁 Destination: My Drive > {DEST_FOLDER_NAME} ({dest_id})", flush=True)

    # Start copying
    print(f"\n🚀 เริ่ม copy...\n", flush=True)
    start = time.time()
    stats = copy_folder_recursive(service, SOURCE_FOLDER_ID, dest_id)
    elapsed = time.time() - start

    print(f"\n{'='*50}", flush=True)
    print(f"✅ เสร็จสิ้น! ({elapsed:.0f} วินาที)", flush=True)
    print(f"   📄 Copy ไฟล์: {stats['files']}", flush=True)
    print(f"   📁 สร้างโฟลเดอร์: {stats['folders']}", flush=True)
    print(f"   ⏭️  ข้าม (มีแล้ว): {stats['skipped']}", flush=True)
    print(f"   ❌ ล้มเหลว: {stats['failed']}", flush=True)
    print(f"   💾 ขนาดรวม: {stats['bytes']/1024/1024:.0f} MB", flush=True)


if __name__ == "__main__":
    main()
