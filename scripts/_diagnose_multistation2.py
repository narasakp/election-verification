#!/usr/bin/env python3
"""Diagnose why multi-station PDFs only produce 1 review item."""
import json, os, sys, re
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load chaiyaphum source OCR 
data = json.load(open(os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'), encoding='utf-8'))

# Find records for the specific files from screenshots
targets = ['โคกสูง-001-แบ่งเขต', 'โนนสำราญ-001-แบ่งเขต']

for target in targets:
    matches = [r for r in data if target in (r.get('file', '') or '')]
    print(f"\n=== SOURCE OCR: '{target}' — {len(matches)} records ===")
    matches.sort(key=lambda r: r.get('page', 0) or 0)
    for r in matches:
        stn = r.get('station_no') or r.get('ocr_station_no')
        page = r.get('page')
        tp = r.get('total_pages')
        vt = r.get('vote_type', '?')
        ncands = len(r.get('candidates', []))
        bp = r.get('is_back_page', False)
        print(f"  p{page}/{tp}: stn={stn}, vt={vt}, cands={ncands}, back={bp}")

# Count ALL multi-station แบ่งเขต PDFs (>4 pages) 
print("\n=== Multi-station แบ่งเขต summary (all provinces) ===")
all_records = []
for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    d = json.load(open(os.path.join(DATA_DIR, fname), encoding='utf-8'))
    all_records.extend(d)

by_file = defaultdict(list)
for r in all_records:
    by_file[r.get('file', '')].append(r)

# Multi-station = file has >4 records AND at least 1 แบ่งเขต front page
multi = {}
for f, recs in by_file.items():
    front_bk = [r for r in recs if r.get('vote_type') == 'แบ่งเขต' and not r.get('is_back_page')]
    if len(front_bk) > 1:
        multi[f] = front_bk

total_stations_missing = sum(len(recs) - 1 for recs in multi.values())
print(f"Multi-station แบ่งเขต files: {len(multi)}")
print(f"Total front pages in those files: {sum(len(v) for v in multi.values())}")
print(f"If only p1 appears, missing stations: {total_stations_missing}")

# Check: what pages get included in review_data
# Simulate the filtering in prepare_review_data.py
content = [r for r in all_records if not r.get('is_back_page')]
multi_content = {}
for f, recs in multi.items():
    content_recs = [r for r in recs if not r.get('is_back_page')]
    if content_recs:
        multi_content[f] = content_recs

print(f"\nAfter back_page filter: {sum(len(v) for v in multi_content.values())} front pages remain")

# Check station_no distribution in multi-station front pages
stn_set = 0
stn_none = 0
for f, recs in multi_content.items():
    for r in recs:
        if r.get('station_no') or r.get('ocr_station_no'):
            stn_set += 1
        else:
            stn_none += 1
print(f"  With station_no: {stn_set}")
print(f"  Without station_no: {stn_none}")

# Check how many UNIQUE (file, page) tuples exist for multi-station files
from collections import Counter
page_counts = Counter()
for f, recs in multi_content.items():
    pages = [r.get('page') for r in recs]
    page_counts[len(set(pages))] += 1
    if len(pages) != len(set(pages)):
        print(f"  DUPLICATE pages in {f[-60:]}: {sorted(pages)}")
print(f"\nUnique pages per file distribution: {dict(sorted(page_counts.items()))}")
