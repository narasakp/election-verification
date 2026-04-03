#!/usr/bin/env python3
"""Diagnose combined แบ่งเขต/บัญชีรายชื่อ files — show ALL pages."""
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

# Find combined files with party list pages having n=23
print("=== All pages in combined file (first sample) ===\n")

for slug, records in sources.items():
    by_file = defaultdict(list)
    for r in records:
        by_file[r.get('file', '')].append(r)
    
    found = 0
    for f, recs in by_file.items():
        if 'แบ่งเขต' not in f:
            continue
        has_pl = any('บัญชีรายชื่อ' in (r.get('vote_type') or '') for r in recs)
        if not has_pl:
            continue
        
        tp = max((r.get('total_pages', 0) or 0) for r in recs)
        if tp <= 4:
            continue
        
        recs.sort(key=lambda r: r.get('page', 0))
        
        print(f"File: ...{f[-70:]}")
        print(f"total_pages={tp}, records={len(recs)}")
        
        # Determine pages per station
        pl_pages = [r.get('page') for r in recs if 'บัญชีรายชื่อ' in (r.get('vote_type') or '') and not r.get('is_back_page')]
        if len(pl_pages) >= 2:
            gap = pl_pages[1] - pl_pages[0]
            print(f"Party list gap: {gap} pages/station")
            n_stations = tp // gap if gap > 0 else '?'
            print(f"Estimated stations: {n_stations}")
        
        # Show first 2 stations (all pages)
        show_pages = min(tp, 18)
        print(f"\nPage | VoteType        | Back | Cands | CandNums range")
        print("-" * 65)
        for pg in range(1, show_pages + 1):
            rec = next((r for r in recs if r.get('page') == pg), None)
            if rec:
                vt = (rec.get('vote_type') or '?')[:15]
                back = rec.get('is_back_page', False)
                cands = rec.get('candidates') or []
                nc = len(cands)
                nums = sorted([c.get('number') for c in cands if c.get('number') is not None])
                num_range = f"{min(nums)}-{max(nums)}" if nums else "-"
                print(f"  {pg:3d} | {vt:15s} | {'Y' if back else 'N':4s} | {nc:5d} | {num_range}")
            else:
                print(f"  {pg:3d} | {'--- NOT IN SOURCE ---':15s}")
        
        found += 1
        print()
        if found >= 2:
            break
    
    if found:
        break

# Count: how many n=23 items are from 6pp layout?
print("\n" + "="*60)
print("=== n!=57 item classification ===")

REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
review = json.load(open(REVIEW_PATH, encoding='utf-8'))
bad_pl = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ' and len(r.get('candidates', [])) != 57]

# Classify by file type
combined_6pp = 0  # files with both vote types
pure_party_4pp = 0  # pure party list files
unknown = 0

for item in bad_pl:
    f = item.get('file', '')
    # Check source data
    for slug, records in sources.items():
        file_recs = [r for r in records if r.get('file') == f]
        if not file_recs:
            continue
        has_both = (any('แบ่งเขต' in (r.get('vote_type') or '') for r in file_recs) and
                    any('บัญชีรายชื่อ' in (r.get('vote_type') or '') for r in file_recs))
        if has_both:
            combined_6pp += 1
        else:
            pure_party_4pp += 1
        break
    else:
        unknown += 1

print(f"Total n!=57: {len(bad_pl)}")
print(f"  Combined 6pp files: {combined_6pp}")
print(f"  Pure party 4pp files: {pure_party_4pp}")
print(f"  Unknown: {unknown}")

# For combined files: check what pages exist at expected party-list positions
print(f"\n=== Missing party list pages in combined files ===")
missing_pages_total = 0
misclassified_total = 0
truly_missing = 0

for slug, records in sources.items():
    by_file = defaultdict(list)
    for r in records:
        by_file[r.get('file', '')].append(r)
    
    for f, recs in by_file.items():
        tp = max((r.get('total_pages', 0) or 0) for r in recs)
        if tp <= 4:
            continue
        
        # Detect 6pp layout
        pl_pages = sorted(r.get('page') for r in recs 
                         if 'บัญชีรายชื่อ' in (r.get('vote_type') or '') and not r.get('is_back_page'))
        if len(pl_pages) < 2:
            continue
        
        gaps = [pl_pages[i+1] - pl_pages[i] for i in range(len(pl_pages)-1)]
        median_gap = sorted(gaps)[len(gaps)//2] if gaps else 0
        
        if median_gap != 6:
            continue
        
        # This is a 6pp layout file
        n_stations = tp // 6
        existing = {r.get('page'): r for r in recs}
        
        for stn_idx in range(n_stations):
            base = stn_idx * 6
            # Expected party list positions: base+4, base+5, base+6 (1-indexed)
            # Or: we know one is at base+5 (the detected one). Others at base+4 and base+6
            for offset in [4, 5, 6]:
                pg = base + offset
                if pg > tp:
                    continue
                
                rec = existing.get(pg)
                if rec:
                    vt = rec.get('vote_type') or ''
                    if 'บัญชีรายชื่อ' not in vt and not rec.get('is_back_page'):
                        misclassified_total += 1
                    elif rec.get('is_back_page'):
                        missing_pages_total += 1
                else:
                    truly_missing += 1
                    missing_pages_total += 1

print(f"  Misclassified as แบ่งเขต (actually party list): {misclassified_total}")
print(f"  Back pages at party list positions: {missing_pages_total - truly_missing}")
print(f"  Not in source at all: {truly_missing}")
