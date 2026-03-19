# -*- coding: utf-8 -*-
"""
OCR สส.5/18 ด้วย Google Cloud Vision REST API
- ใช้ API Key (ไม่ต้อง Service Account)
- รองรับ handwriting + Thai text
- แม่นยำกว่า Tesseract มาก

Setup:
  1. Set env var: GOOGLE_CLOUD_API_KEY=<your-key>
     หรือสร้างไฟล์ .env ที่ root ของ project ใส่: GOOGLE_CLOUD_API_KEY=<your-key>
  2. เปิด Cloud Vision API ที่ Google Cloud Console

Usage:
  python scripts/ocr_cloud_vision.py                     # ทดสอบ 1 ไฟล์
  python scripts/ocr_cloud_vision.py --all                # ทุกไฟล์ชัยภูมิ
  python scripts/ocr_cloud_vision.py --file <path>        # ไฟล์เดียว
  python scripts/ocr_cloud_vision.py --file <path> --page 0  # เฉพาะหน้า
"""
import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import fitz  # PyMuPDF
import numpy as np
import cv2
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, '..', 'downloads', 'ss518')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

# Rate limit: Vision API free tier = 1,000 requests/month
RATE_LIMIT_SEC = 1.5


def get_api_key():
    """Get API key from env or .env file."""
    key = os.environ.get('GOOGLE_CLOUD_API_KEY')
    if key:
        return key
    # Try .env file
    env_path = os.path.join(SCRIPT_DIR, '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('GOOGLE_CLOUD_API_KEY='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def thai_text_to_number(text):
    """Convert Thai written number to integer.
    e.g. 'สี่ร้อยเก้าสิบหก' → 496, 'สามร้อยสิบเจ็ด' → 317
    Returns None if cannot parse.
    """
    if not text:
        return None
    # Clean up OCR noise
    text = re.sub(r'[^ก-๙\s]', '', text).strip()
    if not text:
        return None

    # Token map: word → (value, type)
    # type: 'digit' for units 0-9, 'tens' for สิบ, 'mult' for ร้อย/พัน/หมื่น/แสน/ล้าน
    TOKENS = [
        ('ยี่สิบ', 20, 'fixed'),
        ('สิบ', 10, 'tens'),
        ('ร้อย', 100, 'mult'),
        ('พัน', 1000, 'mult'),
        ('หมื่น', 10000, 'mult'),
        ('แสน', 100000, 'mult'),
        ('ล้าน', 1000000, 'mult'),
        ('หนึ่ง', 1, 'digit'),
        ('เอ็ด', 1, 'digit'),
        ('สอง', 2, 'digit'),
        ('สาม', 3, 'digit'),
        ('สี่', 4, 'digit'),
        ('ห้า', 5, 'digit'),
        ('หก', 6, 'digit'),
        ('เจ็ด', 7, 'digit'),
        ('แปด', 8, 'digit'),
        ('เก้า', 9, 'digit'),
        ('ศูนย์', 0, 'digit'),
    ]

    # Tokenize greedily, tracking coverage
    tokens = []
    pos = 0
    matched_chars = 0
    s = text.replace(' ', '')
    while pos < len(s):
        matched = False
        for word, val, typ in TOKENS:
            if s[pos:].startswith(word):
                tokens.append((val, typ))
                matched_chars += len(word)
                pos += len(word)
                matched = True
                break
        if not matched:
            pos += 1  # skip unknown char

    if not tokens:
        return None

    # Reject if too few characters matched (garbled OCR text)
    coverage = matched_chars / len(s) if s else 0
    if coverage < 0.7:
        return None

    # Evaluate: process multipliers
    # e.g. สี่(4) ร้อย(x100) เก้า(9) สิบ(x10) หก(6) → 400+96 = 496
    # Key: after สิบ, the next digit is ones-place (ADD, not replace)
    result = 0
    current = 0
    after_tens = False
    for val, typ in tokens:
        if typ == 'digit':
            if after_tens:
                current += val   # ones place after tens: 90+6=96
            else:
                current = val
            after_tens = False
        elif typ == 'tens':
            # สิบ without preceding digit means 10
            current = (current if current else 1) * 10
            after_tens = True
        elif typ == 'fixed':
            # ยี่สิบ = 20
            current = val
            after_tens = True
        elif typ == 'mult':
            # ร้อย/พัน/หมื่น/แสน/ล้าน
            current = (current if current else 1) * val
            result += current
            current = 0
            after_tens = False
    result += current

    return result if result > 0 else None


# Province name → slug mapping for output files
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


def find_province(name):
    """Find province directory by Thai name or English slug."""
    slug = PROVINCE_SLUGS.get(name, '')
    for d in os.listdir(BASE):
        if name in d:
            return os.path.join(BASE, d)
        if slug and d == slug:
            return os.path.join(BASE, d)
    return None


def extract_number(text):
    if not text:
        return None
    text = str(text).translate(THAI_DIGITS)
    text = text.strip().replace(',', '').replace('.', '').replace(' ', '')
    text = re.sub(r'[^\d]', '', text)
    if text:
        try:
            v = int(text)
            return v if v < 9999999 else None
        except ValueError:
            return None
    return None


# ============================================================
# Metadata from file paths
# ============================================================
def extract_metadata_from_path(filepath, prov_dir):
    rel = os.path.relpath(filepath, prov_dir)
    parts = rel.replace('\\', '/').split('/')
    fname = os.path.splitext(os.path.basename(filepath))[0]

    meta = {
        "province": "ชัยภูมิ",
        "constituency": None,
        "district": None,
        "sub_district": None,
        "station_range": None,
        "vote_type": None,
        "form_type": None,
    }

    for p in parts:
        m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', p)
        if m:
            meta["constituency"] = int(m.group(1))

    for p in parts:
        m = re.match(r'อำเภอ(.+)', p)
        if m:
            meta["district"] = m.group(1).strip()
            break

    m = re.search(r'ต\.(.+?)[-_]', fname)
    if m:
        meta["sub_district"] = m.group(1).strip()
    else:
        m = re.match(r'([^\-]+?)-(\d+)-', fname)
        if m:
            meta["sub_district"] = m.group(1).strip()

    m = re.search(r'หน่วยที่\s*(\d+)-(\d+)', fname)
    if m:
        meta["station_range"] = f"{m.group(1)}-{m.group(2)}"
    else:
        m = re.search(r'-(\d{3})-', fname)
        if m:
            meta["station_range"] = m.group(1)

    if 'แบ่งเขต' in fname or 'แบ่งเขต' in rel:
        meta["vote_type"] = "แบ่งเขต"
    if 'บัญชีรายชื่อ' in fname or 'บัญชีรายชื่อ' in rel:
        meta["vote_type"] = "บัญชีรายชื่อ" if not meta["vote_type"] else "แบ่งเขต+บัญชีรายชื่อ"

    if '5_16' in fname:
        meta["form_type"] = "สส.5/16"
    elif '5_17' in fname:
        meta["form_type"] = "สส.5/17"
    else:
        meta["form_type"] = "สส.5/18"

    return meta


# ============================================================
# PDF to image
# ============================================================
def pdf_page_to_png_bytes(pdf_path, page_num=0, dpi=200):
    """Convert PDF page to PNG bytes for API submission."""
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    return pdf_bytes_to_png(pdf_bytes, page_num, dpi)


def pdf_bytes_to_png(pdf_bytes, page_num=0, dpi=200):
    """Convert PDF bytes (in-memory) to PNG bytes. No disk I/O."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    if page_num >= total:
        doc.close()
        return None, total
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes, total


# ============================================================
# Cloud Vision API call
# ============================================================
def call_vision_api(image_bytes, api_key, feature="DOCUMENT_TEXT_DETECTION"):
    """Call Google Cloud Vision API with image bytes."""
    b64_image = base64.b64encode(image_bytes).decode('utf-8')

    payload = {
        "requests": [{
            "image": {"content": b64_image},
            "features": [{"type": feature}],
            "imageContext": {
                "languageHints": ["th", "en"]
            }
        }]
    }

    url = f"{VISION_API_URL}?key={api_key}"
    response = requests.post(url, json=payload, timeout=60)

    if response.status_code != 200:
        return {"error": f"HTTP {response.status_code}: {response.text[:500]}"}

    result = response.json()
    if "error" in result:
        return {"error": result["error"]}

    responses = result.get("responses", [{}])
    if not responses:
        return {"error": "Empty response"}

    resp = responses[0]
    if "error" in resp:
        return {"error": resp["error"]}

    return resp


def extract_text_from_response(resp):
    """Extract full text from Vision API response."""
    annotation = resp.get("fullTextAnnotation", {})
    text = annotation.get("text", "")
    return text


# ============================================================
# Layout-aware extraction from Cloud Vision response
# ============================================================
def extract_layout_from_response(resp):
    """Extract words with bounding boxes from Vision API response.
    Returns list of {text, x, y, w, h, mid_x, mid_y} sorted by (y, x)."""
    annotation = resp.get("fullTextAnnotation", {})
    pages = annotation.get("pages", [])
    if not pages:
        return []

    words = []
    for page in pages:
        for block in page.get("blocks", []):
            for para in block.get("paragraphs", []):
                for word in para.get("words", []):
                    symbols = word.get("symbols", [])
                    text = ''.join(s.get("text", "") for s in symbols)
                    bb = word.get("boundingBox", {})
                    verts = bb.get("vertices", bb.get("normalizedVertices", []))
                    if len(verts) < 4:
                        continue
                    xs = [v.get("x", 0) for v in verts]
                    ys = [v.get("y", 0) for v in verts]
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    words.append({
                        "text": text,
                        "x": x_min, "y": y_min,
                        "w": x_max - x_min, "h": y_max - y_min,
                        "mid_x": (x_min + x_max) / 2,
                        "mid_y": (y_min + y_max) / 2,
                    })
    words.sort(key=lambda w: (w["y"], w["x"]))
    return words


def group_words_into_rows(words, y_tolerance=15):
    """Group words into rows based on y-coordinate proximity.
    Returns list of rows, each row is a list of words sorted by x."""
    if not words:
        return []
    rows = []
    current_row = [words[0]]
    current_y = words[0]["mid_y"]
    for w in words[1:]:
        if abs(w["mid_y"] - current_y) <= y_tolerance:
            current_row.append(w)
        else:
            current_row.sort(key=lambda w: w["x"])
            rows.append(current_row)
            current_row = [w]
            current_y = w["mid_y"]
    if current_row:
        current_row.sort(key=lambda w: w["x"])
        rows.append(current_row)
    return rows


def row_text(row):
    """Concatenate words in a row into a single string."""
    return ' '.join(w["text"] for w in row)


def find_value_near_label(words, label_word, search_direction='right', max_dist=300):
    """Find a numeric value near a label word.
    search_direction: 'right' (same row, to the right) or 'below' (next row, similar x)."""
    results = []
    lx, ly = label_word["mid_x"], label_word["mid_y"]

    for w in words:
        t = w["text"].translate(THAI_DIGITS)
        # Skip non-numeric words
        digits = re.sub(r'[^\d]', '', t)
        if not digits:
            continue

        wx, wy = w["mid_x"], w["mid_y"]
        if search_direction == 'right':
            # Same row (similar y), to the right
            if abs(wy - ly) < 20 and wx > lx and (wx - lx) < max_dist:
                val = extract_number(t)
                if val is not None:
                    results.append((val, wx - lx, w))
        elif search_direction == 'below':
            # Below (greater y), similar x
            if wy > ly and (wy - ly) < max_dist and abs(wx - lx) < 100:
                val = extract_number(t)
                if val is not None:
                    results.append((val, wy - ly, w))

    if results:
        results.sort(key=lambda r: r[1])  # closest first
        return results[0][0]  # return value
    return None


def parse_ss518_with_layout(resp):
    """Parse structured data using Cloud Vision layout (bounding boxes).
    Falls back to text-only parsing for fields not found via layout."""
    text = extract_text_from_response(resp)
    # Start with text-based parsing as baseline
    result = parse_ss518_text(text)

    # Try layout-based extraction for key numeric fields
    words = extract_layout_from_response(resp)
    if not words:
        return result  # no layout data, return text-only result

    rows = group_words_into_rows(words)

    # Build lookup: find words containing specific labels
    label_patterns = {
        'registered_voters': [r'สิทธิเลือกตั้ง', r'ตามบัญชีรายชื่อ'],
        'turnout': [r'มาแสดงตน', r'มาใช้สิทธิ'],
        'ballots_received': [r'ได้รับจัดสรร', r'รับจัดสรร'],
        'valid_ballots': [r'บัตรดี'],
        'invalid_ballots': [r'บัตรเสีย'],
        'no_vote_ballots': [r'ไม่(?:เลือก|ประสงค์)'],
        'remaining_ballots': [r'ที่เหลือ'],
    }

    layout_results = {}
    for field, patterns in label_patterns.items():
        for row in rows:
            rt = row_text(row)
            for pat in patterns:
                if re.search(pat, rt):
                    # Found label row — look for number in same row (right side)
                    # or in the row content itself
                    label_w = row[-1]  # rightmost word in label row
                    val = find_value_near_label(words, label_w, 'right', max_dist=400)
                    if val is None:
                        # Try looking below
                        val = find_value_near_label(words, row[0], 'below', max_dist=80)
                    if val is not None and val < 9999999:
                        layout_results[field] = val
                    break
            if field in layout_results:
                break

    # Merge layout results with text-based results
    # Layout values override text-only when text had low/no confidence
    conf = result.get("_confidence", {})
    for field, layout_val in layout_results.items():
        text_val = result.get(field)
        text_conf = conf.get(field, "none")

        if text_val is None:
            # Text parser found nothing — use layout
            result[field] = layout_val
            conf[field] = "medium:layout"
        elif text_conf.startswith("low") or text_conf == "none":
            # Text parser had low confidence — prefer layout if different
            if layout_val != text_val:
                # Cross-validate: prefer larger (same heuristic as _pick_best)
                result[field] = max(layout_val, text_val)
                conf[field] = f"medium:layout={layout_val},text={text_val}"
            else:
                conf[field] = "high:layout+text"
        elif layout_val == text_val:
            # Both agree — boost confidence
            conf[field] = "high:layout+text"
        # else: text had medium/high confidence and layout disagrees — keep text

    result["_confidence"] = conf
    result["_has_layout"] = True
    return result


# ============================================================
# Parsing OCR text (same as v2 but tuned for better Cloud Vision output)
# ============================================================
def parse_ss518_text(text):
    """Parse structured data from Cloud Vision OCR text.
    
    Cloud Vision output has candidate info on separate lines:
      ๑ (or 1)          <- candidate number
      นายกิตติธัช คำวงษ์  <- name
      ประชาชน              <- party
      40 (               <- votes
    """
    result = {
        "ocr_vote_type": None,
        "ocr_constituency": None,
        "ocr_province": None,
        "ocr_station_no": None,
        "ocr_village_no": None,
        "ocr_sub_district": None,
        "ocr_district": None,
        "registered_voters": None,
        "turnout": None,
        "ballots_received": None,
        "valid_ballots": None,
        "invalid_ballots": None,
        "no_vote_ballots": None,
        "remaining_ballots": None,
        "candidates": [],
        "total_votes": None,
    }

    text_d = text.translate(THAI_DIGITS)
    lines = text.split('\n')
    lines_d = text_d.split('\n')  # Thai-digits-converted version

    # Vote type
    if 'แบ่งเขต' in text:
        result["ocr_vote_type"] = "แบ่งเขต"
    elif 'บัญชีรายชื่อ' in text:
        result["ocr_vote_type"] = "บัญชีรายชื่อ"

    # Constituency: find last occurrence (first may be in header)
    for m in re.finditer(r'เขตเลือกตั้งที่\s*(\d+)', text_d):
        result["ocr_constituency"] = extract_number(m.group(1))

    # Province
    m = re.search(r'จังหวัด\s*([\u0E00-\u0E7F]{2,})', text)
    if m:
        result["ocr_province"] = m.group(1).strip()

    # Station number: from "หน่วยเลือกตั้งที่ 14"
    m = re.search(r'หน่วยเลือกตั้งที่\s*(\d+)', text_d)
    if m:
        result["ocr_station_no"] = extract_number(m.group(1))

    # Village number
    m = re.search(r'หมู่ที่\s*(\d+)', text_d)
    if m:
        result["ocr_village_no"] = extract_number(m.group(1))

    # Sub-district: "ตำบล/แขวง/เทศบาลหนองหาน" or "ตำบล หนองหาน"
    for pat in [r'ต[ำํา]บล/แขวง/เทศบาล([\u0E00-\u0E7F]{2,})',
                r'ต[ำํา]บล/?แ?ข?ว?ง?/?เ?ท?ศ?บ?า?ล?\s*([\u0E00-\u0E7F]{2,})',
                r'ต[ำํา]บล\s*([\u0E00-\u0E7F]{2,})']:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip()
            if val not in ('แขวง', 'เทศบาล', 'เทศมหาล'):
                result["ocr_sub_district"] = val
                break

    # District: "อำเภอ/เขต" followed by Thai text
    # But Cloud Vision often puts district on the same line as "อำเภอ/เขต"
    # then the next line starts with "เขตเลือกตั้งที่" which is NOT the district
    m = re.search(r'อ[ำํา]เภอ/?เ?ข?ต?\s*([\u0E00-\u0E7F]{2,})', text)
    if m:
        val = m.group(1).strip()
        if val not in ('เขต', 'เขตเลือกตั้งที่'):
            result["ocr_district"] = val

    # ---- Vote statistics (v2: Thai text fallback + cross-validation) ----
    # Cloud Vision reads form columns separately:
    #   Left column: labels (๒.๑ ... ได้รับจัดสรร)
    #   Right column: values (จำนวน 480 บัตร)
    # So keyword and value may be far apart in OCR text.
    #
    # Strategy:
    #   1. Section 1 (คน): keyword-based with Thai text fallback
    #   2. Section 2 (บัตร): positional extraction of all "จำนวน X บัตร" patterns
    #   3. Cross-validate digit vs Thai text

    result["_confidence"] = {}  # per-field confidence info

    def _extract_digit_and_thai(region_d, region_orig, unit):
        """Extract both digit-based and Thai-text-based number from a text region.
        Returns (digit_val, thai_val)."""
        digit_val = None
        thai_val = None

        # Digit: "จำนวน <digits> <unit>" or just "<digits> <unit>"
        def _valid_digit(raw):
            """Reject section numbers like 2.2.3, 2.1.1 (single digits separated by dots)."""
            if re.match(r'^\d\.\d(\.\d)+$', raw):
                return None
            return extract_number(raw)

        if unit:
            m = re.search(r'จ[ำํา]นวน[^\d]{0,10}(\d[\d,.]*)\s*' + re.escape(unit), region_d)
            if not m:
                m = re.search(r'(\d[\d,.]*)\s*' + re.escape(unit), region_d)
            if m:
                digit_val = _valid_digit(m.group(1))
        else:
            m = re.search(r'จ[ำํา]นวน[^\d]{0,10}(\d[\d,.]*)', region_d)
            if m:
                digit_val = _valid_digit(m.group(1))

        # Thai text: content in parentheses "( สี่ร้อยเก้าสิบหก )"
        # Require closing paren to avoid matching truncated text like "(สาม" → 3
        for pm in re.finditer(r'\(\s*([^)]{3,60})\s*\)', region_orig):
            v = thai_text_to_number(pm.group(1))
            if v and v > 0:
                thai_val = v
                break

        return digit_val, thai_val

    def _pick_best(digit_val, thai_val, field_name):
        """Cross-validate digit vs Thai text, return (value, confidence)."""
        if digit_val and thai_val:
            if digit_val == thai_val:
                result["_confidence"][field_name] = "high"
                return digit_val
            else:
                # Both exist but disagree — prefer LARGER value
                # Rationale: truncated Thai (missing leading word) always gives smaller;
                # garbled OCR digits also tend to lose leading digits
                best = max(digit_val, thai_val)
                result["_confidence"][field_name] = f"low:digit={digit_val},thai={thai_val}"
                return best
        elif thai_val:
            result["_confidence"][field_name] = "medium:thai_only"
            return thai_val
        elif digit_val:
            result["_confidence"][field_name] = "medium:digit_only"
            return digit_val
        result["_confidence"][field_name] = "none"
        return None

    def find_stat_v2(keyword, unit, stop_keywords=None, alt_keywords=None):
        """Find stat with Thai text fallback and bounded search scope."""
        keywords = [keyword] + (alt_keywords or [])
        for kw in keywords:
            kw_match = re.search(re.escape(kw), text_d)
            if not kw_match:
                continue
            kw_end = kw_match.end()

            # Determine search limit (bounded by next section keyword)
            limit = 200
            if stop_keywords:
                for sk in stop_keywords:
                    sk_m = re.search(re.escape(sk), text_d[kw_end + 5:])
                    if sk_m:
                        limit = min(limit, sk_m.start() + 5)

            region_d = text_d[kw_end:kw_end + max(limit, 40)]
            region_orig = text[kw_match.end():kw_match.end() + max(limit, 40)]

            digit_val, thai_val = _extract_digit_and_thai(region_d, region_orig, unit)
            if digit_val or thai_val:
                return digit_val, thai_val
        return None, None

    # --- Section 1: ผู้มีสิทธิ (registered) and มาแสดงตน (turnout) ---
    # These use keyword matching with section boundaries

    d, t = find_stat_v2('บัญชีรายชื่อผู้มีสิทธิ', 'คน',
                        stop_keywords=['แสดงตน', 'มาใช้สิทธิ'],
                        alt_keywords=['ผู้มีสิทธิเลือกตั้ง'])
    result["registered_voters"] = _pick_best(d, t, "registered_voters")

    d, t = find_stat_v2('แสดงตน', 'คน',
                        stop_keywords=['จำนวนบัตร', 'จํานวนบัตร', 'ได้รับจัดสรร'],
                        alt_keywords=['มาใช้สิทธิ'])
    result["turnout"] = _pick_best(d, t, "turnout")

    # --- Section 2: ballot stats (positional extraction) ---
    # Cloud Vision reads labels and values in separate blocks.
    # Find ALL "จำนวน [X] บัตร ([Thai text])" patterns in order.
    ballot_vals = []  # list of (digit_val, thai_val, match_pos)
    for bm in re.finditer(r'จ[ำํา]นวน', text_d):
        bpos = bm.end()
        # Skip LABEL lines: "จำนวนบัตรเลือกตั้ง" (Thai consonant immediately after)
        if bpos < len(text_d) and re.match(r'[\u0E01-\u0E2E]', text_d[bpos:bpos+1]):
            continue  # label, not value
        # Also skip "จำนวนผู้" and "จำนวนคะแนน" (person/score descriptions)
        ahead_check = text_d[bpos:bpos + 8]
        if re.match(r'(?:ผู้|คะแนน)', ahead_check):
            continue
        # Find first "บัตร" within 40 chars
        ahead_d = text_d[bpos:bpos + 40]
        bat_m = re.search(r'บัตร', ahead_d)
        if not bat_m:
            continue
        # Skip if "คน" appears before "บัตร" (person count, not ballot)
        khon_m = re.search(r'คน', ahead_d)
        if khon_m and khon_m.start() < bat_m.start():
            continue
        # Skip if "ชุด" appears between จำนวน and บัตร (footnote "จำนวน ๑ ชุด")
        between_check = ahead_d[:bat_m.start()]
        if re.search(r'ชุด', between_check):
            continue
        # Extract digit from content BETWEEN จำนวน and บัตร (not beyond)
        between = ahead_d[:bat_m.start()]
        digit_val = None
        nums = re.findall(r'\d[\d,.]*', between)
        if nums:
            raw = nums[0]
            # Reject section numbers like "2.1.1", "2.2.2" (single digits separated by dots)
            if re.match(r'^\d\.\d(\.\d)+$', raw):
                pass  # section number, skip
            else:
                digit_val = extract_number(raw)
        # Extract Thai text from parentheses AFTER บัตร
        after_bat_orig = text[bpos + bat_m.end():bpos + bat_m.end() + 60]
        thai_val = None
        # Pass 1: strict — require closing paren
        pm = re.search(r'\(\s*([^)]{3,60})\s*\)', after_bat_orig)
        if pm:
            thai_val = thai_text_to_number(pm.group(1))
        # Pass 2: lenient — optional closing paren, but limit to same line and require result > 9
        if not thai_val:
            pm = re.search(r'\(\s*([^\n)]{3,40})', after_bat_orig)
            if pm:
                v = thai_text_to_number(pm.group(1))
                if v and v > 9:
                    thai_val = v
        if digit_val or thai_val:
            ballot_vals.append((digit_val, thai_val, bm.start()))

    # Map ballot values to fields by position:
    # Form order: received, used, valid, invalid, no_vote, remaining
    # But "used" is often = valid + invalid + no_vote (sometimes omitted)
    BALLOT_FIELDS = [
        ("ballots_received", None),
        ("_ballots_used", None),  # intermediate, not stored
        ("valid_ballots", None),
        ("invalid_ballots", None),
        ("no_vote_ballots", None),
        ("remaining_ballots", None),
    ]

    n = len(ballot_vals)
    if n >= 6:
        # Full: received, used, valid, invalid, no_vote, remaining
        assignments = [
            ("ballots_received", ballot_vals[0]),
            ("valid_ballots", ballot_vals[2]),
            ("invalid_ballots", ballot_vals[3]),
            ("no_vote_ballots", ballot_vals[4]),
            ("remaining_ballots", ballot_vals[-1]),
        ]
    elif n == 5:
        # No "used": received, valid, invalid, no_vote, remaining
        assignments = [
            ("ballots_received", ballot_vals[0]),
            ("valid_ballots", ballot_vals[1]),
            ("invalid_ballots", ballot_vals[2]),
            ("no_vote_ballots", ballot_vals[3]),
            ("remaining_ballots", ballot_vals[4]),
        ]
    elif n == 4:
        # Likely: received, valid, (invalid or no_vote), remaining
        assignments = [
            ("ballots_received", ballot_vals[0]),
            ("valid_ballots", ballot_vals[1]),
            ("invalid_ballots", ballot_vals[2]),
            ("remaining_ballots", ballot_vals[3]),
        ]
    elif n == 3:
        # Most likely: received, valid, remaining
        assignments = [
            ("ballots_received", ballot_vals[0]),
            ("valid_ballots", ballot_vals[1]),
            ("remaining_ballots", ballot_vals[2]),
        ]
    elif n == 2:
        # Likely: received, remaining
        assignments = [
            ("ballots_received", ballot_vals[0]),
            ("remaining_ballots", ballot_vals[1]),
        ]
    elif n == 1:
        assignments = [("ballots_received", ballot_vals[0])]
    else:
        assignments = []

    for field, (dv, tv, _) in assignments:
        result[field] = _pick_best(dv, tv, field)

    # For any ballot fields still None, try keyword-based fallback
    # Each entry: (field, keyword, unit, alt_keywords, stop_keywords)
    kw_fallbacks = [
        ("ballots_received", 'ได้รับจัดสรร', 'บัตร', ['รับจัดสรร'], ['บัตรดี', 'บัตรเสีย']),
        ("valid_ballots", 'บัตรดี', 'บัตร', None, ['บัตรเสีย', 'ไม่เลือก']),
        ("invalid_ballots", 'บัตรเสีย', 'บัตร', None, ['ไม่เลือก', 'ที่เหลือ']),
        ("no_vote_ballots", 'ไม่เลือกผู้สมัครผู้ใด', 'บัตร', ['ไม่ประสงค์'], ['ที่เหลือ', 'คะแนน']),
        ("remaining_ballots", 'เลือกตั้งที่เหลือ', 'บัตร', ['ที่เหลือ'], ['คะแนน', 'ผู้สมัคร']),
    ]
    for field, kw, unit, alts, stops in kw_fallbacks:
        if result.get(field) is None:
            d, t = find_stat_v2(kw, unit, alt_keywords=alts, stop_keywords=stops)
            if d or t:
                result[field] = _pick_best(d, t, field)

    # ---- Candidates (name-first approach) ----
    # Cloud Vision reads columns interleaved, so we anchor on NAME lines
    # (which are reliably detected) and search nearby for number/party/votes.

    name_prefix_re = re.compile(r'^(?:นาย|นาง(?:สาว)?|น\.?ส\.?|ม\.?ร\.?ว\.?|ส\.อ\.|ร\.ต\.|พ\.ต\.)')

    known_parties = [
        'ประชาชน', 'รวมไทยสร้างชาติ', 'ภูมิใจไทย', 'พลังประชารัฐ', 'เพื่อไทย',
        'ก้าวไกล', 'ประชาธิปัตย์', 'ไทยก้าวใหม่', 'ประชาธิปไตยใหม่',
        'ไทยทรัพย์ทวี', 'เศรษฐกิจ', 'กล้าธรรม', 'ทางเลือกใหม่',
        'ประชากรไทย', 'พลังประชาธิปไตย',
    ]

    # Thai number words (vote counts written in Thai) — NOT party names
    thai_number_words = {
        'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า', 'สิบ',
        'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน', 'ศูนย์',
        'สี่สิบ', 'สามสิบ', 'ยี่สิบ', 'ห้าสิบ', 'หกสิบ', 'เจ็ดสิบ', 'แปดสิบ', 'เก้าสิบ',
    }

    def is_party_name(s):
        s = s.strip()
        if not s or len(s) < 3:
            return False
        # Exclude Thai number words
        for w in thai_number_words:
            if s == w or s.startswith(w) and len(s) - len(w) < 3:
                return False
        # Exact/fuzzy match known parties
        for p in known_parties:
            if s in p or p in s:
                return True
        # Thai-only text, not a name prefix, at least 3 chars
        if re.match(r'^[\u0E00-\u0E7F\s]+$', s) and not name_prefix_re.match(s):
            if len(s) >= 3 and not re.match(r'^[\u0E50-\u0E59\d]+$', s.replace(' ', '')):
                return True
        return False

    def extract_thai_numeral(s):
        """Extract number from Thai numeral string like ๑, ๒, ๑๐, ๑)"""
        s = re.sub(r'[).:\s]+', '', s.strip())
        if re.match(r'^[\u0E50-\u0E59]+$', s):
            return extract_number(s)
        return None

    # Find candidate table region
    table_start = None
    table_end = None
    for i, line in enumerate(lines):
        if 'หมายเลขประจำ' in line or 'หมายเลขประจํา' in line:
            table_start = i
        if 'รวมคะแนนทั้งสิ้น' in line or 'รวมคะแนนทั้งสิน' in line:
            table_end = i
            break
    if table_start is None:
        for i, line in enumerate(lines):
            if 'ได้คะแนน' in line and 'รวม' not in line:
                table_start = i
                break
    if table_start is None:
        table_start = 0
    if table_end is None:
        table_end = len(lines)

    cand_lines = lines[table_start:table_end]
    cand_lines_d = lines_d[table_start:table_end]

    # Step 1: Find all name lines (anchor points)
    name_indices = []  # (index_in_cand_lines, name_text)
    for i, line in enumerate(cand_lines):
        line_s = line.strip()
        if not line_s:
            continue
        # Skip headers
        if any(kw in line_s for kw in ['หมายเลขประจำ', 'หมายเลขประจํา',
                'ชื่อตัว', 'ผู้สมัครรับเลือก', 'สังกัด',
                'พรรคการเมือง', 'ได้คะแนน',
                'ให้กรอกทั้ง', 'จำนวนคะแนน']):
            continue
        # Check for "๗ นายพลากร ภูมินอก" (Thai numeral + name on same line)
        m_tn = re.match(r'^([\u0E50-\u0E59]+)\s+(' + name_prefix_re.pattern[1:] + r'.+)$', line_s)
        if m_tn:
            num_val = extract_thai_numeral(m_tn.group(1))
            name_indices.append((i, m_tn.group(2).strip(), num_val))
            continue
        # Regular name line
        if name_prefix_re.match(line_s):
            name_indices.append((i, line_s, None))

    # Step 2: For each name, search nearby for number, party, votes
    candidates = []
    used_lines = set()

    for idx, (name_idx, name_text, inline_num) in enumerate(name_indices):
        cand = {"number": inline_num, "name": name_text, "party": None, "votes": None}
        used_lines.add(name_idx)

        # Search BACKWARD (up to 5 lines) for candidate number (Thai numeral)
        if cand["number"] is None:
            for j in range(name_idx - 1, max(name_idx - 6, -1), -1):
                if j < 0 or j in used_lines:
                    continue
                bline = cand_lines[j].strip()
                num_val = extract_thai_numeral(bline)
                if num_val and 1 <= num_val <= 30:
                    cand["number"] = num_val
                    used_lines.add(j)
                    break
                # Also try pure arabic digit (e.g. "1)")
                bline_d = cand_lines_d[j].strip()
                clean = re.sub(r'[).:\s]+', '', bline_d)
                if clean.isdigit() and 1 <= int(clean) <= 30:
                    cand["number"] = int(clean)
                    used_lines.add(j)
                    break
                # Stop if we hit another name
                if name_prefix_re.match(bline):
                    break

        # Search FORWARD (up to 4 lines) for party and votes
        next_name_idx = name_indices[idx + 1][0] if idx + 1 < len(name_indices) else table_end - table_start
        search_end = min(name_idx + 5, next_name_idx)

        for j in range(name_idx + 1, search_end):
            if j >= len(cand_lines) or j in used_lines:
                continue
            fline = cand_lines[j].strip()
            fline_d = cand_lines_d[j].strip()
            if not fline:
                continue

            # Skip noise
            if len(fline) <= 2:
                continue

            # Party
            if cand["party"] is None and is_party_name(fline):
                cand["party"] = fline
                used_lines.add(j)
                continue

            # Votes (digits in the line)
            if cand["votes"] is None:
                nums = re.findall(r'\d+', fline_d)
                if nums:
                    v = int(nums[0])
                    if 0 <= v < 100000:
                        cand["votes"] = v
                        used_lines.add(j)
                        continue

        candidates.append(cand)

    result["candidates"] = candidates

    # Post-process: assign missing numbers based on sequence gaps
    # E.g., if we have [1, 2, None, None, 5], assign 3 and 4
    assigned_nums = {c["number"] for c in result["candidates"] if c.get("number")}
    unassigned = [c for c in result["candidates"] if not c.get("number")]
    if unassigned:
        # Find gaps in 1..max_num
        max_num = max(assigned_nums) if assigned_nums else 11
        available = [n for n in range(1, max_num + 2) if n not in assigned_nums]
        for c, n in zip(unassigned, available):
            c["number"] = n

    result["candidates"].sort(key=lambda c: c.get("number") or 99)

    # Total votes: "รวมคะแนนทั้งสิ้น" followed by number (may be on next line)
    # Take the LARGEST reasonable number (not the first), since OCR noise
    # may produce small numbers before the actual total
    total_match = re.search(r'รวมคะแนนทั้งสิ้น', text)
    if not total_match:
        total_match = re.search(r'รวมคะแนนทั้งสิน', text)  # OCR variant
    if total_match:
        after = text_d[total_match.end():]
        nums = re.findall(r'\d+', after[:300])
        best = None
        for n in nums:
            v = int(n)
            if 1 < v < 999999:
                if best is None or v > best:
                    best = v
        result["total_votes"] = best

    return result


# ============================================================
# Main processing
# ============================================================
def process_page(pdf_path, page_num, prov_dir, api_key, dpi=200, save_debug=False, debug_dir=None):
    """Process one PDF page with Cloud Vision."""
    meta = extract_metadata_from_path(pdf_path, prov_dir)

    png_bytes, total_pages = pdf_page_to_png_bytes(pdf_path, page_num, dpi)
    if png_bytes is None:
        return None, total_pages

    # Call Cloud Vision
    resp = call_vision_api(png_bytes, api_key)
    if "error" in resp:
        print(f"    ❌ API error: {resp['error']}")
        return {"error": str(resp["error"]), **meta, "page": page_num + 1}, total_pages

    # Extract text
    text = extract_text_from_response(resp)

    # Detect back page (signatures, notes — no candidate data)
    is_back = False
    if text:
        back_indicators = ['ประธานกรรมการประจำหน่วย', '(ลงชื่อ)', 'หมายเหตุ : ส.ส.']
        front_indicators = ['รายงานผลการนับคะแนน', 'หมายเลขประจำ', 'หมายเลขประจํา',
                           'ผู้สมัครรับเลือกตั้ง', 'รวมคะแนนทั้งสิ้น']
        back_score = sum(1 for b in back_indicators if b in text)
        front_score = sum(1 for f in front_indicators if f in text)
        if back_score >= 2 and front_score == 0:
            is_back = True

    # Save debug
    if save_debug and debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        base = re.sub(r'[^\w.-]', '_', os.path.basename(pdf_path))
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}_vision.txt"), 'w', encoding='utf-8') as f:
            f.write(text)
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}.png"), 'wb') as f:
            f.write(png_bytes)
        # Save full API response (with bounding boxes) for layout-aware parsing
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}_resp.json"), 'w', encoding='utf-8') as f:
            json.dump(resp, f, ensure_ascii=False)

    # Parse (skip back pages)
    if is_back:
        result = {
            "file": os.path.relpath(pdf_path, prov_dir),
            "page": page_num + 1,
            "total_pages": total_pages,
            **meta,
            "is_back_page": True,
            "candidates": [],
            "ocr_text_length": len(text),
        }
        return result, total_pages

    # Use layout-aware parsing (falls back to text-only internally)
    parsed = parse_ss518_with_layout(resp)

    result = {
        "file": os.path.relpath(pdf_path, prov_dir),
        "page": page_num + 1,
        "total_pages": total_pages,
        **meta,
        **parsed,
        "is_back_page": False,
        "ocr_text_length": len(text),
    }

    return result, total_pages


# ============================================================
# Drive streaming (no local disk needed)
# ============================================================
def download_pdf_from_drive(file_id, api_key=None):
    """Download PDF bytes from Google Drive to memory. No disk I/O.
    Works with public files using API key, or direct download URL."""
    # Try API key method first (works for shared files)
    if api_key:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}"
        resp = requests.get(url, timeout=120)
        if resp.status_code == 200:
            return resp.content

    # Fallback: public download URL
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    session = requests.Session()
    resp = session.get(url, timeout=120, stream=True)

    # Handle virus scan warning for large files
    if resp.status_code == 200 and b'download_warning' in resp.content[:2000]:
        import re as _re
        m = _re.search(r'confirm=([^&]+)', resp.text)
        if m:
            url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={m.group(1)}"
            resp = session.get(url, timeout=120)

    if resp.status_code == 200:
        return resp.content
    raise Exception(f"Failed to download {file_id}: HTTP {resp.status_code}")


def extract_metadata_from_drive_entry(entry):
    """Build metadata dict from a Drive index entry."""
    constituency = entry.get("constituency")
    path = entry.get("path", "")
    name = entry.get("name", "")

    meta = {
        "province": entry.get("province", ""),
        "constituency": constituency,
        "district": None,
        "sub_district": None,
        "station_range": None,
        "vote_type": None,
        "form_type": "สส.5/18",
        "drive_file_id": entry.get("file_id"),
        "drive_view_url": entry.get("view_url"),
    }

    # Try extract district from path
    import re as _re
    for part in path.split("/"):
        m = _re.match(r'อำเภอ(.+)', part)
        if m:
            meta["district"] = m.group(1).strip()
            break

    # Sub-district from filename
    m = _re.search(r'ต\.(.+?)[-_]', name)
    if m:
        meta["sub_district"] = m.group(1).strip()

    # Station range from filename
    m = _re.search(r'หน่วยที่\s*(\d+)-(\d+)', name)
    if m:
        meta["station_range"] = f"{m.group(1)}-{m.group(2)}"

    # Vote type
    if 'แบ่งเขต' in name or 'แบ่งเขต' in path:
        meta["vote_type"] = "แบ่งเขต"
    if 'บัญชีรายชื่อ' in name or 'บัญชีรายชื่อ' in path:
        meta["vote_type"] = "บัญชีรายชื่อ" if not meta["vote_type"] else "แบ่งเขต+บัญชีรายชื่อ"

    if '5_16' in name:
        meta["form_type"] = "สส.5/16"
    elif '5_17' in name:
        meta["form_type"] = "สส.5/17"

    return meta


def process_page_from_bytes(pdf_bytes, page_num, meta, api_key, dpi=200,
                            save_debug=False, debug_dir=None, file_label=""):
    """Process one PDF page from in-memory bytes (streamed from Drive)."""
    png_bytes, total_pages = pdf_bytes_to_png(pdf_bytes, page_num, dpi)
    if png_bytes is None:
        return None, total_pages

    # Call Cloud Vision
    resp = call_vision_api(png_bytes, api_key)
    if "error" in resp:
        print(f"    ❌ API error: {resp['error']}")
        return {"error": str(resp["error"]), **meta, "page": page_num + 1}, total_pages

    text = extract_text_from_response(resp)

    # Detect back page
    is_back = False
    if text:
        back_indicators = ['ประธานกรรมการประจำหน่วย', '(ลงชื่อ)', 'หมายเหตุ : ส.ส.']
        front_indicators = ['รายงานผลการนับคะแนน', 'หมายเลขประจำ', 'หมายเลขประจํา',
                           'ผู้สมัครรับเลือกตั้ง', 'รวมคะแนนทั้งสิ้น']
        back_score = sum(1 for b in back_indicators if b in text)
        front_score = sum(1 for f in front_indicators if f in text)
        if back_score >= 2 and front_score == 0:
            is_back = True

    # Save debug
    if save_debug and debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        base = re.sub(r'[^\w.-]', '_', file_label or 'drive_file')
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}_vision.txt"), 'w', encoding='utf-8') as f:
            f.write(text)
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}.png"), 'wb') as f:
            f.write(png_bytes)
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}_resp.json"), 'w', encoding='utf-8') as f:
            json.dump(resp, f, ensure_ascii=False)

    if is_back:
        result = {
            "file": file_label,
            "page": page_num + 1,
            "total_pages": total_pages,
            **meta,
            "is_back_page": True,
            "candidates": [],
            "ocr_text": text,
            "ocr_text_length": len(text),
        }
        return result, total_pages

    parsed = parse_ss518_with_layout(resp)
    result = {
        "file": file_label,
        "page": page_num + 1,
        "total_pages": total_pages,
        **meta,
        **parsed,
        "is_back_page": False,
        "ocr_text": text,
        "ocr_text_length": len(text),
    }
    return result, total_pages


def main():
    parser = argparse.ArgumentParser(description="OCR สส.5/18 ด้วย Cloud Vision")
    parser.add_argument("--file", help="ไฟล์เดียว")
    parser.add_argument("--grep", help="ค้นหาไฟล์จากชื่อ pattern (เช่น 'หนองขาม-แบ่งเขต')")
    parser.add_argument("--all", action="store_true", help="ทุกไฟล์")
    parser.add_argument("--page", type=int, default=None, help="เฉพาะหน้า (0-indexed)")
    parser.add_argument("--dpi", type=int, default=200, help="DPI")
    parser.add_argument("--debug", action="store_true", help="บันทึก debug")
    parser.add_argument("--limit", type=int, default=1, help="จำนวนไฟล์ทดสอบ")
    parser.add_argument("--max-pages", type=int, default=3, help="จำนวนหน้าสูงสุดต่อไฟล์ (ประหยัด API quota)")
    parser.add_argument("--ss518-only", action="store_true", help="เฉพาะไฟล์ สส.5/18 (ข้ามสส.5/16, 5/17)")
    parser.add_argument("--resume", action="store_true", help="ข้ามไฟล์ที่ OCR แล้ว (resume)")
    parser.add_argument("--province", default="ชัยภูมิ", help="ชื่อจังหวัด (ภาษาไทย เช่น ชัยภูมิ, อ่างทอง)")
    parser.add_argument("--drive", action="store_true",
                        help="Stream PDF จาก Google Drive (ไม่ต้องดาวน์โหลดลง disk) — ใช้ drive_index_{slug}.json")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("❌ Google Cloud API Key not found!")
        print("   Set env: GOOGLE_CLOUD_API_KEY=<your-key>")
        print("   Or create .env file in project root with: GOOGLE_CLOUD_API_KEY=<your-key>")
        sys.exit(1)

    print(f"✅ API Key found ({api_key[:8]}...)")

    debug_dir = os.path.join(DATA_DIR, "ocr_debug_vision") if args.debug else None

    prov_name = args.province
    prov_slug = PROVINCE_SLUGS.get(prov_name, re.sub(r'[^\w]', '', prov_name))
    print(f"🗺️  Province: {prov_name} ({prov_slug})")

    # ========== Drive mode: stream from Google Drive ==========
    if args.drive:
        index_path = os.path.join(DATA_DIR, f"drive_index_{prov_slug}.json")
        if not os.path.exists(index_path):
            print(f"❌ ไม่พบ Drive index: {index_path}")
            print(f"   สร้างก่อน: python scripts/build_drive_index.py --provinces N")
            sys.exit(1)

        with open(index_path, 'r', encoding='utf-8') as f:
            drive_index = json.load(f)
        print(f"📡 Drive mode: {len(drive_index)} PDFs จาก drive_index_{prov_slug}.json")

        # Filter by grep
        if args.grep:
            drive_index = [e for e in drive_index if args.grep in e.get("name", "")]
            print(f"   Filtered by '{args.grep}': {len(drive_index)} files")

        if not args.all:
            drive_index = drive_index[:args.limit]

        # Resume support
        out_json = os.path.join(DATA_DIR, f"ocr_vision_{prov_slug}.json")
        existing_results = []
        done_files = set()
        if args.resume and os.path.exists(out_json):
            with open(out_json, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
            done_files = set(r.get('drive_file_id', r.get('file', '')) for r in existing_results)
            before = len(drive_index)
            drive_index = [e for e in drive_index if e["file_id"] not in done_files]
            print(f"📄 Files: {len(drive_index)} (skipped {before - len(drive_index)} already done)")
        else:
            print(f"📄 Files: {len(drive_index)}")
        print(f"⚙️  Max pages/file: {args.max_pages}")

        all_results = list(existing_results)
        api_calls = 0
        save_every = 5

        for i, entry in enumerate(drive_index):
            file_id = entry["file_id"]
            file_name = entry.get("name", file_id)
            file_path_label = entry.get("path", "")
            if file_path_label:
                file_label = f"{file_path_label}/{file_name}"
            else:
                file_label = file_name
            sz = entry.get("size", 0)

            print(f"\n[{i+1}/{len(drive_index)}] 📡 {file_label} ({sz:,} bytes)")

            # Download PDF to memory
            try:
                pdf_bytes = download_pdf_from_drive(file_id, api_key)
                print(f"  ⬇️  Downloaded {len(pdf_bytes):,} bytes to memory")
            except Exception as e:
                print(f"  ❌ Download failed: {e}")
                time.sleep(3)
                try:
                    pdf_bytes = download_pdf_from_drive(file_id, api_key)
                    print(f"  ⬇️  Retry OK: {len(pdf_bytes):,} bytes")
                except Exception as e2:
                    print(f"  ❌ Retry failed: {e2}")
                    all_results.append({
                        "file": file_label, "error": str(e2),
                        **extract_metadata_from_drive_entry(entry),
                    })
                    continue

            # Get total pages
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                total_pages = len(doc)
                doc.close()
            except Exception as e:
                print(f"  ❌ PDF corrupt: {e}")
                continue

            meta = extract_metadata_from_drive_entry(entry)

            if args.page is not None:
                pages_to_process = [args.page]
            else:
                pages_to_process = list(range(min(total_pages, args.max_pages)))
                print(f"  Total pages: {total_pages}, processing: {len(pages_to_process)}")

            for pg in pages_to_process:
                try:
                    result, _ = process_page_from_bytes(
                        pdf_bytes, pg, meta, api_key, args.dpi,
                        args.debug, debug_dir, file_label)
                except Exception as e:
                    print(f"  ⚠️ Error on p{pg+1}: {e}")
                    time.sleep(5)
                    try:
                        result, _ = process_page_from_bytes(
                            pdf_bytes, pg, meta, api_key, args.dpi,
                            args.debug, debug_dir, file_label)
                    except Exception as e2:
                        print(f"  ❌ Retry failed p{pg+1}: {e2}")
                        result = None
                api_calls += 1

                if result:
                    all_results.append(result)
                    if "error" not in result:
                        if result.get("is_back_page"):
                            print(f"  p{pg+1}: (back page)")
                        else:
                            station = result.get("ocr_station_no", "?")
                            cands = len(result.get("candidates", []))
                            total_v = result.get("total_votes", "?")
                            voters = result.get("registered_voters", "?")
                            print(f"  p{pg+1}: station={station} voters={voters} cands={cands} total={total_v}")

                time.sleep(RATE_LIMIT_SEC)

            # Free memory
            del pdf_bytes

            # Incremental save
            if (i + 1) % save_every == 0:
                with open(out_json, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=2)
                print(f"  💾 Saved {len(all_results)} results (auto-save)")

        # Jump to summary/save section (shared with local mode)
        # Save final
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n{'='*60}")
        print(f"📊 Summary (Drive mode)")
        print(f"{'='*60}")
        print(f"  API calls: {api_calls}")
        print(f"  Pages processed: {len(all_results)}")
        print(f"  📁 JSON: {out_json}")
        return

    # ========== Local file mode (original) ==========
    prov_dir = find_province(prov_name)
    if not prov_dir and not args.file:
        print(f"❌ Province '{prov_name}' not found in {BASE}")
        avail = [d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))]
        print(f"   Available: {', '.join(sorted(avail)[:10])}...")
        sys.exit(1)

    if args.file:
        all_pdfs = [args.file]
        if not prov_dir:
            prov_dir = os.path.dirname(args.file)
    else:
        all_pdfs = []
        for dp, dn, fn in os.walk(prov_dir):
            for f in fn:
                if f.lower().endswith('.pdf'):
                    fp = os.path.join(dp, f)
                    # Filter by grep pattern
                    if args.grep and args.grep not in f:
                        continue
                    # Filter สส.5/18 only (แบ่งเขต/นอกเขต files)
                    if args.ss518_only:
                        if 'แบ่งเขต' not in f and 'นอกเขต' not in f:
                            continue
                    all_pdfs.append(fp)
        all_pdfs.sort(key=os.path.getsize)

        if not args.all:
            all_pdfs = all_pdfs[:args.limit]

    # Resume support: load existing results
    existing_results = []
    done_files = set()
    out_json = os.path.join(DATA_DIR, f"ocr_vision_{prov_slug}.json")
    if args.resume and os.path.exists(out_json):
        with open(out_json, 'r', encoding='utf-8') as f:
            existing_results = json.load(f)
        done_files = set(r['file'] for r in existing_results)
        before = len(all_pdfs)
        all_pdfs = [fp for fp in all_pdfs if os.path.relpath(fp, prov_dir) not in done_files]
        print(f"📄 Files: {len(all_pdfs)} (skipped {before - len(all_pdfs)} already done)")
    else:
        print(f"📄 Files: {len(all_pdfs)}")
    print(f"⚙️  Max pages/file: {args.max_pages}")

    all_results = list(existing_results)
    api_calls = 0

    save_every = 5  # incremental save every N files

    for i, fp in enumerate(all_pdfs):
        rel = os.path.relpath(fp, prov_dir)
        sz = os.path.getsize(fp)
        print(f"\n[{i+1}/{len(all_pdfs)}] 📄 {rel} ({sz:,} bytes)")

        if args.page is not None:
            pages_to_process = [args.page]
        else:
            # Get total pages
            with open(fp, "rb") as f:
                pdf_bytes = f.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total = len(doc)
            doc.close()
            pages_to_process = list(range(min(total, args.max_pages)))
            print(f"  Total pages: {total}, processing: {len(pages_to_process)}")

        for pg in pages_to_process:
            try:
                result, total = process_page(fp, pg, prov_dir, api_key, args.dpi, args.debug, debug_dir)
            except Exception as e:
                print(f"  ⚠️ Error on p{pg+1}: {e}")
                # Wait and retry once
                time.sleep(5)
                try:
                    result, total = process_page(fp, pg, prov_dir, api_key, args.dpi, args.debug, debug_dir)
                except Exception as e2:
                    print(f"  ❌ Retry failed p{pg+1}: {e2}")
                    result = None
            api_calls += 1

            if result:
                all_results.append(result)
                if "error" not in result:
                    if result.get("is_back_page"):
                        print(f"  p{pg+1}: (back page - signatures/notes, skipped)")
                    else:
                        station = result.get("ocr_station_no", "?")
                        cands = len(result.get("candidates", []))
                        total_v = result.get("total_votes", "?")
                        voters = result.get("registered_voters", "?")
                        print(f"  p{pg+1}: station={station} voters={voters} cands={cands} total={total_v}")

            time.sleep(RATE_LIMIT_SEC)

        # Incremental save
        if (i + 1) % save_every == 0:
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"  💾 Saved {len(all_results)} results (auto-save)")

    # Summary
    print(f"\n{'='*60}")
    print("📊 Summary")
    print(f"{'='*60}")
    print(f"  API calls: {api_calls}")
    print(f"  Pages processed: {len(all_results)}")

    with_station = sum(1 for r in all_results if r.get("ocr_station_no"))
    with_cands = sum(1 for r in all_results if len(r.get("candidates", [])) > 0)
    with_total = sum(1 for r in all_results if r.get("total_votes") is not None)
    with_voters = sum(1 for r in all_results if r.get("registered_voters") is not None)

    print(f"  With station no: {with_station}")
    print(f"  With voters: {with_voters}")
    print(f"  With candidates: {with_cands}")
    print(f"  With total votes: {with_total}")

    # Save
    # out_json already defined above
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 JSON: {out_json}")

    if all_results:
        out_csv = os.path.join(DATA_DIR, f"ocr_vision_{prov_slug}.csv")
        fields = ["file", "page", "total_pages", "province", "constituency",
                   "district", "sub_district", "station_range", "vote_type", "form_type",
                   "ocr_vote_type", "ocr_constituency", "ocr_station_no", "ocr_village_no",
                   "ocr_sub_district", "ocr_district",
                   "registered_voters", "turnout", "ballots_received",
                   "valid_ballots", "invalid_ballots", "no_vote_ballots", "remaining_ballots",
                   "total_votes", "candidates_count", "candidates_json"]
        with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for r in all_results:
                row = dict(r)
                row["candidates_count"] = len(r.get("candidates", []))
                row["candidates_json"] = json.dumps(r.get("candidates", []), ensure_ascii=False)
                writer.writerow(row)
        print(f"  📁 CSV: {out_csv}")

    # Show best sample
    for r in all_results:
        if r.get("candidates") or r.get("total_votes"):
            print(f"\n📋 Sample result:")
            sample = {k: v for k, v in r.items()}
            print(json.dumps(sample, ensure_ascii=False, indent=2))
            break


if __name__ == "__main__":
    main()
