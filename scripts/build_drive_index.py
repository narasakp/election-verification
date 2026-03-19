#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สร้าง Drive Index สำหรับ OCR Review System
สแกนจาก Google Drive backup ของเรา (ไม่พึ่ง กกต.)
ผลลัพธ์: data/drive_index_{province_slug}.json

Usage:
  python scripts/build_drive_index.py --provinces 2 3 4
  (2=ตาก, 3=ชัยภูมิ, 4=เพชรบูรณ์)

  python scripts/build_drive_index.py --all
  (สแกนทุกจังหวัดที่มีบน Drive)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token_full.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
DRIVE_ROOT_FOLDER = "สส.5_18_ข้อมูลเลือกตั้ง_2569"

PROVINCE_SLUGS = {
    'กรุงเทพมหานคร': 'bangkok', 'กระบี่': 'krabi', 'กาญจนบุรี': 'kanchanaburi',
    'กาฬสินธุ์': 'kalasin', 'กำแพงเพชร': 'kamphaengphet', 'ขอนแก่น': 'khonkaen',
    'จันทบุรี': 'chanthaburi', 'ฉะเชิงเทรา': 'chachoengsao', 'ชลบุรี': 'chonburi',
    'ชัยนาท': 'chainat', 'ชัยภูมิ': 'chaiyaphum', 'ชุมพร': 'chumphon',
    'เชียงราย': 'chiangrai', 'เชียงใหม่': 'chiangmai', 'ตรัง': 'trang',
    'ตราด': 'trat', 'ตาก': 'tak', 'นครนายก': 'nakhonnayok',
    'นครปฐม': 'nakhonpathom', 'นครพนม': 'nakhonphanom', 'นครราชสีมา': 'nakhonratchasima',
    'นครศรีธรรมราช': 'nakhonsithammarat', 'นครสวรรค์': 'nakhonsawan', 'นนทบุรี': 'nonthaburi',
    'นราธิวาส': 'narathiwat', 'น่าน': 'nan', 'บึงกาฬ': 'buengkan',
    'บุรีรัมย์': 'buriram', 'ปทุมธานี': 'pathumthani', 'ประจวบคีรีขันธ์': 'prachuapkhirikhan',
    'ปราจีนบุรี': 'prachinburi', 'ปัตตานี': 'pattani', 'พระนครศรีอยุธยา': 'ayutthaya',
    'พะเยา': 'phayao', 'พังงา': 'phangnga', 'พัทลุง': 'phatthalung',
    'พิจิตร': 'phichit', 'พิษณุโลก': 'phitsanulok', 'เพชรบุรี': 'phetchaburi',
    'เพชรบูรณ์': 'phetchabun', 'แพร่': 'phrae', 'ภูเก็ต': 'phuket',
    'มหาสารคาม': 'mahasarakham', 'มุกดาหาร': 'mukdahan', 'แม่ฮ่องสอน': 'maehongson',
    'ยโสธร': 'yasothon', 'ยะลา': 'yala', 'ร้อยเอ็ด': 'roiet',
    'ระนอง': 'ranong', 'ระยอง': 'rayong', 'ราชบุรี': 'ratchaburi',
    'ลพบุรี': 'lopburi', 'ลำปาง': 'lampang', 'ลำพูน': 'lamphun',
    'เลย': 'loei', 'ศรีสะเกษ': 'sisaket', 'สกลนคร': 'sakonnakhon',
    'สงขลา': 'songkhla', 'สตูล': 'satun', 'สมุทรปราการ': 'samutprakan',
    'สมุทรสงคราม': 'samutsongkhram', 'สมุทรสาคร': 'samutsakhon',
    'สระแก้ว': 'sakaeo', 'สระบุรี': 'saraburi', 'สิงห์บุรี': 'singburi',
    'สุโขทัย': 'sukhothai', 'สุพรรณบุรี': 'suphanburi', 'สุราษฎร์ธานี': 'suratthani',
    'สุรินทร์': 'surin', 'หนองคาย': 'nongkhai', 'หนองบัวลำภู': 'nongbualamphu',
    'อ่างทอง': 'angthong', 'อำนาจเจริญ': 'amnatcharoen', 'อุดรธานี': 'udonthani',
    'อุตรดิตถ์': 'uttaradit', 'อุทัยธานี': 'uthaithani', 'อุบลราชธานี': 'ubonratchathani',
}

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


# ---------------------------------------------------------------------------
# Google Drive helpers
# ---------------------------------------------------------------------------
def authenticate():
    """OAuth2 auth using token_full.json (full drive scope)."""
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
    """Retry wrapper for Drive API calls."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e)
            retryable = any(s in err_str for s in ["500", "503", "429", "Rate Limit", "Internal Error"])
            if not retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"   ⚠️  API error, retry {attempt+1}/{max_retries} in {delay}s: {err_str[:80]}", flush=True)
            time.sleep(delay)


def find_root_folder(service):
    """Find the root backup folder on user's Drive."""
    result = _retry(lambda: service.files().list(
        q=f"name = '{DRIVE_ROOT_FOLDER}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id, name)",
        spaces="drive",
    ).execute())
    files = result.get("files", [])
    if not files:
        return None
    return files[0]["id"]


def find_province_folder(service, province_name, root_id):
    """Find a province folder inside root."""
    result = _retry(lambda: service.files().list(
        q=f"name = '{province_name}' and '{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id, name)",
        spaces="drive",
    ).execute())
    files = result.get("files", [])
    return files[0]["id"] if files else None


def walk_drive_folder(service, folder_id, path_parts=None, depth=0):
    """
    Recursively walk a Drive folder and yield PDF file info.
    Yields: (path_parts_list, file_dict)
    where file_dict = {id, name, size, mimeType}
    """
    if path_parts is None:
        path_parts = []

    page_token = None
    while True:
        result = _retry(lambda: service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=page_token,
            spaces="drive",
        ).execute())

        items = result.get("files", [])
        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                # Recurse into subfolder
                sub_path = path_parts + [item["name"]]
                yield from walk_drive_folder(service, item["id"], sub_path, depth + 1)
            elif item["name"].lower().endswith(".pdf"):
                yield (path_parts, {
                    "id": item["id"],
                    "name": item["name"],
                    "size": int(item.get("size", 0)),
                })

        page_token = result.get("nextPageToken")
        if not page_token:
            break


def parse_constituency(path_parts, filename):
    """Try to detect constituency number from path or filename."""
    for part in path_parts:
        m = re.search(r'เขต(?:เลือกตั้ง)?(?:ที่)?\s*(\d+)', part)
        if m:
            return int(m.group(1))
    # Try filename
    m = re.search(r'เขต(?:เลือกตั้ง)?(?:ที่)?\s*(\d+)', filename)
    if m:
        return int(m.group(1))
    return None


def build_index_for_province(service, province, province_folder_id):
    """
    Scan all PDFs in a province folder and build an index.
    Returns list of dicts with file info + metadata.
    """
    slug = PROVINCE_SLUGS.get(province, province)
    print(f"\n📂 สแกน: {province} ({slug})", flush=True)
    print(f"   Folder ID: {province_folder_id}", flush=True)

    index = []
    count = 0

    for path_parts, file_info in walk_drive_folder(service, province_folder_id):
        constituency = parse_constituency(path_parts, file_info["name"])
        entry = {
            "file_id": file_info["id"],
            "name": file_info["name"],
            "size": file_info["size"],
            "path": "/".join(path_parts) if path_parts else "",
            "province": province,
            "province_slug": slug,
            "constituency": constituency,
            # URLs for direct access (our Drive, not กกต.)
            "view_url": f"https://drive.google.com/file/d/{file_info['id']}/view",
            "preview_url": f"https://drive.google.com/file/d/{file_info['id']}/preview",
            "download_url": f"https://drive.google.com/uc?id={file_info['id']}&export=download",
        }
        index.append(entry)
        count += 1
        if count % 100 == 0:
            print(f"   📊 {count} PDFs...", flush=True)

    print(f"   ✅ รวม {count} PDFs", flush=True)

    # Sort by path + name
    index.sort(key=lambda x: (x["path"], x["name"]))

    # Summary
    constituencies = set(e["constituency"] for e in index if e["constituency"] is not None)
    print(f"   📊 เขตเลือกตั้ง: {sorted(constituencies) if constituencies else 'ไม่ระบุ'}", flush=True)

    return index


def save_index(index, province, slug):
    """Save index to data/drive_index_{slug}.json"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"drive_index_{slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"   💾 บันทึก: {out_path} ({len(index)} entries)", flush=True)
    return out_path


def save_combined_index(all_indices):
    """Save a combined index for all provinces."""
    combined = []
    for idx in all_indices:
        combined.extend(idx)
    out_path = DATA_DIR / "drive_index_all.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Combined index: {out_path} ({len(combined)} entries)", flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="สร้าง Drive Index สำหรับ OCR Review")
    parser.add_argument("--provinces", nargs="+", type=int,
                        help="ลำดับจังหวัด (1=บุรีรัมย์, 2=ตาก, 3=ชัยภูมิ, 4=เพชรบูรณ์)")
    parser.add_argument("--all", action="store_true",
                        help="สแกนทุกจังหวัดที่มีบน Drive")
    args = parser.parse_args()

    if not args.provinces and not args.all:
        # Default: 3 provinces ที่ครบ 100%
        args.provinces = [2, 3, 4]
        print("📋 Default: ตาก(2), ชัยภูมิ(3), เพชรบูรณ์(4)", flush=True)

    print("🔐 เชื่อมต่อ Google Drive (OAuth)...", flush=True)
    service = authenticate()

    # Find root folder
    root_id = find_root_folder(service)
    if not root_id:
        print(f"❌ ไม่พบโฟลเดอร์ '{DRIVE_ROOT_FOLDER}' บน Drive ของคุณ")
        sys.exit(1)
    print(f"🗂️  Root: {DRIVE_ROOT_FOLDER} ({root_id})\n", flush=True)

    # Determine which provinces to scan
    if args.all:
        # List all province folders in root
        result = _retry(lambda: service.files().list(
            q=f"'{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(id, name)",
            pageSize=100,
            spaces="drive",
        ).execute())
        province_folders = {f["name"]: f["id"] for f in result.get("files", [])}
        target_provinces = [(name, fid) for name, fid in province_folders.items()
                           if name in PROVINCE_SLUGS]
        target_provinces.sort(key=lambda x: RANKING_ORDER.index(x[0])
                             if x[0] in RANKING_ORDER else 999)
    else:
        target_provinces = []
        for idx in args.provinces:
            province = RANKING_ORDER[idx - 1]
            fid = find_province_folder(service, province, root_id)
            if fid:
                target_provinces.append((province, fid))
            else:
                print(f"⚠️  ไม่พบโฟลเดอร์ '{province}' บน Drive", flush=True)

    if not target_provinces:
        print("❌ ไม่มีจังหวัดที่จะสแกน")
        sys.exit(1)

    print(f"🎯 จังหวัดที่จะสแกน: {', '.join(name for name, _ in target_provinces)}", flush=True)

    # Scan each province
    all_indices = []
    for province, folder_id in target_provinces:
        slug = PROVINCE_SLUGS.get(province, province)
        index = build_index_for_province(service, province, folder_id)
        save_index(index, province, slug)
        all_indices.append(index)

    # Save combined
    if len(all_indices) > 1:
        save_combined_index(all_indices)

    # Summary
    print(f"\n{'='*50}", flush=True)
    print(f"✅ สร้าง Drive Index สำเร็จ!", flush=True)
    total = sum(len(idx) for idx in all_indices)
    print(f"   📊 รวม {total} PDFs จาก {len(target_provinces)} จังหวัด", flush=True)
    for idx in all_indices:
        if idx:
            p = idx[0]["province"]
            s = idx[0]["province_slug"]
            print(f"   📍 {p}: {len(idx)} PDFs → data/drive_index_{s}.json", flush=True)
    print(f"\n💡 ข้อมูลอยู่บน Drive ของคุณ — ไม่พึ่ง กกต.", flush=True)
    print(f"💡 แชร์โฟลเดอร์เป็น public เพื่อให้ระบบ Review เข้าถึงได้", flush=True)


if __name__ == "__main__":
    main()
