# -*- coding: utf-8 -*-
"""
OCR สส.5/18 (ใบสรุปผลคะแนนรายหน่วยเลือกตั้ง) จาก scanned PDF
แปลงเป็น structured JSON/CSV

ฟอร์ม สส.5/18 มีโครงสร้าง:
- Header: เขตเลือกตั้งที่, จังหวัด, หน่วยเลือกตั้งที่, ตำบล, อำเภอ
- สถิติ: ผู้มีสิทธิ, ผู้มาใช้สิทธิ, บัตรได้รับ, บัตรดี, บัตรเสีย, บัตรไม่เลือก, บัตรเหลือ
- ตาราง: หมายเลขผู้สมัคร, ชื่อ, พรรค, คะแนน
- ท้าย: รวมคะแนนทั้งสิ้น

Usage:
  python scripts/ocr_ss518.py                          # ทดสอบกับไฟล์ตัวอย่าง
  python scripts/ocr_ss518.py --all                    # OCR ทุกไฟล์ชัยภูมิ
  python scripts/ocr_ss518.py --file <path>            # OCR ไฟล์เดียว
  python scripts/ocr_ss518.py --page <n>               # OCR เฉพาะหน้า n (0-indexed)
"""
import argparse
import csv
import json
import os
import re
import sys
import fitz  # PyMuPDF
import numpy as np
import cv2
import pytesseract
from PIL import Image

# --- Config ---
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, '..', 'downloads', 'ss518')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Thai number words → digits mapping
THAI_NUM_WORDS = {
    'ศูนย์': 0, 'หนึ่ง': 1, 'สอง': 2, 'สาม': 3, 'สี่': 4,
    'ห้า': 5, 'หก': 6, 'เจ็ด': 7, 'แปด': 8, 'เก้า': 9,
    'สิบ': 10, 'ยี่สิบ': 20, 'สามสิบ': 30, 'สี่สิบ': 40,
    'ร้อย': 100, 'พัน': 1000, 'หมื่น': 10000, 'แสน': 100000,
}

# Thai digits → Arabic digits
THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')


def find_chaiyaphum():
    for d in os.listdir(BASE):
        if 'ชัยภูมิ' in d:
            return os.path.join(BASE, d)
    return None


def pdf_page_to_image(pdf_path, page_num=0, dpi=300):
    """Convert a PDF page to a numpy array (BGR) for OpenCV processing."""
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    if page_num >= total_pages:
        doc.close()
        return None, total_pages

    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Convert to numpy array
    img_data = pix.samples
    w, h = pix.width, pix.height
    if pix.n == 4:  # RGBA
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:  # RGB
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:  # Grayscale
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w)

    doc.close()
    return img, total_pages


def preprocess_image(img):
    """Preprocess scanned image for better OCR accuracy."""
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Check if image is upside down by looking for the Garuda emblem at top
    # (simple heuristic: top 15% should be lighter than bottom 15% for correct orientation)
    h = gray.shape[0]
    top_mean = np.mean(gray[:h//7])
    bottom_mean = np.mean(gray[-h//7:])
    if bottom_mean > top_mean + 20:  # bottom is lighter → likely upside down
        gray = cv2.rotate(gray, cv2.ROTATE_180)
        img = cv2.rotate(img, cv2.ROTATE_180)

    # Adaptive thresholding for better text contrast
    # Use a mild approach to preserve handwritten numbers
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)

    # Adaptive threshold
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
    )

    return binary, gray, img


def extract_number(text):
    """Extract a number from OCR text (handles Thai digits, Arabic digits, mixed)."""
    if not text:
        return None

    # Replace Thai digits
    text = text.translate(THAI_DIGITS)

    # Remove common OCR noise
    text = text.strip().replace(',', '').replace('.', '').replace(' ', '')
    text = re.sub(r'[^\d]', '', text)

    if text:
        try:
            return int(text)
        except ValueError:
            return None
    return None


def ocr_region(img, x1, y1, x2, y2, lang='tha+eng', config='--psm 7'):
    """OCR a specific region of the image."""
    h, w = img.shape[:2]
    # Clamp coordinates
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 <= x1 or y2 <= y1:
        return ""

    roi = img[y1:y2, x1:x2]

    # Convert to PIL Image
    if len(roi.shape) == 2:
        pil_img = Image.fromarray(roi)
    else:
        pil_img = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))

    try:
        text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
        return text.strip()
    except Exception as e:
        return f"[OCR ERROR: {e}]"


def ocr_full_page(img_binary, lang='tha+eng'):
    """OCR the full page to get all text."""
    pil_img = Image.fromarray(img_binary)
    try:
        text = pytesseract.image_to_string(pil_img, lang=lang, config='--psm 6')
        return text.strip()
    except Exception as e:
        return f"[OCR ERROR: {e}]"


def parse_ss518_text(full_text):
    """Parse OCR'd text from สส.5/18 form into structured data.
    Tuned for actual Tesseract output on scanned Thai election forms."""
    result = {
        "form_type": "สส.5/18",
        "vote_type": None,
        "constituency": None,
        "province": None,
        "station_no": None,
        "village_no": None,
        "sub_district": None,
        "district": None,
        "registered_voters": None,
        "turnout": None,
        "ballots_received": None,
        "valid_ballots": None,
        "invalid_ballots": None,
        "no_vote_ballots": None,
        "remaining_ballots": None,
        "candidates": [],
        "total_votes": None,
        "raw_text": full_text,
    }

    lines = full_text.split('\n')
    # Normalize: Thai digits → Arabic for number extraction
    text_d = full_text.translate(THAI_DIGITS)

    # --- Vote type ---
    if 'แบ่งเขต' in full_text:
        result["vote_type"] = "แบ่งเขต"
    elif 'บัญชีรายชื่อ' in full_text:
        result["vote_type"] = "บัญชีรายชื่อ"

    # --- Constituency number ---
    # OCR may produce: "เขตเลือกตังที 9", "เขตเลือกตั้งที่ ๗"
    for pat in [r'เขตเลือกต[ัั้ง]*ที[่่]*\s*[.:]*\s*(\d+)',
                r'เขตเลือกต[ัั้ง]*ที[่่]*\s*[.:]*\s*([\d๐-๙]+)']:
        m = re.search(pat, text_d)
        if m:
            result["constituency"] = extract_number(m.group(1))
            break

    # --- Province ---
    # OCR may produce: "จังหวัด DUN", "จังหวัด ชัยภูมิ"
    m = re.search(r'จังหวัด\s*[.:]*\s*([\u0E00-\u0E7F]{2,})', full_text)
    if m:
        result["province"] = m.group(1).strip()

    # --- Station number ---
    # OCR: "หน่วยเลือกตั้งที่ AA" — often garbled handwriting
    m = re.search(r'หน่วยเลือกต[ัั้ง]*ที[่่]*\s*[.:]*\s*(\d+)', text_d)
    if m:
        result["station_no"] = extract_number(m.group(1))

    # --- Village number ---
    m = re.search(r'หมู่ที[่่]*\s*[.:]*\s*(\d+)', text_d)
    if m:
        result["village_no"] = extract_number(m.group(1))

    # --- Sub-district ---
    # OCR: "ตําบล/แขจร์/เทศมหล...หนองทม" → grab Thai word after dots/noise
    for pat in [
        r'ตํา?บล[/แขวง/เทศบาล]*[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})',
        r'ตำบล[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})',
    ]:
        m = re.search(pat, full_text)
        if m:
            val = m.group(1).strip()
            if val not in ('แขวง', 'เทศบาล', 'หมู่'):
                result["sub_district"] = val
                break

    # --- District ---
    for pat in [
        r'อํา?เภอ[/เขต]*[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})',
        r'อำเภอ[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})',
    ]:
        m = re.search(pat, full_text)
        if m:
            val = m.group(1).strip()
            if val not in ('เขต',):
                result["district"] = val
                break

    # --- Vote statistics ---
    # These are handwritten numbers — OCR is often garbled.
    # Use very loose patterns: find ANY digits near the keyword.
    def extract_stat(keyword_pattern, text):
        m = re.search(keyword_pattern, text)
        if m:
            # Find first plausible number in the matched region
            region = m.group(0)
            nums = re.findall(r'\d+', region)
            for n in nums:
                v = int(n)
                if 0 < v < 999999:  # sanity check
                    return v
        return None

    result["registered_voters"] = extract_stat(
        r'ผู้มีสิทธิ[\u0E00-\u0E7F]*ตามบัญชี.{0,80}?(\d[\d,.\s]{0,15})\s*คน', text_d)
    result["turnout"] = extract_stat(
        r'(?:แสดงตน|มาใช้สิทธิ).{0,60}?จ[ําำ]นวน[^\d]{0,10}(\d[\d,.\s]{0,15})\s*คน', text_d)
    result["ballots_received"] = extract_stat(
        r'ได้รับ(?:จัดสรร)?.{0,60}?จ[ําำ]นวน[^\d]{0,10}(\d[\d,.\s]{0,15})\s*บัตร', text_d)
    result["valid_ballots"] = extract_stat(
        r'บัตรดี.{0,60}?จ[ําำ]นวน[^\d]{0,10}(\d[\d,.\s]{0,15})\s*บัตร', text_d)
    result["invalid_ballots"] = extract_stat(
        r'บัตรเสีย.{0,60}?จ[ําำ]นวน[^\d]{0,10}(\d[\d,.\s]{0,15})', text_d)
    result["no_vote_ballots"] = extract_stat(
        r'ไม่เลือก.{0,60}?จ[ําำ]นวน[^\d]{0,10}(\d[\d,.\s]{0,15})', text_d)
    result["remaining_ballots"] = extract_stat(
        r'(?:บัตร.{0,20}?เหลือ|เลือกตั้งที่เหลือ).{0,60}?(\d[\d,.\s]{0,15})\s*บัตร', text_d)

    # --- Candidate table ---
    # Actual OCR output patterns:
    #   "| ๒ | นายกิติพร เศรษฐกภูมิภักดี     รวมไทยสร้างชาติ   - eX"
    #   " นายกิตติธัช คําวงษ์              ปรชาชน |..40202สสป .)"
    #   "| ๕ | นางสาวปัญชลีย์ วัฒนชัยศาสตร์ |   พลังประชารัฐ    - 2 0 ไโ0"
    # Strategy: find lines containing Thai name prefixes (นาย/นาง/นางสาว)
    # then extract candidate number, name, party, and any trailing digits

    name_prefixes = r'(?:นาย|นาง(?:สาว)?|น\.?ส\.?|ม\.?ร\.?ว\.?|ม\.?ล\.?)'

    for line in lines:
        line_d = line.translate(THAI_DIGITS).strip()
        if not line_d:
            continue

        # Skip header/label lines
        if any(kw in line for kw in ['หมายเลขประจ', 'ผู้สมัคร', 'ให้กรอก', 'ชื่อตัว', 'พรรคการเมือง']):
            continue

        # Pattern 1: Table with pipe separators
        # "| ๒ | นายกิติพร เศรษฐกภูมิภักดี     รวมไทยสร้างชาติ"
        m = re.search(
            r'(?:\|\s*)?([\d๐-๙]{1,2})\s*(?:\|\s*)?'
            + name_prefixes +
            r'([\u0E00-\u0E7F\s]{2,30})\s+'
            r'([\u0E00-\u0E7F]{2,})',
            line.translate(THAI_DIGITS)
        )
        if m:
            cand_num = extract_number(m.group(1))
            # Full name = prefix + rest
            name_start = m.start(2) - len(m.group(0)) + m.start(2) - m.start(0)
            raw_name = m.group(0)[m.start(2)-m.start(0):m.end(2)-m.start(0)]
            # Re-extract name and party from the original match
            name_match = re.search(name_prefixes + r'([\u0E00-\u0E7F\s]+)', line)
            if not name_match:
                continue
            full_name = name_match.group(0).strip()
            # Party: Thai text after the name (before any numbers/noise)
            after_name = line[name_match.end():]
            party_m = re.search(r'([\u0E00-\u0E7F]{2,})', after_name)
            party = party_m.group(1).strip() if party_m else None

            # Votes: find digits in the line (last group of digits)
            all_nums = re.findall(r'\d+', line_d)
            # First number is candidate number, votes might be a later one
            votes = None
            if len(all_nums) >= 2:
                # Try the last number that's not the candidate number
                for n in reversed(all_nums):
                    v = int(n)
                    if v != cand_num and v < 100000:
                        votes = v
                        break

            if cand_num and cand_num <= 30:
                candidate = {
                    "number": cand_num,
                    "name": full_name,
                    "party": party,
                    "votes": votes,
                }
                # Avoid duplicates
                existing_nums = [c["number"] for c in result["candidates"]]
                if cand_num not in existing_nums:
                    result["candidates"].append(candidate)

    # Sort candidates by number
    result["candidates"].sort(key=lambda c: c.get("number", 0))

    # --- Total votes ---
    m = re.search(r'รวมคะแนนทั้งสิ้น[^\d]{0,20}(\d[\d,. ]*)', text_d)
    if m:
        result["total_votes"] = extract_number(m.group(1))

    return result


def process_pdf_page(pdf_path, page_num=0, dpi=300, save_debug=False, debug_dir=None):
    """Process a single PDF page and return structured data."""
    img, total_pages = pdf_page_to_image(pdf_path, page_num, dpi)
    if img is None:
        return None, total_pages

    # Preprocess
    binary, gray, img_corrected = preprocess_image(img)

    # Full page OCR
    full_text = ocr_full_page(binary, lang='tha+eng')

    # Parse structured data
    result = parse_ss518_text(full_text)
    result["source_file"] = os.path.basename(pdf_path)
    result["page_number"] = page_num + 1
    result["total_pages"] = total_pages

    # Save debug images if requested
    if save_debug and debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        cv2.imwrite(os.path.join(debug_dir, f"{base}_p{page_num+1}_binary.png"), binary)
        # Save raw text
        with open(os.path.join(debug_dir, f"{base}_p{page_num+1}_text.txt"), 'w', encoding='utf-8') as f:
            f.write(full_text)

    return result, total_pages


def process_pdf_file(pdf_path, dpi=300, save_debug=False, debug_dir=None, specific_page=None):
    """Process all pages in a PDF file."""
    results = []

    if specific_page is not None:
        result, total = process_pdf_page(pdf_path, specific_page, dpi, save_debug, debug_dir)
        if result:
            results.append(result)
        return results

    # Get total pages first
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    doc.close()

    for pg in range(total_pages):
        print(f"    Page {pg+1}/{total_pages}...", end=" ", flush=True)
        result, _ = process_pdf_page(pdf_path, pg, dpi, save_debug, debug_dir)
        if result:
            results.append(result)
            # Quick summary
            station = result.get("station_no", "?")
            votes = result.get("total_votes", "?")
            cands = len(result.get("candidates", []))
            print(f"station={station}, candidates={cands}, total_votes={votes}")
        else:
            print("(skipped)")

    return results


def main():
    parser = argparse.ArgumentParser(description="OCR สส.5/18 จาก scanned PDF")
    parser.add_argument("--file", help="OCR ไฟล์เดียว")
    parser.add_argument("--all", action="store_true", help="OCR ทุกไฟล์ชัยภูมิ")
    parser.add_argument("--page", type=int, default=None, help="OCR เฉพาะหน้า (0-indexed)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI สำหรับ render PDF")
    parser.add_argument("--debug", action="store_true", help="บันทึกภาพ debug")
    parser.add_argument("--type", choices=["แบ่งเขต", "บัญชีรายชื่อ", "all"], default="แบ่งเขต",
                        help="ประเภทเอกสารที่จะ OCR")
    args = parser.parse_args()

    # Verify Tesseract is available
    try:
        ver = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {ver}")
    except Exception as e:
        print(f"❌ Tesseract not found: {e}")
        print(f"   Please install Tesseract OCR from:")
        print(f"   https://github.com/UB-Mannheim/tesseract/wiki")
        print(f"   Make sure to include Thai language data during installation.")
        print(f"   Expected path: {TESSERACT_CMD}")
        sys.exit(1)

    # Check Thai language data
    try:
        langs = pytesseract.get_languages()
        if 'tha' not in langs:
            print(f"⚠️ Thai language data not found in Tesseract!")
            print(f"   Available: {langs}")
            print(f"   Please reinstall Tesseract with Thai language selected.")
            sys.exit(1)
        print(f"Available languages: {langs}")
    except Exception:
        pass

    debug_dir = os.path.join(DATA_DIR, "ocr_debug") if args.debug else None

    if args.file:
        # OCR single file
        print(f"\n📄 Processing: {args.file}")
        results = process_pdf_file(args.file, args.dpi, args.debug, debug_dir, args.page)
    else:
        # Find Chaiyaphum folder
        prov_dir = find_chaiyaphum()
        if not prov_dir:
            print("❌ Chaiyaphum folder not found!")
            sys.exit(1)

        # Collect target PDFs
        all_pdfs = []
        for dp, dn, fn in os.walk(prov_dir):
            for f in fn:
                if not f.lower().endswith('.pdf'):
                    continue
                # Filter by type
                if args.type == "แบ่งเขต":
                    if 'แบ่งเขต' not in f and '5_16' not in f and '5_17' not in f:
                        continue
                    if 'บัญชีรายชื่อ' in f and 'แบ่งเขต' not in f:
                        continue
                elif args.type == "บัญชีรายชื่อ":
                    if 'บัญชีรายชื่อ' not in f:
                        continue
                all_pdfs.append(os.path.join(dp, f))

        all_pdfs.sort()

        if not args.all:
            # Test mode: just first 2 smallest files
            all_pdfs.sort(key=os.path.getsize)
            all_pdfs = all_pdfs[:2]
            print(f"🧪 Test mode: processing {len(all_pdfs)} smallest files")
        else:
            print(f"📂 Processing {len(all_pdfs)} PDF files")

        results = []
        for i, pdf_path in enumerate(all_pdfs):
            rel = os.path.relpath(pdf_path, prov_dir)
            print(f"\n[{i+1}/{len(all_pdfs)}] 📄 {rel}")
            page_results = process_pdf_file(pdf_path, args.dpi, args.debug, debug_dir, args.page)
            results.extend(page_results)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 OCR Summary")
    print(f"{'='*60}")
    print(f"  Total pages processed: {len(results)}")

    filled = sum(1 for r in results if r.get("station_no") is not None)
    with_candidates = sum(1 for r in results if len(r.get("candidates", [])) > 0)
    with_total = sum(1 for r in results if r.get("total_votes") is not None)

    print(f"  Pages with station number: {filled}")
    print(f"  Pages with candidates: {with_candidates}")
    print(f"  Pages with total votes: {with_total}")

    # Remove raw_text from output to keep file small
    for r in results:
        if "raw_text" in r:
            del r["raw_text"]

    # Save JSON
    out_json = os.path.join(DATA_DIR, "ocr_results_chaiyaphum.json")
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 JSON: {out_json}")

    # Save CSV
    if results:
        out_csv = os.path.join(DATA_DIR, "ocr_results_chaiyaphum.csv")
        fieldnames = [
            "source_file", "page_number", "form_type", "vote_type",
            "constituency", "province", "station_no", "village_no",
            "sub_district", "district",
            "registered_voters", "turnout", "ballots_received",
            "valid_ballots", "invalid_ballots", "no_vote_ballots", "remaining_ballots",
            "total_votes", "candidates_json",
        ]
        with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {k: r.get(k) for k in fieldnames if k != "candidates_json"}
                row["candidates_json"] = json.dumps(r.get("candidates", []), ensure_ascii=False)
                writer.writerow(row)
        print(f"  📁 CSV: {out_csv}")

    # Print sample results
    if results:
        print(f"\n📋 Sample result (first page):")
        sample = {k: v for k, v in results[0].items() if k != "raw_text"}
        print(json.dumps(sample, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
