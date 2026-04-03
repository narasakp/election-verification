#!/usr/bin/env python3
"""Diagnose remaining n!=57 cases after even-page OCR."""
import json, os, sys
from collections import Counter, defaultdict

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

# Analyze n=23, n=34, n=47 separately
for target_n, label in [(23, 'n=23 (1 page?)'), (34, 'n=34 (2 pages?)'), (47, 'n=47 (2 pages?)')]:
    items = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ'
             and len(r.get('candidates', [])) == target_n]
    if not items:
        continue
    
    print(f"\n{'='*60}")
    print(f"=== {label}: {len(items)} items ===")
    
    consol = sum(1 for r in items if r.get('_consolidated'))
    print(f"  Consolidated: {consol}, Not: {len(items)-consol}")
    
    prov = Counter(r.get('province') for r in items)
    print(f"  Province: {dict(prov)}")
    
    # Sample 3: trace source pages
    for sample in items[:3]:
        f = sample.get('file', '')
        stn = sample.get('ocr_station_no') or sample.get('station_no') or '?'
        tp = sample.get('total_pages')
        merged = sample.get('_merged_pages')
        print(f"\n  Sample: stn={stn} p={sample.get('page')}/{tp} merged={merged}")
        print(f"    file=...{f[-65:]}")
        
        # Find source records for this file+station
        for slug, records in sources.items():
            matching = [r for r in records if r.get('file') == f and not r.get('is_back_page')]
            if not matching:
                continue
            
            # Apply station calc
            by_calc_stn = defaultdict(list)
            for r in matching:
                pg = r.get('page', 0)
                if tp and isinstance(tp, (int, float)) and int(tp) > 4:
                    calc = (int(pg) - 1) // 4 + 1
                    mx = int(tp) // 4
                    calc = min(calc, max(mx, 1))
                else:
                    calc = str(r.get('station_no') or r.get('ocr_station_no') or '?')
                by_calc_stn[str(calc)].append(r)
            
            stn_recs = by_calc_stn.get(str(stn), [])
            stn_recs.sort(key=lambda r: r.get('page', 0))
            
            print(f"    Source ({slug}): stn={stn} → {len(stn_recs)} pages")
            for r in stn_recs:
                nc = len(r.get('candidates', []))
                print(f"      p={r.get('page')} cands={nc} back={r.get('is_back_page',False)}")
            
            # Check gaps
            if len(stn_recs) >= 2:
                pages = [r.get('page', 0) for r in stn_recs]
                gaps = [pages[i+1]-pages[i] for i in range(len(pages)-1)]
                print(f"      Pages={pages} Gaps={gaps}")

# Check: how many n!=57 items have _merged_pages?
print(f"\n\n{'='*60}")
print("=== Overall: n!=57 consolidation status ===")
bad = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ' and len(r.get('candidates',[])) != 57]
print(f"Total n!=57: {len(bad)}")
consol = sum(1 for r in bad if r.get('_consolidated'))
not_consol = len(bad) - consol
print(f"  Consolidated but still wrong: {consol}")
print(f"  Never consolidated: {not_consol}")

merged_pages_dist = Counter(len(r.get('_merged_pages',[])) for r in bad if r.get('_consolidated'))
print(f"  Merged page counts: {dict(sorted(merged_pages_dist.items()))}")

# Pages per station in source for n!=57
print(f"\n  Source pages per station for never-consolidated items:")
no_consol_items = [r for r in bad if not r.get('_consolidated')][:10]
for item in no_consol_items:
    f = item.get('file', '')
    stn = str(item.get('ocr_station_no') or item.get('station_no') or '?')
    tp = item.get('total_pages')
    nc = len(item.get('candidates', []))
    
    for slug, records in sources.items():
        matching = [r for r in records if r.get('file') == f and not r.get('is_back_page')]
        if matching:
            by_stn = defaultdict(list)
            for r in matching:
                pg = r.get('page', 0)
                if tp and isinstance(tp, (int,float)) and int(tp) > 4:
                    calc = min((int(pg)-1)//4+1, max(int(tp)//4,1))
                else:
                    calc = str(r.get('station_no') or r.get('ocr_station_no') or '?')
                by_stn[str(calc)].append(r)
            
            src_pages = len(by_stn.get(stn, []))
            print(f"    stn={stn} nc={nc} src_pages={src_pages} tp={tp} ...{f[-50:]}")
            break
