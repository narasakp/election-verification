#!/usr/bin/env python3
"""Find ALL remaining missing pages for บัญชีรายชื่อ multi-station files."""
import json, os, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')

sources = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))

print("=== Remaining missing pages for บัญชีรายชื่อ ===\n")

total_missing = 0
total_expected = 0

for slug, records in sources.items():
    # Group by file
    by_file = defaultdict(list)
    for r in records:
        by_file[r.get('file', '')].append(r)
    
    slug_missing = 0
    slug_expected = 0
    missing_positions = Counter()  # position within 4-page block
    
    for f, recs in by_file.items():
        tp = max((r.get('total_pages') or 0) for r in recs)
        if not tp or tp <= 4:
            continue
        
        # Check if file has party list data
        has_party = any('บัญชีรายชื่อ' in (r.get('vote_type') or '') for r in recs)
        if not has_party:
            continue
        
        existing_pages = set(r.get('page') for r in recs)
        
        # For each station, check which data pages exist
        n_stations = tp // 4
        for stn_idx in range(n_stations):
            base = stn_idx * 4  # 0-indexed
            # Data pages: base+1, base+2, base+3 (1-indexed)
            # Back page: base+4
            for pos in range(1, 4):  # positions 1,2,3 within station
                page_1idx = base + pos
                if page_1idx <= tp and page_1idx not in existing_pages:
                    slug_missing += 1
                    missing_positions[pos] += 1
                slug_expected += 1
    
    total_missing += slug_missing
    total_expected += slug_expected
    
    print(f"  {slug}: {slug_missing} missing / {slug_expected} expected data pages")
    print(f"    Position distribution: {dict(sorted(missing_positions.items()))}")

print(f"\n  TOTAL: {total_missing} missing data pages / {total_expected} expected")

# Also check: how many pages exist but have 0 candidates (potential misclassified back pages)?
print("\n\n=== Pages with 0 candidates (potential misclassified back) ===")
for slug, records in sources.items():
    by_file = defaultdict(list)
    for r in records:
        by_file[r.get('file', '')].append(r)
    
    zero_cand = 0
    zero_cand_back = 0
    zero_cand_front = 0
    
    for f, recs in by_file.items():
        tp = max((r.get('total_pages') or 0) for r in recs)
        if not tp or tp <= 4:
            continue
        has_party = any('บัญชีรายชื่อ' in (r.get('vote_type') or '') for r in recs)
        if not has_party:
            continue
        
        n_stations = tp // 4
        for r in recs:
            pg = r.get('page', 0)
            if pg <= 0:
                continue
            # Check if this is a data page position
            stn_idx = (pg - 1) // 4
            pos_in_stn = (pg - 1) % 4 + 1  # 1-based
            
            if stn_idx < n_stations and pos_in_stn <= 3:
                cands = len(r.get('candidates') or [])
                if cands == 0:
                    zero_cand += 1
                    if r.get('is_back_page'):
                        zero_cand_back += 1
                    else:
                        zero_cand_front += 1
    
    print(f"  {slug}: {zero_cand} data-position pages with 0 cands (back={zero_cand_back}, front={zero_cand_front})")
