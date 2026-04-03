#!/usr/bin/env python3
"""Check candidate numbering across pages to understand dedup issue."""
import json, os, sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')

sources = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))

# Find a multi-page station and check candidate numbers across pages
print("=== Candidate numbering across pages ===")
for slug, records in sources.items():
    # Find บัญชีรายชื่อ records in multi-station files
    party = [r for r in records 
             if 'บัญชีรายชื่อ' in (r.get('vote_type') or '')
             and not r.get('is_back_page')
             and r.get('total_pages') and int(r.get('total_pages', 0)) > 4]
    
    # Group by file
    by_file = defaultdict(list)
    for r in party:
        by_file[r.get('file', '')].append(r)
    
    checked = 0
    renumbered = 0  # pages where numbering starts from 1
    continuous = 0  # pages with continuous numbering
    
    for f, recs in by_file.items():
        recs.sort(key=lambda r: r.get('page', 0))
        tp = max(r.get('total_pages', 0) for r in recs)
        
        # Check first station's pages
        n_stations = int(tp) // 4
        for stn_idx in range(min(n_stations, 3)):  # check first 3 stations
            base = stn_idx * 4
            stn_pages = [r for r in recs if base < r.get('page', 0) <= base + 4]
            stn_pages.sort(key=lambda r: r.get('page', 0))
            
            if len(stn_pages) < 2:
                continue
            
            for i, r in enumerate(stn_pages):
                cands = r.get('candidates') or []
                if not cands:
                    continue
                nums = [c.get('number') or c.get('candidate_no') for c in cands]
                nums = [n for n in nums if n is not None]
                
                if nums:
                    min_n = min(int(n) if str(n).isdigit() else 999 for n in nums)
                    max_n = max(int(n) if str(n).isdigit() else 0 for n in nums)
                    
                    if checked < 15:
                        print(f"  {slug} p={r.get('page')} stn={stn_idx+1} cands={len(cands)} nums=[{min_n}..{max_n}] ({len(nums)} nums)")
                    
                    if i > 0 and min_n <= 2:
                        renumbered += 1
                    elif i > 0 and min_n > 5:
                        continuous += 1
                    checked += 1
        
        if checked >= 50:
            break
    
    print(f"\n  {slug}: checked={checked} renumbered_pages={renumbered} continuous_pages={continuous}")
    print()
