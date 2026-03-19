# -*- coding: utf-8 -*-
"""Check OCR data vs image mapping for a specific file"""
import json, os, sys

DATA_FILE = os.path.join('data', 'ocr_vision_chaiyaphum.json')

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find the entry for หนองขาม 1-14
for d in data:
    if 'หนองขาม' in d.get('file', '') and '1-14' in d.get('file', ''):
        print("=== OCR Entry ===")
        print(f"File: {d['file']}")
        print(f"Page: {d['page']} / {d.get('total_pages')}")
        print(f"Station: {d.get('ocr_station_no')}")
        print(f"Village: {d.get('ocr_village_no')}")
        print(f"Sub-district (OCR): {d.get('ocr_sub_district')}")
        print()
        print("--- Statistics ---")
        print(f"Registered: {d.get('registered_voters')}")
        print(f"Turnout: {d.get('turnout')}")
        print(f"Ballots received: {d.get('ballots_received')}")
        print(f"Valid: {d.get('valid_ballots')}")
        print(f"Invalid: {d.get('invalid_ballots')}")
        print(f"No vote: {d.get('no_vote_ballots')}")
        print(f"Remaining: {d.get('remaining_ballots')}")
        print(f"Total votes: {d.get('total_votes')}")
        print()
        print("--- Candidates ---")
        for c in d.get('candidates', []):
            print(f"  #{c.get('number')} {c.get('name')} | {c.get('party')} | votes={c.get('votes')}")
        print()

        # Check the actual PDF page count
        import subprocess
        pdf_path = os.path.join('downloads', 'ss518', 'chaiyaphum', d['file'])
        if os.path.exists(pdf_path):
            print(f"PDF exists: {pdf_path}")
            print(f"PDF size: {os.path.getsize(pdf_path)} bytes")
            # Try to get page count
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                print(f"Actual PDF pages: {len(doc)}")
                doc.close()
            except ImportError:
                print("PyMuPDF not installed, can't check page count")
        else:
            print(f"PDF NOT FOUND: {pdf_path}")

        # Check debug image
        import re
        basename = os.path.basename(d['file'])
        sanitized = re.sub(r'[^\w.-]', '_', basename)
        debug_img = os.path.join('data', 'ocr_debug_vision', f"{sanitized}_p{d['page']}.png")
        if os.path.exists(debug_img):
            print(f"Debug image exists: {debug_img} ({os.path.getsize(debug_img)} bytes)")
        else:
            print(f"Debug image NOT FOUND: {debug_img}")
        
        # Check what the raw OCR text looks like
        raw_text_file = os.path.join('data', 'ocr_debug_vision', f"{sanitized}_p{d['page']}_raw.txt")
        if os.path.exists(raw_text_file):
            print(f"\n=== Raw OCR text ===")
            with open(raw_text_file, 'r', encoding='utf-8') as f:
                print(f.read()[:2000])
        break
