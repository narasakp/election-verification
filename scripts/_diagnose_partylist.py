#!/usr/bin/env python3
"""Diagnose why 38% of บัญชีรายชื่อ items don't have n=57 candidates."""
import json, os, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')

# Load source OCR data
sources = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))

# Find บัญชีรายชื่อ records in source
print("=== SOURCE OCR: บัญชีรายชื่อ records ===")
for slug, records in sources.items():
    party = [r for r in records if 'บัญชีรายชื่อ' in (r.get('vote_type') or r.get('file') or '')]
    cand_dist = Counter(len(r.get('candidates', [])) for r in party)
    print(f"\n{slug}: {len(party)} records")
    for n, cnt in sorted(cand_dist.items()):
        if cnt >= 5:
            print(f"  n={n:3d}: {cnt}")

# Check consolidation: group by (file, station_no) and see page counts
print("\n\n=== CONSOLIDATION ANALYSIS ===")
for slug, records in sources.items():
    party = [r for r in records 
             if 'บัญชีรายชื่อ' in (r.get('vote_type') or r.get('file') or '')
             and not r.get('is_back_page')]
    
    # Group by (file, station_no)
    groups = defaultdict(list)
    for r in party:
        f = r.get('file', '')
        stn = r.get('station_no') or r.get('ocr_station_no') or 'none'
        groups[(f, str(stn))].append(r)
    
    # Check pages per group
    page_counts = Counter()
    total_cands_dist = Counter()
    for (f, stn), recs in groups.items():
        pages = sorted(r.get('page', 0) for r in recs)
        page_counts[len(pages)] += 1
        total_cands = sum(len(r.get('candidates', [])) for r in recs)
        total_cands_dist[total_cands] += 1
    
    print(f"\n{slug}: {len(groups)} groups (file+station)")
    print(f"  Pages per group: {dict(sorted(page_counts.items()))}")
    print(f"  Total candidates per group (top):")
    for n, cnt in sorted(total_cands_dist.items(), key=lambda x: -x[1])[:15]:
        print(f"    n={n:3d}: {cnt} groups")

# Deep dive: what do n=23/24 look like?
print("\n\n=== DEEP DIVE: n=23/24 items ===")
review_path = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
review = json.load(open(review_path, encoding='utf-8'))

n23_24 = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ' 
          and len(r.get('candidates', [])) in (23, 24)]
print(f"Total n=23/24: {len(n23_24)}")

# Check if consolidated or not
consol = sum(1 for r in n23_24 if r.get('_consolidated'))
print(f"  Consolidated: {consol}")
print(f"  Not consolidated: {len(n23_24) - consol}")

# Check merged_pages
has_merged = sum(1 for r in n23_24 if r.get('merged_pages'))
print(f"  Has merged_pages: {has_merged}")

# Province distribution
prov_dist = Counter(r.get('province') for r in n23_24)
print(f"  By province: {dict(prov_dist)}")

# Sample
for r in n23_24[:5]:
    f = r.get('file', '')[-70:]
    mp = r.get('merged_pages')
    tp = r.get('total_pages')
    stn = r.get('ocr_station_no') or r.get('station_no')
    print(f"  p={r.get('page')}/{tp} stn={stn} cands={len(r.get('candidates',[]))} merged={mp} file=...{f}")

# Check source records for a sample n=23 item
if n23_24:
    sample = n23_24[0]
    sample_file = sample.get('file', '')
    sample_stn = str(sample.get('ocr_station_no') or sample.get('station_no') or '')
    print(f"\n  Source records for: {sample_file[-60:]} stn={sample_stn}")
    for slug, records in sources.items():
        matching = [r for r in records if r.get('file') == sample_file]
        if matching:
            for r in sorted(matching, key=lambda x: x.get('page', 0)):
                nc = len(r.get('candidates', []))
                back = r.get('is_back_page', False)
                stn = r.get('station_no') or r.get('ocr_station_no') or '?'
                print(f"    p={r.get('page')} stn={stn} cands={nc} back={back} vt={r.get('vote_type','?')}")

# Check: how many total candidates if we sum ALL pages per file?
print("\n\n=== IF WE SUM ALL PAGES PER FILE ===")
for slug, records in sources.items():
    party = [r for r in records 
             if 'บัญชีรายชื่อ' in (r.get('vote_type') or r.get('file') or '')
             and not r.get('is_back_page')]
    
    by_file_stn = defaultdict(list)
    for r in party:
        f = r.get('file', '')
        stn = str(r.get('station_no') or r.get('ocr_station_no') or 'none')
        by_file_stn[(f, stn)].append(r)
    
    # For groups with total < 57, check if pages with different station_no exist
    underfilled = 0
    could_fix = 0
    for (f, stn), recs in by_file_stn.items():
        total = sum(len(r.get('candidates', [])) for r in recs)
        if total < 50:
            underfilled += 1
            # Check if same file has records with different station_no
            all_file_recs = [r for r in party if r.get('file') == f]
            all_total = sum(len(r.get('candidates', [])) for r in all_file_recs)
            if all_total >= 50:
                could_fix += 1
    
    print(f"  {slug}: underfilled={underfilled}, could fix by ignoring stn={could_fix}")
