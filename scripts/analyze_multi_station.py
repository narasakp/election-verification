# -*- coding: utf-8 -*-
"""Analyze multi-station PDF structure in OCR data."""
import json, sys

data = json.load(open('data/ocr_multimodel_chaiyaphum.json', 'r', encoding='utf-8'))

# Find the specific file
target = 'จังหวัดชัยภูมิ/เขตเลือกตั้งที่ 1/อำเภอเมืองชัยภูมิ/แบ่งเขต/ต.กุดตุ้ม-แบ่งเขต-หน่วยที่ 1-18.pdf'
hits = [x for x in data if x.get('file') == target]
print(f"File: {target}")
print(f"Pages: {len(hits)}")
print()
for x in hits:
    p = x.get('page')
    stn = x.get('station_no')
    back = x.get('is_back_page')
    voters = x.get('registered_voters')
    votes = x.get('total_votes')
    cands = len(x.get('candidates', []))
    print(f"  page={p:2d}  stn={str(stn):>5s}  back={str(back):>5s}  voters={str(voters):>5s}  total_votes={str(votes):>5s}  cands={cands}")

# Count all multi-station files across all data
print("\n--- All multi-station PDFs ---")
from collections import Counter
file_pages = Counter()
for x in data:
    file_pages[x.get('file', '')] += 1

multi = {f: c for f, c in file_pages.items() if c > 4}
print(f"PDFs with >4 pages: {len(multi)}")
for f, c in sorted(multi.items()):
    print(f"  {c:3d} pages: {f}")
