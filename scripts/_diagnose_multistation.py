#!/usr/bin/env python3
"""Diagnose multi-station PDF consolidation issue."""
import json, os, sys, re
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
REVIEW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'review-app', 'public', 'data', 'review_data.json')

# 1) Check source OCR for multi-station files
print("=== SOURCE OCR: Multi-station PDFs ===")
all_records = []
for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    data = json.load(open(os.path.join(DATA_DIR, fname), encoding='utf-8'))
    all_records.extend(data)

# Group by file
by_file = defaultdict(list)
for r in all_records:
    by_file[r.get('file', '')].append(r)

# Find multi-station PDFs (>4 pages = multiple stations for แบ่งเขต)
multi_station_files = {f: recs for f, recs in by_file.items() 
                        if len(recs) > 4 and any('แบ่งเขต' in (r.get('vote_type','') or '') for r in recs)}

print(f"Files with >4 pages (potential multi-station): {len(multi_station_files)}")

# Check station_no coverage
no_stn = 0
has_stn = 0
stn_from_postprocess = 0
for f, recs in multi_station_files.items():
    for r in recs:
        stn = r.get('station_no') or r.get('ocr_station_no')
        if stn:
            has_stn += 1
        else:
            no_stn += 1

print(f"  Records with station_no: {has_stn}")
print(f"  Records WITHOUT station_no: {no_stn}")

# Show sample multi-station file
sample_files = sorted(multi_station_files.keys(), key=lambda f: -len(multi_station_files[f]))[:3]
for f in sample_files:
    recs = sorted(multi_station_files[f], key=lambda r: r.get('page', 0) or 0)
    print(f"\n  File: ...{f[-80:]}")
    print(f"  Pages: {len(recs)}")
    for r in recs[:8]:
        stn = r.get('station_no') or r.get('ocr_station_no')
        vt = r.get('vote_type', '?')
        ncands = len(r.get('candidates', []))
        page = r.get('page')
        bp = r.get('is_back_page', False)
        print(f"    p{page}: stn={stn}, vt={vt}, cands={ncands}, back={bp}")

# 2) Check review_data.json for the specific files from screenshots
print("\n=== REVIEW DATA: Specific files from screenshots ===")
review = json.load(open(REVIEW_PATH, encoding='utf-8'))

target_files = ['โคกสูง-001-แบ่งเขต', 'ลาดใหญ่-002-แบ่งเขต', 'โนนสำราญ-001-แบ่งเขต']
for target in target_files:
    matches = [r for r in review if target in (r.get('file', '') or '')]
    print(f"\n  '{target}': {len(matches)} review items")
    for m in matches[:5]:
        stn = m.get('ocr_station_no') or m.get('station_no')
        page = m.get('page')
        merged = m.get('_merged_pages')
        ncands = len(m.get('candidates', []))
        consol = m.get('_consolidated', False)
        print(f"    id={m.get('id')}, p={page}, merged={merged}, stn={stn}, cands={ncands}, consolidated={consol}")

# 3) Count review items from multi-station files
print("\n=== REVIEW DATA: Multi-station file coverage ===")
multi_review = [r for r in review if any(target in (r.get('file','') or '') for target in target_files)]
print(f"  Review items from target files: {len(multi_review)}")

# 4) How many review items have >10 candidates for แบ่งเขต? 
bk_over10 = [r for r in review if r.get('vote_type') == 'แบ่งเขต' 
             and len(r.get('candidates', [])) > 10]
print(f"\n=== แบ่งเขต items with >10 candidates: {len(bk_over10)} ===")
if bk_over10:
    # Check how many are from multi-station PDFs
    multi_page_over10 = [r for r in bk_over10 if r.get('_consolidated')]
    print(f"  Of those, consolidated: {len(multi_page_over10)}")
    cand_dist = Counter(len(r.get('candidates',[])) for r in bk_over10)
    print(f"  Candidate count distribution: {dict(sorted(cand_dist.items()))}")
    # Sample
    for r in bk_over10[:3]:
        print(f"  Sample: file=...{(r.get('file',''))[-60:]}, p={r.get('page')}, merged={r.get('_merged_pages')}, stn={r.get('ocr_station_no')}, cands={len(r.get('candidates',[]))}")
