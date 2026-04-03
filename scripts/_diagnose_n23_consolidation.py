#!/usr/bin/env python3
"""Diagnose why n=23 items aren't consolidating despite pages existing."""
import json, os, sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')

review = json.load(open(REVIEW_PATH, encoding='utf-8'))
sources = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))

src_by_file = defaultdict(list)
for slug, records in sources.items():
    for r in records:
        src_by_file[r.get('file', '')].append(r)

# Find n=23 non-consolidated items
n23_nc = [r for r in review 
          if r.get('vote_type') == 'บัญชีรายชื่อ' 
          and len(r.get('candidates', [])) == 23
          and not r.get('_consolidated')]

print(f"n=23 non-consolidated: {len(n23_nc)}")

# Categorize reasons
reasons = defaultdict(int)
samples = defaultdict(list)

for item in n23_nc:
    f = item.get('file', '')
    tp = item.get('total_pages') or 0
    stn = item.get('ocr_station_no') or item.get('station_no')
    pg = item.get('page')
    is_6pp = item.get('_6pp_layout', False)
    
    src_recs = src_by_file.get(f, [])
    if not src_recs:
        reasons['no_source'] += 1
        continue
    
    # Find all party list pages for this station
    pps = 6 if is_6pp else 4
    stn_int = int(stn) if stn and str(stn).isdigit() else 0
    
    # Get all party list pages in source for same file and station
    same_stn_pl = []
    for r in src_recs:
        vt = r.get('vote_type') or ''
        if 'บัญชีรายชื่อ' not in vt:
            continue
        if r.get('is_back_page'):
            continue
        # Calculate station_no using same formula as prepare_review_data
        r_pg = r.get('page', 0)
        if pps and tp > 4:
            r_stn = (r_pg - 1) // pps + 1
            r_stn = min(r_stn, max(tp // pps, 1))
        else:
            r_stn = int(r.get('station_no') or r.get('ocr_station_no') or 0)
        
        if r_stn == stn_int:
            nc = len(r.get('candidates') or [])
            nums = sorted([c.get('number') for c in (r.get('candidates') or []) if c.get('number') is not None])
            same_stn_pl.append({
                'page': r_pg,
                'cands': nc,
                'nums_range': f"{min(nums)}-{max(nums)}" if nums else "-",
                'calc_stn': r_stn,
            })
    
    same_stn_pl.sort(key=lambda x: x['page'])
    
    if len(same_stn_pl) <= 1:
        reasons['only_1_page_in_source'] += 1
        if len(samples['only_1_page_in_source']) < 3:
            samples['only_1_page_in_source'].append({
                'file': f[-55:], 'stn': stn, 'pg': pg, 'tp': tp,
                'src_pages': same_stn_pl,
            })
    elif len(same_stn_pl) == 2:
        # 2 pages exist but not consolidated — why?
        pages = [p['page'] for p in same_stn_pl]
        gap = max(pages) - min(pages)
        cands_total = sum(p['cands'] for p in same_stn_pl)
        if gap > 2:
            reasons['gap_too_large'] += 1
            if len(samples['gap_too_large']) < 3:
                samples['gap_too_large'].append({
                    'file': f[-55:], 'stn': stn, 'pg': pg, 'tp': tp,
                    'src_pages': same_stn_pl, 'gap': gap,
                })
        else:
            reasons['2_pages_but_not_merged'] += 1
            if len(samples['2_pages_but_not_merged']) < 3:
                samples['2_pages_but_not_merged'].append({
                    'file': f[-55:], 'stn': stn, 'pg': pg, 'tp': tp,
                    'src_pages': same_stn_pl,
                })
    else:
        # 3+ pages exist — should have consolidated
        cands_total = sum(p['cands'] for p in same_stn_pl)
        pages = [p['page'] for p in same_stn_pl]
        max_gap = max(pages[i+1] - pages[i] for i in range(len(pages)-1)) if len(pages) > 1 else 0
        reasons[f'3+_pages_gap={max_gap}'] += 1
        if len(samples[f'3+_pages_gap={max_gap}']) < 2:
            samples[f'3+_pages_gap={max_gap}'].append({
                'file': f[-55:], 'stn': stn, 'pg': pg, 'tp': tp,
                'src_pages': same_stn_pl,
            })

print(f"\nReasons for non-consolidation:")
for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"  {reason}: {count}")
    for s in samples.get(reason, []):
        print(f"    file=...{s['file']} stn={s['stn']} pg={s['pg']} tp={s['tp']}")
        for sp in s['src_pages']:
            print(f"      source p={sp['page']} cands={sp['cands']} nums={sp['nums_range']}")
