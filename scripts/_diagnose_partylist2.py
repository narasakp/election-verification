#!/usr/bin/env python3
"""Deep diagnosis: why consolidation fails for บัญชีรายชื่อ after station_no fix."""
import json, os, sys, re
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')

# Load source + review
sources = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))

review = json.load(open(REVIEW_PATH, encoding='utf-8'))

# Find n=23/24 items in review and trace back to source
print("=== n=23/24 items: why not consolidated to 57? ===")
n23_24 = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ'
          and len(r.get('candidates', [])) in (23, 24)]
print(f"Total: {len(n23_24)}")

# Sample 5 items - trace to source
for sample in n23_24[:5]:
    f = sample.get('file', '')
    stn = sample.get('ocr_station_no') or sample.get('station_no') or '?'
    tp = sample.get('total_pages')
    consol = sample.get('_consolidated', False)
    merged = sample.get('_merged_pages')
    print(f"\n  file=...{f[-60:]}  stn={stn} p={sample.get('page')}/{tp} cands={len(sample.get('candidates',[]))} consol={consol} merged={merged}")
    
    # Find ALL source records for this file
    for slug, records in sources.items():
        matching = [r for r in records if r.get('file') == f and not r.get('is_back_page')]
        if matching:
            # Apply page-position station_no
            for r in matching:
                pg = r.get('page', 0)
                if tp and int(tp) > 4:
                    calc_stn = (int(pg) - 1) // 4 + 1
                    max_stn = int(tp) // 4
                    calc_stn = min(calc_stn, max(max_stn, 1))
                else:
                    calc_stn = r.get('station_no') or r.get('ocr_station_no') or '?'
                r['_calc_stn'] = str(calc_stn)
            
            # Group by calculated station_no
            by_stn = defaultdict(list)
            for r in matching:
                by_stn[r['_calc_stn']].append(r)
            
            target_stn_recs = by_stn.get(str(stn), [])
            target_stn_recs.sort(key=lambda r: r.get('page', 0))
            
            print(f"    Source ({slug}): {len(matching)} front pages, stn={stn} has {len(target_stn_recs)} pages")
            for r in target_stn_recs:
                nc = len(r.get('candidates', []))
                print(f"      p={r.get('page')} ocr_stn={r.get('station_no') or r.get('ocr_station_no','?')} calc_stn={r['_calc_stn']} cands={nc}")
            
            # Check gaps
            if len(target_stn_recs) >= 2:
                pages = [r.get('page', 0) for r in target_stn_recs]
                gaps = [pages[i+1] - pages[i] for i in range(len(pages)-1)]
                print(f"      Pages: {pages}, Gaps: {gaps}")
                if any(g > 2 for g in gaps):
                    print(f"      ⚠️  GAP > 2 detected! Consolidation will split here!")

# Simulate consolidation with different gap thresholds
print("\n\n=== SIMULATION: consolidation with different max_gap ===")
for slug, records in sources.items():
    party = [r for r in records 
             if 'บัญชีรายชื่อ' in (r.get('vote_type') or r.get('file') or '')
             and not r.get('is_back_page')]
    
    # Assign page-position station_no
    for r in party:
        tp = r.get('total_pages')
        pg = r.get('page', 0)
        if tp and isinstance(tp, (int, float)) and int(tp) > 4:
            calc_stn = (int(pg) - 1) // 4 + 1
            max_stn = int(tp) // 4
            r['_calc_stn'] = str(min(calc_stn, max(max_stn, 1)))
        else:
            r['_calc_stn'] = str(r.get('station_no') or r.get('ocr_station_no') or 'none')
    
    # Group by (file, calc_stn, vote_type)
    groups = defaultdict(list)
    for r in party:
        key = (r.get('file',''), r['_calc_stn'])
        groups[key].append(r)
    
    for max_gap in [2, 3, 4, 6]:
        n57 = 0
        total_groups = 0
        for key, recs in groups.items():
            recs.sort(key=lambda r: r.get('page', 0))
            # Simulate merge with max_gap
            sub_groups = []
            current = [recs[0]]
            for i in range(1, len(recs)):
                prev_p = current[-1].get('page', 0)
                curr_p = recs[i].get('page', 0)
                if curr_p - prev_p <= max_gap and len(current) < 4:
                    current.append(recs[i])
                else:
                    sub_groups.append(current)
                    current = [recs[i]]
            sub_groups.append(current)
            
            for sub in sub_groups:
                total_groups += 1
                total_cands = sum(len(r.get('candidates', [])) for r in sub)
                if 50 <= total_cands <= 65:
                    n57 += 1
        
        print(f"  {slug} max_gap={max_gap}: {n57}/{total_groups} groups reach n≈57 ({n57*100/total_groups:.1f}%)")
