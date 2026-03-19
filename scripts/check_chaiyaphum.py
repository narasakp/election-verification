#!/usr/bin/env python3
"""Check Chaiyaphum PDF files for batch OCR."""
import os
import glob

DL_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads', 'ss518')

# Find chaiyaphum folder (might be Thai name)
for d in os.listdir(DL_DIR):
    full = os.path.join(DL_DIR, d)
    if not os.path.isdir(full):
        continue
    if 'chaiyaphum' in d.lower() or 'ชัยภูมิ' in d:
        pdfs = [f for f in os.listdir(full) if f.lower().endswith('.pdf')]
        print(f"Folder: {d}")
        print(f"  PDFs: {len(pdfs)}")
        for p in sorted(pdfs)[:5]:
            size = os.path.getsize(os.path.join(full, p))
            print(f"    {p} ({size:,} bytes)")
        if len(pdfs) > 5:
            print(f"    ... and {len(pdfs)-5} more")

# Also check the data directory for existing Chaiyaphum OCR
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
ocr_json = os.path.join(DATA_DIR, 'ocr_vision_chaiyaphum.json')
if os.path.exists(ocr_json):
    import json
    data = json.load(open(ocr_json, 'r', encoding='utf-8'))
    files = set(d.get('file', '') for d in data)
    print(f"\nExisting OCR: {len(data)} pages from {len(files)} files")
    # Check which PDFs have been OCR'd
    for f in sorted(files)[:3]:
        print(f"  {f}")
