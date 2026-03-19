#!/usr/bin/env python3
"""Check how many Chaiyaphum files still need OCR."""
import os
import json

BASE = os.path.join(os.path.dirname(__file__), '..', 'downloads', 'ss518')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Find chaiyaphum
prov = None
for d in os.listdir(BASE):
    if '\u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34' in d:
        prov = os.path.join(BASE, d)
        break

if not prov:
    print("Chaiyaphum not found!")
    exit(1)

# Count all PDFs
all_pdfs = []
for dp, dn, fn in os.walk(prov):
    for f in fn:
        if f.lower().endswith('.pdf'):
            all_pdfs.append(os.path.join(dp, f))

# Categorize
ss518 = [f for f in all_pdfs if '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15' in f or '\u0e19\u0e2d\u0e01\u0e40\u0e02\u0e15' in f]
other = [f for f in all_pdfs if f not in ss518]
print(f"Total PDFs: {len(all_pdfs)}")
print(f"  \u0e2a\u0e2a.5/18 (\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15/\u0e19\u0e2d\u0e01\u0e40\u0e02\u0e15): {len(ss518)}")
print(f"  Other (\u0e1a\u0e31\u0e0d\u0e0a\u0e35\u0e23\u0e32\u0e22\u0e0a\u0e37\u0e48\u0e2d etc): {len(other)}")

# Already OCR'd
ocr_path = os.path.join(DATA_DIR, 'ocr_vision_chaiyaphum.json')
done_files = set()
if os.path.exists(ocr_path):
    ocr = json.load(open(ocr_path, 'r', encoding='utf-8'))
    done_files = set(r['file'] for r in ocr)
    print(f"Already OCR'd: {len(done_files)} unique files, {len(ocr)} pages")

# How many ss518 still need OCR?
remaining = []
for f in ss518:
    rel = os.path.relpath(f, prov)
    if rel not in done_files:
        remaining.append(rel)

print(f"Remaining \u0e2a\u0e2a.5/18 to OCR: {len(remaining)}")
print(f"Estimated API calls: ~{len(remaining) * 2}")

# Show sample of other files
if other:
    print(f"\nSample 'other' files:")
    for f in sorted(other)[:5]:
        print(f"  {os.path.relpath(f, prov)}")
