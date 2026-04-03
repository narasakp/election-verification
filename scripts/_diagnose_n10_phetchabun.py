#!/usr/bin/env python3
"""Diagnose n=10 party list items from เพชรบูรณ์."""
import json, os, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')

review = json.load(open(REVIEW_PATH, encoding='utf-8'))
source = json.load(open(os.path.join(DATA_DIR, 'ocr_multimodel_phetchabun.json'), encoding='utf-8'))

# Group source by file
src_by_file = defaultdict(list)
for r in source:
    src_by_file[r.get('file', '')].append(r)

# Find n=10 party list items from phetchabun
n10 = [r for r in review 
       if r.get('vote_type') == 'บัญชีรายชื่อ' 
       and len(r.get('candidates', [])) == 10
       and r.get('province') == 'เพชรบูรณ์']

print(f"n=10 from เพชรบูรณ์: {len(n10)}")

# Check source coverage
for i, item in enumerate(n10[:5]):
    f = item.get('file', '')
    tp = item.get('total_pages')
    stn = item.get('ocr_station_no') or item.get('station_no')
    pg = item.get('page')
    merged = item.get('_merged_pages')
    
    print(f"\n  Sample {i+1}: stn={stn} page={pg} tp={tp} merged={merged}")
    print(f"    file=...{f[-65:]}")
    
    # Check source
    src_recs = src_by_file.get(f, [])
    if not src_recs:
        print(f"    Source: NOT FOUND")
        continue
    
    # Show party list pages for this station
    pps = 4
    if tp and int(tp) > 4:
        stn_int = int(stn) if stn and str(stn).isdigit() else 0
        base = (stn_int - 1) * pps
        stn_pages = [r for r in src_recs if base < r.get('page', 0) <= base + pps]
    else:
        stn_pages = src_recs
    
    stn_pages.sort(key=lambda r: r.get('page', 0))
    print(f"    Source pages for station (4pp calc):")
    for r in stn_pages:
        nc = len(r.get('candidates', []))
        vt = r.get('vote_type', '?')[:15]
        back = r.get('is_back_page', False)
        nums = sorted([c.get('number') for c in (r.get('candidates') or []) if c.get('number') is not None])
        nr = f"{min(nums)}-{max(nums)}" if nums else "-"
        print(f"      p={r.get('page')} vt={vt} back={back} cands={nc} nums={nr}")
    
    # Also show ALL source pages to check total coverage
    all_pl = [r for r in src_recs if 'บัญชีรายชื่อ' in (r.get('vote_type') or '') and not r.get('is_back_page')]
    print(f"    Total party list pages in file: {len(all_pl)} (of {len(src_recs)} total)")
    
    # Check missing pages
    existing = set(r.get('page') for r in src_recs)
    missing = [p for p in range(1, (tp or 0) + 1) if p not in existing]
    if missing:
        print(f"    Missing pages: {len(missing)} (e.g. {missing[:10]})")

# Unique file count
files = set(r.get('file') for r in n10)
print(f"\nUnique files: {len(files)}")

# Check: are these all from multi-station files?
multi = sum(1 for r in n10 if (r.get('total_pages') or 0) > 4)
single = len(n10) - multi
print(f"Multi-station: {multi}, Single-station: {single}")
