# -*- coding: utf-8 -*-
"""
OCR สส.5/18 v2 — Hybrid approach:
1. Extract metadata from file/folder names (100% reliable)
2. Assess scan quality per page before OCR
3. OCR readable pages with tuned preprocessing
4. Export structured JSON/CSV

Usage:
  python scripts/ocr_ss518_v2.py                     # ทดสอบ 3 ไฟล์
  python scripts/ocr_ss518_v2.py --all                # ทุกไฟล์
  python scripts/ocr_ss518_v2.py --file <path>        # ไฟล์เดียว
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

THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')


def find_chaiyaphum():
    for d in os.listdir(BASE):
        if 'ชัยภูมิ' in d:
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
            return int(text)
        except ValueError:
            return None
    return None


# ============================================================
# PART 1: Metadata from file/folder paths
# ============================================================
def extract_metadata_from_path(filepath, prov_dir):
    """Extract constituency, district, sub-district, unit info from path."""
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

    # Constituency from folder name: "เขตเลือกตั้งที่ 7"
    for p in parts:
        m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', p)
        if m:
            meta["constituency"] = int(m.group(1))

    # District from folder name: "อำเภอแก้งคร้อ" or "อำเภอเมืองชัยภูมิ"
    for p in parts:
        m = re.match(r'อำเภอ(.+)', p)
        if not m:
            m = re.match(r'อำเภอ(.+)', p)
        if m:
            meta["district"] = m.group(1).strip()

    # Sub-district from filename or folder: "ต.หนองขาม-..." or "หนองทม-001-"
    m = re.search(r'ต\.(.+?)[-_]', fname)
    if m:
        meta["sub_district"] = m.group(1).strip()
    else:
        # Try: "ตำบลname" or just "name-001-"
        m = re.match(r'([^\-]+?)-(\d+)-', fname)
        if m:
            meta["sub_district"] = m.group(1).strip()

    # Station range from filename: "หน่วยที่ 1-14" or "-001-"
    m = re.search(r'หน่วยที่\s*(\d+)-(\d+)', fname)
    if m:
        meta["station_range"] = f"{m.group(1)}-{m.group(2)}"
    else:
        m = re.search(r'-(\d{3})-', fname)
        if m:
            meta["station_range"] = m.group(1)

    # Vote type
    if 'แบ่งเขต' in fname or 'แบ่งเขต' in rel:
        meta["vote_type"] = "แบ่งเขต"
    if 'บัญชีรายชื่อ' in fname or 'บัญชีรายชื่อ' in rel:
        if meta["vote_type"] == "แบ่งเขต":
            meta["vote_type"] = "แบ่งเขต+บัญชีรายชื่อ"
        else:
            meta["vote_type"] = "บัญชีรายชื่อ"

    # Form type from filename
    if '5_16' in fname or '5/16' in fname:
        meta["form_type"] = "สส.5/16"
    elif '5_17' in fname or '5/17' in fname:
        meta["form_type"] = "สส.5/17"
    else:
        meta["form_type"] = "สส.5/18"

    return meta


# ============================================================
# PART 2: PDF processing + quality assessment
# ============================================================
def pdf_page_to_image(pdf_path, page_num=0, dpi=300):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    if page_num >= total:
        doc.close()
        return None, total
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.samples
    w, h = pix.width, pix.height
    if pix.n == 4:
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(h, w)
    doc.close()
    return img, total


def assess_quality(img):
    """Assess scan quality: contrast, sharpness, text density."""
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    # Contrast: std deviation of pixel values
    contrast = np.std(gray)
    # Sharpness: Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = laplacian.var()
    # Quality score (heuristic)
    score = 0
    if contrast > 50:
        score += 1
    if contrast > 70:
        score += 1
    if sharpness > 100:
        score += 1
    if sharpness > 500:
        score += 1
    return {
        "contrast": round(contrast, 1),
        "sharpness": round(sharpness, 1),
        "quality_score": score,  # 0-4
        "readable": score >= 2,
    }


def preprocess_for_ocr(img):
    """Preprocess image for OCR with orientation correction."""
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Orientation check
    h = gray.shape[0]
    top_mean = np.mean(gray[:h // 7])
    bot_mean = np.mean(gray[-h // 7:])
    if bot_mean > top_mean + 20:
        gray = cv2.rotate(gray, cv2.ROTATE_180)

    # Denoise
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    # Adaptive threshold
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 15
    )
    return binary


# ============================================================
# PART 3: OCR + Parsing
# ============================================================
def ocr_page(binary_img):
    pil_img = Image.fromarray(binary_img)
    try:
        text = pytesseract.image_to_string(pil_img, lang='tha+eng', config='--psm 6')
        return text.strip()
    except Exception as e:
        return ""


def parse_ocr_text(text):
    """Parse structured data from OCR text."""
    parsed = {
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

    # Constituency
    m = re.search(r'เขตเลือกต[ัั้ง]*ที[่่ ]*(\d+)', text_d)
    if m:
        parsed["ocr_constituency"] = extract_number(m.group(1))

    # Province
    m = re.search(r'จังหวัด\s*([\u0E00-\u0E7F]{2,})', text)
    if m:
        parsed["ocr_province"] = m.group(1).strip()

    # Station number
    m = re.search(r'หน่วยเลือกต[ัั้ง]*ที[่่ ]*(\d+)', text_d)
    if m:
        parsed["ocr_station_no"] = extract_number(m.group(1))

    # Village number
    m = re.search(r'หมู่ที[่่ ]*(\d+)', text_d)
    if m:
        parsed["ocr_village_no"] = extract_number(m.group(1))

    # Sub-district: "ตําบล...หนองทม"
    m = re.search(r'ต[ํำ]า?บล[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})', text)
    if m and m.group(1) not in ('แขวง', 'เทศบาล'):
        parsed["ocr_sub_district"] = m.group(1).strip()

    # District
    m = re.search(r'อ[ํำ]า?เภอ[^\u0E00-\u0E7F]*([\u0E00-\u0E7F]{2,})', text)
    if m and m.group(1) not in ('เขต',):
        parsed["ocr_district"] = m.group(1).strip()

    # Vote statistics — extract digits near keywords
    def find_stat_number(pattern):
        m = re.search(pattern, text_d, re.DOTALL)
        if m:
            nums = re.findall(r'\d+', m.group(0))
            for n in nums:
                v = int(n)
                if 0 < v < 999999:
                    return v
        return None

    parsed["registered_voters"] = find_stat_number(r'ผู้มีสิทธิ.{0,80}?(\d+)\s*คน')
    parsed["turnout"] = find_stat_number(r'(?:แสดงตน|มาใช้สิทธิ).{0,80}?(\d+)\s*คน')
    parsed["ballots_received"] = find_stat_number(r'ได้รับ.{0,80}?(\d+)\s*บัตร')
    parsed["valid_ballots"] = find_stat_number(r'บัตรดี.{0,80}?(\d+)\s*บัตร')
    parsed["invalid_ballots"] = find_stat_number(r'บัตรเสีย.{0,60}?(\d+)')
    parsed["no_vote_ballots"] = find_stat_number(r'ไม่เลือก.{0,60}?(\d+)')
    parsed["remaining_ballots"] = find_stat_number(r'เหลือ.{0,60}?(\d+)\s*บัตร')

    # Candidates — find lines with Thai name prefixes
    name_prefix = r'(?:นาย|นาง(?:สาว)?|น\.?ส\.?)'
    for line in lines:
        line_d = line.translate(THAI_DIGITS).strip()
        if not line_d:
            continue
        if any(kw in line for kw in ['หมายเลขประจ', 'ผู้สมัคร', 'ให้กรอก', 'ชื่อตัว', 'พรรคการเมือง']):
            continue

        # Find name prefix in line
        nm = re.search(name_prefix + r'([\u0E00-\u0E7F\s]{3,})', line)
        if not nm:
            continue

        full_name = nm.group(0).strip()
        # Clean: remove excess trailing Thai that's actually party name
        # Split on multiple spaces (party is separated by spaces in the form)
        name_parts = re.split(r'\s{2,}', full_name)
        clean_name = name_parts[0].strip()
        party = name_parts[1].strip() if len(name_parts) > 1 else None

        # If no party from name split, look after name match
        if not party:
            after = line[nm.end():]
            pm = re.search(r'([\u0E00-\u0E7F]{2,})', after)
            if pm:
                party = pm.group(1).strip()

        # Candidate number: find digit before the name in the line
        before = line_d[:nm.start()]
        nums_before = re.findall(r'\d+', before)
        cand_num = None
        if nums_before:
            v = int(nums_before[-1])
            if 1 <= v <= 30:
                cand_num = v

        # Votes: digits after the name+party region
        all_nums = re.findall(r'\d+', line_d)
        votes = None
        if len(all_nums) >= 2:
            for n in reversed(all_nums):
                v = int(n)
                if v != cand_num and v < 100000:
                    votes = v
                    break

        if cand_num is not None:
            existing = [c["number"] for c in parsed["candidates"]]
            if cand_num not in existing:
                parsed["candidates"].append({
                    "number": cand_num,
                    "name": clean_name,
                    "party": party,
                    "votes": votes,
                })

    parsed["candidates"].sort(key=lambda c: c.get("number", 0))

    # Total votes
    m = re.search(r'รวมคะแนนทั้งสิ้น[^\d]{0,20}(\d[\d,. ]*)', text_d)
    if m:
        parsed["total_votes"] = extract_number(m.group(1))

    return parsed


# ============================================================
# PART 4: Main processing pipeline
# ============================================================
def process_file(pdf_path, prov_dir, dpi=300, save_debug=False, debug_dir=None):
    """Process one PDF: extract metadata + OCR each page."""
    meta = extract_metadata_from_path(pdf_path, prov_dir)
    rel = os.path.relpath(pdf_path, prov_dir)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    doc.close()

    pages = []
    for pg in range(total_pages):
        img, _ = pdf_page_to_image(pdf_path, pg, dpi)
        if img is None:
            continue

        quality = assess_quality(img)
        page_result = {
            "file": rel,
            "page": pg + 1,
            "total_pages": total_pages,
            **meta,
            "quality": quality,
        }

        if quality["readable"]:
            binary = preprocess_for_ocr(img)
            ocr_text = ocr_page(binary)
            parsed = parse_ocr_text(ocr_text)
            page_result.update(parsed)

            # Save debug
            if save_debug and debug_dir:
                os.makedirs(debug_dir, exist_ok=True)
                base = re.sub(r'[^\w.-]', '_', os.path.basename(pdf_path))
                with open(os.path.join(debug_dir, f"{base}_p{pg+1}.txt"), 'w', encoding='utf-8') as f:
                    f.write(ocr_text)

            station = parsed.get("ocr_station_no", "?")
            cands = len(parsed.get("candidates", []))
            total_v = parsed.get("total_votes", "?")
            print(f"    p{pg+1}: Q={quality['quality_score']} station={station} cands={cands} total={total_v}")
        else:
            page_result["candidates"] = []
            print(f"    p{pg+1}: Q={quality['quality_score']} (skipped - low quality)")

        pages.append(page_result)

    return pages


def main():
    parser = argparse.ArgumentParser(description="OCR สส.5/18 v2")
    parser.add_argument("--file", help="OCR ไฟล์เดียว")
    parser.add_argument("--all", action="store_true", help="ทุกไฟล์")
    parser.add_argument("--dpi", type=int, default=300, help="DPI")
    parser.add_argument("--debug", action="store_true", help="บันทึก debug")
    parser.add_argument("--limit", type=int, default=3, help="จำนวนไฟล์ทดสอบ (default: 3)")
    args = parser.parse_args()

    try:
        ver = pytesseract.get_tesseract_version()
        print(f"Tesseract: {ver}")
    except Exception as e:
        print(f"❌ Tesseract not found: {e}")
        sys.exit(1)

    debug_dir = os.path.join(DATA_DIR, "ocr_debug_v2") if args.debug else None

    prov_dir = find_chaiyaphum()
    if not prov_dir:
        print("❌ Chaiyaphum not found!")
        sys.exit(1)

    # Collect PDFs
    if args.file:
        all_pdfs = [args.file]
    else:
        all_pdfs = []
        for dp, dn, fn in os.walk(prov_dir):
            for f in fn:
                if f.lower().endswith('.pdf'):
                    fp = os.path.join(dp, f)
                    all_pdfs.append(fp)
        all_pdfs.sort(key=os.path.getsize)

        if not args.all:
            # Test: pick a few diverse files (small, medium, large)
            n = min(args.limit, len(all_pdfs))
            indices = [0, len(all_pdfs)//3, len(all_pdfs)//2][:n]
            all_pdfs = [all_pdfs[i] for i in indices]
            print(f"🧪 Test mode: {len(all_pdfs)} files")

    print(f"📂 Province: {os.path.basename(prov_dir)}")
    print(f"📄 Files: {len(all_pdfs)}")

    # Step 1: Show metadata extraction (no OCR needed)
    print(f"\n{'='*60}")
    print("STEP 1: Metadata from file paths")
    print(f"{'='*60}")
    for fp in all_pdfs[:5]:
        meta = extract_metadata_from_path(fp, prov_dir)
        rel = os.path.relpath(fp, prov_dir)
        print(f"  📄 {rel}")
        print(f"     เขต={meta['constituency']} อำเภอ={meta['district']} ตำบล={meta['sub_district']} หน่วย={meta['station_range']} ประเภท={meta['vote_type']} ฟอร์ม={meta['form_type']}")

    # Step 2: OCR
    print(f"\n{'='*60}")
    print("STEP 2: OCR processing")
    print(f"{'='*60}")

    all_results = []
    for i, fp in enumerate(all_pdfs):
        rel = os.path.relpath(fp, prov_dir)
        sz = os.path.getsize(fp)
        print(f"\n[{i+1}/{len(all_pdfs)}] 📄 {rel} ({sz:,} bytes)")
        pages = process_file(fp, prov_dir, args.dpi, args.debug, debug_dir)
        all_results.extend(pages)

    # Summary
    print(f"\n{'='*60}")
    print("📊 Summary")
    print(f"{'='*60}")
    total_pages = len(all_results)
    readable = sum(1 for r in all_results if r.get("quality", {}).get("readable", False))
    with_cands = sum(1 for r in all_results if len(r.get("candidates", [])) > 0)
    with_total = sum(1 for r in all_results if r.get("total_votes") is not None)

    print(f"  Total pages: {total_pages}")
    print(f"  Readable (Q>=2): {readable} ({readable*100//max(total_pages,1)}%)")
    print(f"  With candidates: {with_cands}")
    print(f"  With total votes: {with_total}")

    # Quality distribution
    q_dist = {}
    for r in all_results:
        q = r.get("quality", {}).get("quality_score", -1)
        q_dist[q] = q_dist.get(q, 0) + 1
    print(f"  Quality distribution: {dict(sorted(q_dist.items()))}")

    # Save results (remove quality details for cleaner output)
    for r in all_results:
        if "quality" in r:
            r["quality_score"] = r["quality"]["quality_score"]
            r["readable"] = r["quality"]["readable"]
            del r["quality"]

    out_json = os.path.join(DATA_DIR, "ocr_results_chaiyaphum_v2.json")
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 JSON: {out_json}")

    # CSV
    if all_results:
        out_csv = os.path.join(DATA_DIR, "ocr_results_chaiyaphum_v2.csv")
        fields = ["file", "page", "total_pages", "province", "constituency",
                   "district", "sub_district", "station_range", "vote_type", "form_type",
                   "quality_score", "readable",
                   "ocr_constituency", "ocr_station_no", "ocr_sub_district", "ocr_district",
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

    # Show sample with candidates
    for r in all_results:
        if r.get("candidates"):
            print(f"\n📋 Best sample (with candidates):")
            sample = {k: v for k, v in r.items()}
            print(json.dumps(sample, ensure_ascii=False, indent=2))
            break


if __name__ == "__main__":
    main()
