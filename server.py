# -*- coding: utf-8 -*-
"""
Backend server for Election Verification Review App.
Handles file uploads (folders, .zip, .rar, .7z), triggers OCR pipeline,
and serves the React frontend.

Usage:
  pip install -r requirements.txt
  python server.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import zipfile
from pathlib import Path

import requests as http_requests  # renamed to avoid conflict with flask.request

try:
    import gdown
    HAS_GDOWN = True
except ImportError:
    HAS_GDOWN = False
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads" / "ss518"
REVIEW_APP_DIR = PROJECT_ROOT / "review-app"
REVIEW_PUBLIC = REVIEW_APP_DIR / "public"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

ALLOWED_PDF_EXT = {".pdf"}
ALLOWED_ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz"}
MAX_UPLOAD_MB = 4096  # 4 GB

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
CORS(app)

# In-memory job status
_jobs = {}  # job_id -> {status, province, progress, log, ...}
_jobs_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Province slug mapping (shared with ocr_cloud_vision.py)
# ---------------------------------------------------------------------------
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
    'สมุทรสงคราม': 'samutsongkhram', 'สมุทรสาคร': 'samutsakhon', 'สระแก้ว': 'sakaeo',
    'สระบุรี': 'saraburi', 'สิงห์บุรี': 'singburi', 'สุโขทัย': 'sukhothai',
    'สุพรรณบุรี': 'suphanburi', 'สุราษฎร์ธานี': 'suratthani', 'สุรินทร์': 'surin',
    'หนองคาย': 'nongkhai', 'หนองบัวลำภู': 'nongbualamphu', 'อ่างทอง': 'angthong',
    'อำนาจเจริญ': 'amnatcharoen', 'อุดรธานี': 'udonthani', 'อุตรดิตถ์': 'uttaradit',
    'อุทัยธานี': 'uthaithani', 'อุบลราชธานี': 'ubonratchathani',
}
SLUG_TO_PROVINCE = {v: k for k, v in PROVINCE_SLUGS.items()}


def province_to_slug(name):
    """Thai province name → English slug."""
    return PROVINCE_SLUGS.get(name, re.sub(r'[^\w]', '_', name).strip('_').lower())


# ---------------------------------------------------------------------------
# Helpers – archive extraction
# ---------------------------------------------------------------------------
def extract_archive(archive_path, dest_dir):
    """Extract .zip / .rar / .7z / .tar.gz into dest_dir. Returns list of extracted files."""
    archive_path = str(archive_path)
    ext = Path(archive_path).suffix.lower()

    extracted = []

    if ext == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest_dir)
            extracted = zf.namelist()

    elif ext == ".rar":
        try:
            import rarfile
            with rarfile.RarFile(archive_path, "r") as rf:
                rf.extractall(dest_dir)
                extracted = rf.namelist()
        except ImportError:
            # Fallback: try patool
            import patoolib
            patoolib.extract_archive(archive_path, outdir=str(dest_dir))
            extracted = list_files_recursive(dest_dir)

    elif ext == ".7z":
        try:
            import py7zr
            with py7zr.SevenZipFile(archive_path, "r") as sz:
                sz.extractall(path=dest_dir)
                extracted = sz.getnames()
        except ImportError:
            import patoolib
            patoolib.extract_archive(archive_path, outdir=str(dest_dir))
            extracted = list_files_recursive(dest_dir)

    elif ext in (".tar", ".tgz") or archive_path.endswith(".tar.gz"):
        import tarfile
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(dest_dir)
            extracted = tf.getnames()

    else:
        # Generic fallback via patool
        try:
            import patoolib
            patoolib.extract_archive(archive_path, outdir=str(dest_dir))
            extracted = list_files_recursive(dest_dir)
        except Exception as e:
            raise ValueError(f"Unsupported archive format: {ext} ({e})")

    return extracted


def list_files_recursive(directory):
    """List all files in directory recursively (relative paths)."""
    result = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            result.append(os.path.relpath(os.path.join(root, f), directory))
    return result


# ---------------------------------------------------------------------------
# Helpers – file organization
# ---------------------------------------------------------------------------
def detect_province_constituency(root_dir):
    """
    Detect province and constituency structure from extracted/uploaded files.
    Expected patterns:
      จังหวัด/เขตเลือกตั้งที่ N/file.pdf
      province_name/เขต N/file.pdf
      เขตเลือกตั้งที่ N/file.pdf  (province inferred from parent or filename)
    Returns: {province_name: {constituency_no: [pdf_paths]}}
    """
    result = {}

    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue
            full_path = os.path.join(root, f)
            rel = os.path.relpath(full_path, root_dir)
            parts = Path(rel).parts

            province = None
            constituency = None

            # Try to detect from path parts
            for part in parts:
                # Constituency detection
                m = re.search(r'เขต(?:เลือกตั้ง)?(?:ที่)?\s*(\d+)', part)
                if m:
                    constituency = int(m.group(1))
                    continue

                # Province detection — check if it's a known province name
                for prov_name in PROVINCE_SLUGS:
                    if prov_name in part:
                        province = prov_name
                        break

            if province is None:
                # Try to detect from filename
                for prov_name in PROVINCE_SLUGS:
                    if prov_name in f:
                        province = prov_name
                        break

            if province and constituency is not None:
                result.setdefault(province, {}).setdefault(constituency, []).append(full_path)
            elif province:
                result.setdefault(province, {}).setdefault(0, []).append(full_path)

    return result


def organize_uploads(detected, target_base=None):
    """
    Copy detected PDFs into the standard folder structure:
      downloads/ss518/จังหวัด/เขตเลือกตั้งที่ N/file.pdf
    Returns summary dict.
    """
    if target_base is None:
        target_base = DOWNLOADS_DIR

    summary = {}
    for province, constituencies in detected.items():
        prov_dir = target_base / province
        total = 0
        for cons_no, pdf_paths in constituencies.items():
            if cons_no == 0:
                cons_dir = prov_dir
            else:
                cons_dir = prov_dir / f"เขตเลือกตั้งที่ {cons_no}"
            cons_dir.mkdir(parents=True, exist_ok=True)

            for src in pdf_paths:
                dst = cons_dir / os.path.basename(src)
                if not dst.exists():
                    shutil.copy2(src, dst)
                total += 1

        summary[province] = {
            "constituencies": len([c for c in constituencies if c != 0]),
            "pdfs": total,
            "slug": province_to_slug(province),
        }
    return summary


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/api/provinces", methods=["GET"])
def api_provinces():
    """List all provinces with their status."""
    provinces = []

    # Scan downloads/ss518 for province folders
    if DOWNLOADS_DIR.exists():
        for d in sorted(DOWNLOADS_DIR.iterdir()):
            if not d.is_dir():
                continue
            folder_name = d.name
            # Count PDFs and constituencies
            pdf_count = 0
            cons_set = set()
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        pdf_count += 1
                rel = os.path.relpath(root, d)
                m = re.search(r'เขต(?:เลือกตั้ง)?(?:ที่)?\s*(\d+)', rel)
                if m:
                    cons_set.add(int(m.group(1)))

            # Resolve folder name: could be Thai name or English slug
            if folder_name in PROVINCE_SLUGS:
                # Thai name folder
                name = folder_name
                slug = PROVINCE_SLUGS[folder_name]
            elif folder_name in SLUG_TO_PROVINCE:
                # English slug folder
                name = SLUG_TO_PROVINCE[folder_name]
                slug = folder_name
            else:
                name = folder_name
                slug = folder_name
            # Check if OCR results exist
            ocr_file = DATA_DIR / f"ocr_vision_{slug}.json"
            ocr_count = 0
            if ocr_file.exists():
                try:
                    with open(ocr_file, "r", encoding="utf-8") as f:
                        ocr_count = len(json.load(f))
                except Exception:
                    pass

            provinces.append({
                "name": name,
                "slug": slug,
                "folder": folder_name,
                "pdf_count": pdf_count,
                "constituencies": sorted(cons_set),
                "constituency_count": len(cons_set),
                "ocr_count": ocr_count,
                "has_ocr": ocr_count > 0,
            })

    return jsonify({"provinces": provinces})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Upload files for a province.
    Accepts multipart/form-data with:
      - files[]: one or more files (PDFs or archives)
      - province: (optional) province name override
      - constituency: (optional) constituency number override
    Supports: .pdf, .zip, .rar, .7z, .tar.gz
    Also supports folder uploads via webkitRelativePath.
    """
    files = request.files.getlist("files[]") or request.files.getlist("files")
    if not files:
        return jsonify({"error": "ไม่พบไฟล์ที่อัปโหลด"}), 400

    province_override = request.form.get("province", "").strip()
    constituency_override = request.form.get("constituency", "").strip()

    # Create temp dir for processing
    tmp_dir = Path(tempfile.mkdtemp(prefix="election_upload_"))

    try:
        uploaded_pdfs = []
        uploaded_archives = []

        for f in files:
            if not f.filename:
                continue

            # Preserve relative path from folder upload (webkitRelativePath)
            rel_path = f.filename  # browsers send relative path for folder uploads
            safe_parts = Path(rel_path).parts
            # Sanitize each part but preserve structure
            safe_path = tmp_dir
            for part in safe_parts[:-1]:
                safe_path = safe_path / part
            safe_path.mkdir(parents=True, exist_ok=True)
            dest = safe_path / safe_parts[-1]
            f.save(str(dest))

            ext = Path(dest).suffix.lower()
            if ext == ".pdf":
                uploaded_pdfs.append(str(dest))
            elif ext in ALLOWED_ARCHIVE_EXT or ext in (".gz",):
                uploaded_archives.append(str(dest))

        # Extract archives
        for arc in uploaded_archives:
            arc_name = Path(arc).stem
            extract_dir = tmp_dir / f"_extracted_{arc_name}"
            extract_dir.mkdir(exist_ok=True)
            try:
                extract_archive(arc, str(extract_dir))
            except Exception as e:
                return jsonify({"error": f"ไม่สามารถแตกไฟล์ {Path(arc).name}: {e}"}), 400

        # Detect province/constituency structure
        detected = detect_province_constituency(str(tmp_dir))

        # Apply overrides
        if province_override and not detected:
            # All PDFs go under the specified province
            all_pdfs = []
            for root, dirs, fnames in os.walk(tmp_dir):
                for fn in fnames:
                    if fn.lower().endswith(".pdf"):
                        all_pdfs.append(os.path.join(root, fn))

            if all_pdfs:
                cons = int(constituency_override) if constituency_override.isdigit() else 0
                detected = {province_override: {cons: all_pdfs}}

        elif province_override and detected:
            # Rename detected province to override
            old_keys = list(detected.keys())
            if len(old_keys) == 1:
                detected[province_override] = detected.pop(old_keys[0])

        if not detected:
            # Last resort: collect all PDFs, assign to "ไม่ทราบจังหวัด"
            all_pdfs = []
            for root, dirs, fnames in os.walk(tmp_dir):
                for fn in fnames:
                    if fn.lower().endswith(".pdf"):
                        all_pdfs.append(os.path.join(root, fn))
            if all_pdfs:
                detected = {"ไม่ทราบจังหวัด": {0: all_pdfs}}
            else:
                return jsonify({"error": "ไม่พบไฟล์ PDF ในไฟล์ที่อัปโหลด"}), 400

        # Organize into standard folder structure
        summary = organize_uploads(detected, DOWNLOADS_DIR)

        return jsonify({
            "success": True,
            "message": f"อัปโหลดสำเร็จ",
            "summary": summary,
        })

    finally:
        # Cleanup temp dir
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Google Drive helpers — dual strategy:
#   1. Public scraping (no API key needed, works for publicly shared folders)
#   2. Drive API v3 fallback (needs GOOGLE_CLOUD_API_KEY)
# ---------------------------------------------------------------------------
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_google_api_key():
    """Get Google Cloud API key from env or .env file."""
    key = os.environ.get("GOOGLE_CLOUD_API_KEY")
    if key:
        return key
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GOOGLE_CLOUD_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def parse_drive_folder_id(url_or_id):
    """Extract Google Drive folder ID from URL or raw ID.

    Supports:
      https://drive.google.com/drive/folders/XXXXX
      https://drive.google.com/drive/folders/XXXXX?usp=sharing
      https://drive.google.com/drive/u/0/folders/XXXXX
      XXXXX  (raw ID)
    """
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()
    # Direct ID (no slashes, no dots)
    if re.match(r'^[\w-]{20,}$', url_or_id):
        return url_or_id
    # URL patterns
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', url_or_id)
    if m:
        return m.group(1)
    return None


# --- Strategy 1: Public access (no API key) ---

def _drive_gdown_list_folder(folder_id, timeout=30):
    """Use gdown to list files in a public Google Drive folder.

    Returns list of {id, name, mimeType} or None if gdown is not available or fails.
    Uses a thread with timeout to prevent hanging.
    """
    if not HAS_GDOWN:
        return None

    result_box = [None]
    error_box = [None]

    def _inner():
        try:
            from gdown.download_folder import (
                _download_and_parse_google_drive_link,
                _get_directory_structure,
                _get_session,
            )
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            sess = _get_session(proxy=None, use_cookies=True, user_agent=DRIVE_UA)
            return_code, gdrive_file = _download_and_parse_google_drive_link(
                sess, url, quiet=True, remaining_ok=True,
            )
            result_box[0] = (return_code, gdrive_file)
        except Exception as e:
            error_box[0] = e

    t = threading.Thread(target=_inner, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return None  # timed out
    if error_box[0] or not result_box[0]:
        return None

    return_code, gdrive_file = result_box[0]
    if not return_code or not gdrive_file:
        return None

    try:  # parse structure

        # _get_directory_structure returns (file_id_or_None, path) pairs
        # file_id=None means it's a folder
        structure = _get_directory_structure(gdrive_file, gdrive_file.name)

        entries = []
        seen = set()
        for file_id, file_path in structure:
            if file_id is None:
                # It's a folder — extract folder name from path
                folder_name = os.path.basename(file_path)
                # We don't have the folder's Drive ID from this structure,
                # so we get children directly from gdrive_file
                continue
            name = os.path.basename(file_path)
            if file_id not in seen:
                seen.add(file_id)
                entries.append({
                    "id": file_id,
                    "name": name,
                    "mimeType": "application/pdf" if name.lower().endswith(".pdf") else "application/octet-stream",
                })

        # Also extract subfolder info from gdrive_file.children
        if hasattr(gdrive_file, "children"):
            for child in gdrive_file.children:
                is_folder = hasattr(child, "children")
                if is_folder and child.id not in seen:
                    seen.add(child.id)
                    entries.append({
                        "id": child.id,
                        "name": child.name,
                        "mimeType": "application/vnd.google-apps.folder",
                    })
                elif not is_folder and child.id not in seen:
                    seen.add(child.id)
                    entries.append({
                        "id": child.id,
                        "name": child.name,
                        "mimeType": "application/pdf" if child.name.lower().endswith(".pdf") else "application/octet-stream",
                    })

        return entries if entries else None
    except Exception:
        return None  # structure parsing failed


def _drive_scrape_folder(folder_id):
    """Scrape a public Google Drive folder page to extract file/folder listings.

    Tries gdown first (reliable), then falls back to regex parsing.
    Returns list of {id, name, mimeType} or None if scraping fails.
    """
    # Try gdown first — it has battle-tested Google Drive page parsing
    gdown_result = _drive_gdown_list_folder(folder_id)
    if gdown_result:
        return gdown_result

    # Fallback: manual regex scraping
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    try:
        resp = http_requests.get(url, headers={"User-Agent": DRIVE_UA}, timeout=30)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    html = resp.text

    # Check if Google redirected to a login page
    if "accounts.google.com" in html and "ServiceLogin" in html:
        return None  # Not publicly accessible

    entries = {}  # id -> {id, name, mimeType}

    # Strategy A: Find ID+name pairs and check surrounding context for type
    for m in re.finditer(r'\["([\w-]{25,60})"\s*,\s*"([^"]{1,500})"', html):
        fid = m.group(1)
        name = m.group(2)
        if fid == folder_id:
            continue

        ctx_start = max(0, m.start() - 300)
        ctx_end = min(len(html), m.end() + 600)
        context = html[ctx_start:ctx_end]

        is_folder = "application/vnd.google-apps.folder" in context
        is_pdf = "application/pdf" in context or name.lower().endswith(".pdf")

        if is_folder or is_pdf:
            mime = "application/vnd.google-apps.folder" if is_folder else "application/pdf"
            if fid not in entries:
                entries[fid] = {"id": fid, "name": name, "mimeType": mime}

    # Strategy B: Look for data-id attributes (older Drive UI format)
    for m in re.finditer(r'data-id="([\w-]{25,60})"[^>]*?data-target="([^"]*)"', html):
        fid = m.group(1)
        if fid == folder_id or fid in entries:
            continue
        target = m.group(2)
        name_m = re.search(r'data-tooltip="([^"]+)"', html[m.start():m.start() + 500])
        if name_m:
            name = name_m.group(1)
            mime = "application/vnd.google-apps.folder" if "folder" in target.lower() else "application/pdf"
            entries[fid] = {"id": fid, "name": name, "mimeType": mime}

    return list(entries.values()) if entries else None


def _drive_download_public(file_id, dest_path):
    """Download a public file from Google Drive without API key.

    Tries gdown first (handles virus scan pages, cookies, etc.),
    then falls back to direct URL download.
    """
    # Strategy A: gdown (most reliable for public files)
    if HAS_GDOWN:
        try:
            url = f"https://drive.google.com/uc?id={file_id}"
            result = gdown.download(url, output=dest_path, quiet=True, fuzzy=False)
            if result and os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                return
            # gdown returned but file is empty/missing — fall through
        except Exception:
            pass  # fall through to manual download

    # Strategy B: Direct download with confirmation handling
    session = http_requests.Session()
    url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    resp = session.get(url, headers={"User-Agent": DRIVE_UA}, stream=True, timeout=120)

    if resp.status_code != 200:
        raise Exception(f"Public download failed: HTTP {resp.status_code}")

    # Stream to file, checking first chunk for HTML error pages
    first_chunk = None
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if first_chunk is None:
                first_chunk = chunk
            f.write(chunk)

    # Sanity check: if file is HTML, it's likely an error page
    if first_chunk and first_chunk.strip().startswith(b"<!DOCTYPE"):
        os.remove(dest_path)
        raise Exception("Downloaded content is HTML (likely error page), not PDF")


# --- Strategy 2: Drive API v3 (needs API key) ---

def _drive_api_list_files(folder_id, api_key, file_type=None):
    """List files in a Google Drive folder using API v3."""
    q = f"'{folder_id}' in parents and trashed = false"
    if file_type == "folder":
        q += " and mimeType = 'application/vnd.google-apps.folder'"
    elif file_type == "pdf":
        q += " and mimeType = 'application/pdf'"

    all_files = []
    page_token = None

    while True:
        params = {
            "q": q,
            "key": api_key,
            "fields": "nextPageToken, files(id, name, mimeType, size)",
            "pageSize": 1000,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = http_requests.get(f"{DRIVE_API_BASE}/files", params=params, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"Drive API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        all_files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_files


def _drive_api_download(file_id, api_key, dest_path):
    """Download a file from Google Drive using API v3."""
    url = f"{DRIVE_API_BASE}/files/{file_id}?alt=media&key={api_key}"
    resp = http_requests.get(url, stream=True, timeout=120)
    if resp.status_code != 200:
        raise Exception(f"API download failed {resp.status_code}: {resp.text[:300]}")
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            f.write(chunk)


# --- Unified functions (try public first, then API) ---

def drive_list_files(folder_id, api_key=None, file_type=None):
    """List files in a Drive folder. Tries API first (faster), then public scraping."""
    errors = []

    # Strategy 1: API (if key available) — reliable and supports file_type filter
    if api_key:
        try:
            return _drive_api_list_files(folder_id, api_key, file_type)
        except Exception as e:
            errors.append(str(e))

    # Strategy 2: Public scraping — no API key needed
    scraped = _drive_scrape_folder(folder_id)
    if scraped is not None:
        if file_type == "folder":
            return [f for f in scraped if f["mimeType"] == "application/vnd.google-apps.folder"]
        elif file_type == "pdf":
            return [f for f in scraped if f["mimeType"] == "application/pdf"]
        return scraped

    # Nothing worked — provide specific guidance
    hint_parts = []
    for e in errors:
        if "has not been used" in e or "disabled" in e:
            hint_parts.append("Google Drive API ยังไม่ได้เปิดใน Cloud Console")
        elif "403" in e:
            hint_parts.append("API key ไม่มีสิทธิ์เข้าถึง")
        else:
            hint_parts.append(e[:200])
    if not errors:
        hint_parts.append("โฟลเดอร์ไม่ได้แชร์สาธารณะ (ต้อง login Google) หรือ URL ไม่ถูกต้อง")

    raise Exception(" | ".join(hint_parts))


def drive_download_file(file_id, api_key=None, dest_path=None):
    """Download a file from Drive. Tries public URL first, then API."""
    errors = []

    # Strategy 1: Public download (no API key needed)
    try:
        _drive_download_public(file_id, dest_path)
        return
    except Exception as e:
        errors.append(f"public: {e}")

    # Strategy 2: API download
    if api_key:
        try:
            _drive_api_download(file_id, api_key, dest_path)
            return
        except Exception as e:
            errors.append(f"api: {e}")

    raise Exception(f"ดาวน์โหลดล้มเหลวทุกวิธี: {'; '.join(errors)}")


def drive_walk_folder(folder_id, api_key=None, path_parts=None, log_fn=None):
    """Recursively walk a Drive folder, returning (relative_path_parts, file_info) for PDFs."""
    if path_parts is None:
        path_parts = []

    results = []

    # List subfolders and PDFs
    folders = drive_list_files(folder_id, api_key, file_type="folder")
    pdfs = drive_list_files(folder_id, api_key, file_type="pdf")

    for pdf in pdfs:
        results.append((path_parts, pdf))

    if log_fn:
        folder_name = "/".join(path_parts) or "(root)"
        log_fn(f"📂 {folder_name}: {len(pdfs)} PDFs, {len(folders)} subfolders")

    for folder in sorted(folders, key=lambda f: f["name"]):
        sub_results = drive_walk_folder(
            folder["id"], api_key, path_parts + [folder["name"]], log_fn
        )
        results.extend(sub_results)
        time.sleep(0.2)  # gentle rate limit

    return results


@app.route("/api/drive-preview", methods=["POST"])
def api_drive_preview():
    """
    Preview contents of a Google Drive folder (quick scan, no download).
    Body: { "url": "https://drive.google.com/drive/folders/XXXXX" }
    Works without API key for public folders.
    """
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()

    folder_id = parse_drive_folder_id(url)
    if not folder_id:
        return jsonify({"error": "URL ไม่ถูกต้อง"}), 400

    api_key = get_google_api_key()  # may be None — that's OK

    try:
        folders = drive_list_files(folder_id, api_key, file_type="folder")
        pdfs = drive_list_files(folder_id, api_key, file_type="pdf")

        items = []
        for f in sorted(folders, key=lambda x: x["name"]):
            try:
                sub_pdfs = drive_list_files(f["id"], api_key, file_type="pdf")
                sub_folders = drive_list_files(f["id"], api_key, file_type="folder")
                items.append({
                    "name": f["name"],
                    "type": "folder",
                    "pdf_count": len(sub_pdfs),
                    "subfolder_count": len(sub_folders),
                })
            except Exception:
                items.append({
                    "name": f["name"],
                    "type": "folder",
                    "pdf_count": -1,
                    "subfolder_count": -1,
                })

        method = "api" if api_key else "public"
        return jsonify({
            "folder_id": folder_id,
            "top_level_pdfs": len(pdfs),
            "subfolders": items,
            "total_subfolders": len(folders),
            "method": method,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/import-drive", methods=["POST"])
def api_import_drive():
    """
    Import PDFs from a Google Drive folder (กกต. shared folders).
    Body: { "url": "https://drive.google.com/drive/folders/XXXXX", "province": "" }
    Works without API key for public folders. Runs in background as a job.
    """
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()
    province_override = body.get("province", "").strip()

    folder_id = parse_drive_folder_id(url)
    if not folder_id:
        return jsonify({"error": "URL ไม่ถูกต้อง — ต้องเป็นลิงก์โฟลเดอร์ Google Drive"}), 400

    api_key = get_google_api_key()  # may be None — that's OK

    job_id = f"drive_{folder_id[:12]}_{int(time.time())}"

    def run_import():
        log_lines = []

        def log(msg):
            log_lines.append(msg)
            with _jobs_lock:
                _jobs[job_id]["log"] = "\n".join(log_lines[-150:])
                _jobs[job_id]["progress"] = msg

        method = "API" if api_key else "public scraping"
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "running",
                "type": "drive_import",
                "folder_id": folder_id,
                "log": "",
                "progress": "กำลังสแกนโฟลเดอร์...",
                "started": time.time(),
            }

        try:
            # 1. Walk the Drive folder
            log(f"🔍 กำลังสแกน Drive folder ({method}): {folder_id}")
            all_pdfs = drive_walk_folder(folder_id, api_key, log_fn=log)
            log(f"📊 พบ {len(all_pdfs)} ไฟล์ PDF ทั้งหมด")

            if not all_pdfs:
                log("❌ ไม่พบไฟล์ PDF ในโฟลเดอร์นี้")
                with _jobs_lock:
                    _jobs[job_id]["status"] = "error"
                return

            total = len(all_pdfs)
            with _jobs_lock:
                _jobs[job_id]["total_count"] = total
                _jobs[job_id]["downloaded_count"] = 0
                _jobs[job_id]["error_count"] = 0
                _jobs[job_id]["percent"] = 0

            # 2. Download each PDF to temp dir
            tmp_dir = Path(tempfile.mkdtemp(prefix="election_drive_"))
            downloaded = 0
            errors = 0

            for path_parts, file_info in all_pdfs:
                try:
                    # Create subdirectory structure
                    sub_dir = tmp_dir
                    for part in path_parts:
                        sub_dir = sub_dir / part
                    sub_dir.mkdir(parents=True, exist_ok=True)

                    dest = sub_dir / file_info["name"]
                    if dest.exists():
                        dest = sub_dir / f"{file_info['id']}_{file_info['name']}"

                    log(f"⬇️  [{downloaded + 1}/{total}] {'/'.join(path_parts + [file_info['name']])}")
                    drive_download_file(file_info["id"], api_key, str(dest))
                    downloaded += 1
                    time.sleep(0.2)  # rate limit

                except Exception as e:
                    log(f"  ⚠️ ดาวน์โหลดล้มเหลว: {file_info['name']}: {e}")
                    errors += 1

                # Update progress
                with _jobs_lock:
                    _jobs[job_id]["downloaded_count"] = downloaded
                    _jobs[job_id]["error_count"] = errors
                    _jobs[job_id]["percent"] = round((downloaded + errors) / total * 100)

            log(f"✅ ดาวน์โหลดสำเร็จ {downloaded}/{total} ไฟล์ (ผิดพลาด: {errors})")

            # 3. Detect province/constituency and organize
            detected = detect_province_constituency(str(tmp_dir))

            if province_override and not detected:
                all_local_pdfs = []
                for root, dirs, fnames in os.walk(tmp_dir):
                    for fn in fnames:
                        if fn.lower().endswith(".pdf"):
                            all_local_pdfs.append(os.path.join(root, fn))
                if all_local_pdfs:
                    detected = {province_override: {0: all_local_pdfs}}
            elif province_override and detected:
                old_keys = list(detected.keys())
                if len(old_keys) == 1:
                    detected[province_override] = detected.pop(old_keys[0])

            if not detected:
                all_local_pdfs = []
                for root, dirs, fnames in os.walk(tmp_dir):
                    for fn in fnames:
                        if fn.lower().endswith(".pdf"):
                            all_local_pdfs.append(os.path.join(root, fn))
                if all_local_pdfs:
                    detected = {"ไม่ทราบจังหวัด": {0: all_local_pdfs}}

            if detected:
                summary = organize_uploads(detected, DOWNLOADS_DIR)
                log("📁 จัดเก็บสำเร็จ:")
                for prov, info in summary.items():
                    log(f"   📍 {prov}: {info['pdfs']} PDFs, {info['constituencies']} เขต")
            else:
                summary = {}
                log("❌ ไม่พบไฟล์ PDF ที่จัดระเบียบได้")

            # Cleanup
            shutil.rmtree(tmp_dir, ignore_errors=True)

            with _jobs_lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["summary"] = summary
                _jobs[job_id]["downloaded"] = downloaded
                _jobs[job_id]["errors"] = errors

        except Exception as e:
            log(f"❌ Error: {e}")
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["log"] = "\n".join(log_lines[-150:])

    thread = threading.Thread(target=run_import, daemon=True)
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "started",
        "folder_id": folder_id,
    })


@app.route("/api/ocr", methods=["POST"])
def api_ocr():
    """
    Trigger OCR for a province (runs in background).
    Body: { "province": "ชัยภูมิ", "options": {"all": true, "debug": true, "resume": true} }
    """
    body = request.get_json(silent=True) or {}
    province = body.get("province", "").strip()
    if not province:
        return jsonify({"error": "กรุณาระบุจังหวัด"}), 400

    options = body.get("options", {})

    job_id = f"ocr_{province_to_slug(province)}_{int(time.time())}"

    def run_ocr():
        with _jobs_lock:
            _jobs[job_id] = {"status": "running", "province": province, "log": "", "started": time.time()}

        cmd = [
            sys.executable, str(SCRIPTS_DIR / "ocr_cloud_vision.py"),
            "--province", province,
        ]
        if options.get("all", True):
            cmd.append("--all")
        if options.get("debug", True):
            cmd.append("--debug")
        if options.get("resume", True):
            cmd.append("--resume")
        if options.get("ss518_only", True):
            cmd.append("--ss518-only")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            log_lines = []
            for line in proc.stdout:
                log_lines.append(line.rstrip())
                with _jobs_lock:
                    _jobs[job_id]["log"] = "\n".join(log_lines[-100:])  # keep last 100 lines

            proc.wait()
            with _jobs_lock:
                _jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
                _jobs[job_id]["returncode"] = proc.returncode
                _jobs[job_id]["log"] = "\n".join(log_lines[-200:])

        except Exception as e:
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["log"] = str(e)

    thread = threading.Thread(target=run_ocr, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "status": "started", "province": province})


@app.route("/api/prepare", methods=["POST"])
def api_prepare():
    """Run prepare_review_data.py to regenerate review_data.json."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "prepare_review_data.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Timeout (120s)"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_job_status(job_id):
    """Check status of a background job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/jobs", methods=["GET"])
def api_jobs():
    """List all jobs."""
    with _jobs_lock:
        return jsonify({"jobs": dict(_jobs)})


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def api_job_cancel(job_id):
    """Cancel/remove a job (marks as cancelled if running, or removes if done)."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if job.get("status") == "running":
            _jobs[job_id]["status"] = "cancelled"
            _jobs[job_id]["progress"] = "ยกเลิกโดยผู้ใช้"
        else:
            del _jobs[job_id]
    return jsonify({"ok": True})


@app.route("/api/jobs", methods=["DELETE"])
def api_jobs_clear():
    """Clear all finished/stuck jobs."""
    with _jobs_lock:
        to_remove = [k for k, v in _jobs.items() if v.get("status") != "running"]
        for k in to_remove:
            del _jobs[k]
        # Mark running jobs older than 10 min as stuck/cancelled
        now = time.time()
        for k, v in _jobs.items():
            if v.get("status") == "running" and now - v.get("started", now) > 600:
                v["status"] = "cancelled"
                v["progress"] = "หมดเวลา (>10 นาที)"
        removed = len(to_remove)
    return jsonify({"ok": True, "removed": removed})


# ---------------------------------------------------------------------------
# Serve React frontend (production build or dev proxy)
# ---------------------------------------------------------------------------
DIST_DIR = REVIEW_APP_DIR / "dist"

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the React app (built or public folder)."""
    # Try dist (production build) first
    if DIST_DIR.exists():
        full = DIST_DIR / path
        if full.is_file():
            return send_from_directory(str(DIST_DIR), path)
        return send_from_directory(str(DIST_DIR), "index.html")

    # Fallback: serve from public folder (dev)
    full = REVIEW_PUBLIC / path
    if full.is_file():
        return send_from_directory(str(REVIEW_PUBLIC), path)
    # Serve index.html for SPA routing
    index = REVIEW_PUBLIC / "index.html"
    if index.exists():
        return send_from_directory(str(REVIEW_PUBLIC), "index.html")

    return "Review app not built. Run: cd review-app && npm run build", 404


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"📁 Project: {PROJECT_ROOT}")
    print(f"📁 Downloads: {DOWNLOADS_DIR}")
    print(f"📁 Data: {DATA_DIR}")
    print(f"🌐 Starting server on http://localhost:5000")
    print(f"   (React dev server: http://localhost:3000)")
    app.run(host="0.0.0.0", port=5000, debug=True)
