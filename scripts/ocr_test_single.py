# -*- coding: utf-8 -*-
"""
Quick test: OCR a single proper สส.5/18 file (per-unit, not สส.5/17)
and print the raw text + parsed results for tuning.
"""
import os
import sys
import json
import re
import fitz
import numpy as np
import cv2
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
THAI_DIGITS = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')

BASE = r'D:\Code\Election69\election-verification\downloads\ss518'
DATA_DIR = r'D:\Code\Election69\election-verification\data'

def find_chaiyaphum():
    for d in os.listdir(BASE):
        if 'ชัยภูมิ' in d:
            return os.path.join(BASE, d)
    return None

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

def preprocess(img):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    # Auto-rotation check
    h = gray.shape[0]
    top_mean = np.mean(gray[:h//7])
    bot_mean = np.mean(gray[-h//7:])
    if bot_mean > top_mean + 20:
        gray = cv2.rotate(gray, cv2.ROTATE_180)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 15)
    return binary

def main():
    prov = find_chaiyaphum()
    if not prov:
        print("Not found!")
        return

    # Find a proper สส.5/18 file (per-unit แบ่งเขต, small-ish)
    target = None
    for dp, dn, fn in os.walk(prov):
        for f in fn:
            if not f.lower().endswith('.pdf'):
                continue
            # Want: per-unit แบ่งเขต files (not สส.5/16, 5/17, not บัญชีรายชื่อ-only)
            if 'แบ่งเขต' in f and '5_16' not in f and '5_17' not in f and 'นอกเขต' not in f:
                fp = os.path.join(dp, f)
                sz = os.path.getsize(fp)
                if sz < 5_000_000:  # <5MB for speed
                    target = fp
                    break
        if target:
            break

    if not target:
        print("No suitable file found!")
        return

    rel = os.path.relpath(target, prov)
    print(f"📄 File: {rel}")
    print(f"   Size: {os.path.getsize(target):,} bytes")

    # Process first page
    img, total = pdf_page_to_image(target, 0, dpi=300)
    print(f"   Pages: {total}")

    binary = preprocess(img)

    # OCR
    pil_img = Image.fromarray(binary)
    text = pytesseract.image_to_string(pil_img, lang='tha+eng', config='--psm 6')

    print(f"\n{'='*60}")
    print(f"RAW OCR TEXT (page 1):")
    print(f"{'='*60}")
    for i, line in enumerate(text.split('\n'), 1):
        print(f"  {i:3d} | {line}")

    # Save
    out = os.path.join(DATA_DIR, 'ocr_debug', 'test_ss518_raw.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f"\n📁 Saved: {out}")

    # Also try with different PSM modes for comparison
    print(f"\n{'='*60}")
    print("Trying --psm 4 (column mode):")
    text4 = pytesseract.image_to_string(pil_img, lang='tha+eng', config='--psm 4')
    lines4 = text4.strip().split('\n')
    print(f"  Lines: {len(lines4)}")
    # Show lines with Thai name prefixes
    for i, line in enumerate(lines4, 1):
        if any(kw in line for kw in ['นาย', 'นาง', 'รวมคะแนน', 'บัตรดี', 'บัตรเสีย',
                                      'ผู้มีสิทธิ', 'แสดงตน', 'หน่วยเลือกตั้ง',
                                      'เขตเลือกตั้ง', 'จังหวัด', 'ตําบล', 'ตำบล', 'อําเภอ', 'อำเภอ']):
            print(f"  {i:3d} | {line}")


if __name__ == "__main__":
    main()
