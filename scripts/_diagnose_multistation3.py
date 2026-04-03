#!/usr/bin/env python3
"""Find the actual multi-station PDF problem in review_data.json."""
import json, os, sys
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')

review = json.load(open(REVIEW_PATH, encoding='utf-8'))

# 1) Find แบ่งเขต zone 1 ชัยภูมิ items
bk = [r for r in review if r.get('vote_type') == 'แบ่งเขต' 
      and r.get('province') == 'ชัยภูมิ' and r.get('constituency') == 1]
print(f"=== ชัยภูมิ zone 1 แบ่งเขต: {len(bk)} items ===")
for r in bk[:10]:
    stn = r.get('ocr_station_no') or r.get('station_no')
    page = r.get('page')
    tp = r.get('total_pages')
    ncands = len(r.get('candidates', []))
    merged = r.get('_merged_pages')
    consol = r.get('_consolidated', False)
    f = r.get('file', '')[-70:]
    print(f"  p={page}/{tp} stn={stn} cands={ncands} merged={merged} consol={consol} ...{f}")

# 2) Find ALL items with total_pages > 4 (multi-station PDFs)
multi_page = [r for r in review if r.get('vote_type') == 'แบ่งเขต' 
              and (r.get('total_pages') or 0) > 4]
print(f"\n=== แบ่งเขต items from multi-station PDFs (total_pages>4): {len(multi_page)} ===")

# How many have station_no?
with_stn = sum(1 for r in multi_page if r.get('ocr_station_no') or r.get('station_no'))
print(f"  With station_no: {with_stn}")
print(f"  Without station_no: {len(multi_page) - with_stn}")

# Group by file to see how many items per multi-station file
by_file = defaultdict(list)
for r in multi_page:
    by_file[r.get('file', '')].append(r)
items_per_file = Counter(len(v) for v in by_file.values())
print(f"  Unique files: {len(by_file)}")
print(f"  Items per file dist: {dict(sorted(items_per_file.items()))}")

# 3) Sample multi-station files with only 1 item
single_item_files = [(f, recs[0]) for f, recs in by_file.items() if len(recs) == 1]
print(f"\n=== Multi-station files with ONLY 1 review item: {len(single_item_files)} ===")
for f, r in single_item_files[:5]:
    stn = r.get('ocr_station_no') or r.get('station_no')
    page = r.get('page')
    tp = r.get('total_pages')
    ncands = len(r.get('candidates', []))
    src = r.get('_source_type', '?')
    print(f"  p={page}/{tp} stn={stn} cands={ncands} src={src} file=...{f[-80:]}")

# 4) Check: are there items with >10 candidates (multiple stations merged)?
over10 = [r for r in review if r.get('vote_type') == 'แบ่งเขต' and len(r.get('candidates', [])) > 10]
print(f"\n=== แบ่งเขต with >10 candidates: {len(over10)} ===")
cand_dist = Counter(len(r.get('candidates', [])) for r in over10)
print(f"  Distribution: {dict(sorted(cand_dist.items()))}")

# 5) Check total expected vs actual stations
total_expected_stations = 0
for f, recs in by_file.items():
    tp = max(r.get('total_pages', 0) or 0 for r in recs)
    expected = tp // 2  # 2 pages per station for แบ่งเขต
    total_expected_stations += expected
actual = sum(len(v) for v in by_file.values())
print(f"\n=== Station coverage ===")
print(f"  Expected stations (from total_pages): ~{total_expected_stations}")
print(f"  Actual review items: {actual}")
print(f"  Missing: ~{total_expected_stations - actual}")

# 6) Check source data for a sample multi-station file
DATA_DIR = os.path.join(ROOT, 'data')
for fname in ['ocr_multimodel_chaiyaphum.json']:
    src_data = json.load(open(os.path.join(DATA_DIR, fname), encoding='utf-8'))
    # Find a file that's in both source and review with total_pages > 4
    review_files = set(r.get('file', '') for r in multi_page)
    src_multi = [r for r in src_data if r.get('file', '') in review_files]
    if src_multi:
        sample_file = src_multi[0].get('file', '')
        file_recs = sorted([r for r in src_data if r.get('file') == sample_file],
                          key=lambda r: r.get('page', 0) or 0)
        print(f"\n=== SOURCE OCR sample: ...{sample_file[-80:]} ({len(file_recs)} records) ===")
        for r in file_recs[:12]:
            stn = r.get('station_no') or r.get('ocr_station_no')
            page = r.get('page')
            vt = r.get('vote_type', '?')
            bp = r.get('is_back_page', False)
            ncands = len(r.get('candidates', []))
            print(f"  p={page}: stn={stn} vt={vt} cands={ncands} back={bp}")
