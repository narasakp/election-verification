#!/usr/bin/env python3
"""Deep diagnosis of remaining n!=57 party list items."""
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

bad = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ' and len(r.get('candidates', [])) != 57]
print(f"Total n!=57: {len(bad)}")
print(f"  n distribution:")
dist = Counter(len(r.get('candidates', [])) for r in bad)
for n, c in sorted(dist.items(), key=lambda x: -x[1])[:20]:
    print(f"    n={n:3d}: {c}")

# === GROUP 1: n=23 (not consolidated) ===
print(f"\n{'='*60}")
print("=== GROUP 1: n=23 not-consolidated ===")
n23_nc = [r for r in bad if len(r.get('candidates', [])) == 23 and not r.get('_consolidated')]
n23_c = [r for r in bad if len(r.get('candidates', [])) == 23 and r.get('_consolidated')]
print(f"  Not consolidated: {len(n23_nc)}")
print(f"  Consolidated: {len(n23_c)}")

# Check: are these from combined files?
combined_files = 0
pure_party_files = 0
for r in n23_nc:
    f = r.get('file', '')
    if 'แบ่งเขต' in f and 'บัญชีรายชื่อ' in f:
        combined_files += 1
    elif 'บัญชีรายชื่อ' in f:
        pure_party_files += 1
print(f"  Combined แบ่งเขต/บัญชีรายชื่อ files: {combined_files}")
print(f"  Pure บัญชีรายชื่อ files: {pure_party_files}")

# For combined files: check the actual page layout
print(f"\n  === Combined file layout analysis ===")
combined_samples = [r for r in n23_nc if 'แบ่งเขต' in r.get('file', '')][:5]
for sample in combined_samples:
    f = sample.get('file', '')
    tp = sample.get('total_pages')
    stn = sample.get('ocr_station_no') or sample.get('station_no')
    
    # Find ALL source records for this file
    for slug, records in sources.items():
        all_recs = [r for r in records if r.get('file') == f]
        if not all_recs:
            continue
        all_recs.sort(key=lambda r: r.get('page', 0))
        
        # Analyze layout: which pages are แบ่งเขต vs บัญชีรายชื่อ
        print(f"\n  File: ...{f[-65:]}")
        print(f"  total_pages={tp}, source_records={len(all_recs)}")
        
        # Group by vote_type
        by_vt = defaultdict(list)
        for r in all_recs:
            vt = r.get('vote_type', '?')
            by_vt[vt].append(r)
        
        for vt, recs in by_vt.items():
            pages = sorted(r.get('page', 0) for r in recs)
            print(f"    {vt}: {len(recs)} pages, range p={min(pages)}-{max(pages)}")
        
        # Show party list pages
        pl_recs = [r for r in all_recs if 'บัญชีรายชื่อ' in (r.get('vote_type') or '')
                   and not r.get('is_back_page')]
        if pl_recs:
            print(f"    Party list front pages:")
            for r in pl_recs[:15]:
                nc = len(r.get('candidates', []))
                stn_ocr = r.get('station_no') or r.get('ocr_station_no') or '?'
                print(f"      p={r.get('page'):3d} stn_ocr={stn_ocr} cands={nc}")
        break

# === GROUP 2: n<30 ===
print(f"\n{'='*60}")
print("=== GROUP 2: n<30 (excluding n=23) ===")
nlt30 = [r for r in bad if len(r.get('candidates', [])) < 30 and len(r.get('candidates', [])) != 23]
print(f"  Total: {len(nlt30)}")
nlt30_dist = Counter(len(r.get('candidates', [])) for r in nlt30)
print(f"  Distribution: {dict(sorted(nlt30_dist.items()))}")
consol = sum(1 for r in nlt30 if r.get('_consolidated'))
print(f"  Consolidated: {consol}, Not: {len(nlt30)-consol}")

# Check source coverage for n<30 items
print(f"\n  Source page coverage for n<30:")
for sample in nlt30[:8]:
    f = sample.get('file', '')
    tp = sample.get('total_pages')
    nc = len(sample.get('candidates', []))
    stn = sample.get('ocr_station_no') or sample.get('station_no')
    merged = sample.get('_merged_pages')
    
    for slug, records in sources.items():
        matching = [r for r in records if r.get('file') == f and not r.get('is_back_page')
                    and 'บัญชีรายชื่อ' in (r.get('vote_type') or '')]
        if not matching:
            continue
        
        # How many pages per station?
        by_calc_stn = defaultdict(list)
        for r in matching:
            pg = r.get('page', 0)
            if tp and int(tp) > 4:
                calc = min((int(pg)-1)//4+1, max(int(tp)//4,1))
            else:
                calc = str(r.get('station_no') or r.get('ocr_station_no') or '?')
            by_calc_stn[str(calc)].append(r)
        
        stn_recs = by_calc_stn.get(str(stn), [])
        total_cands = sum(len(r.get('candidates',[])) for r in stn_recs)
        print(f"    stn={stn} nc={nc} src_pages={len(stn_recs)} total_src_cands={total_cands} merged={merged} ...{f[-50:]}")
        break

# === What about n>57? ===
print(f"\n{'='*60}")
print("=== GROUP 3: n>57 (over-merged?) ===")
ngt57 = [r for r in bad if len(r.get('candidates', [])) > 57]
print(f"  Total: {len(ngt57)}")
ngt57_dist = Counter(len(r.get('candidates', [])) for r in ngt57)
print(f"  Distribution: {dict(sorted(ngt57_dist.items()))}")
for sample in ngt57[:3]:
    nc = len(sample.get('candidates', []))
    merged = sample.get('_merged_pages')
    stn = sample.get('ocr_station_no') or sample.get('station_no')
    print(f"    stn={stn} nc={nc} merged={merged} ...{sample.get('file','')[-50:]}")
    # Check candidate number range
    nums = sorted([c.get('number') for c in sample.get('candidates',[]) if c.get('number') is not None])
    if nums:
        print(f"      nums: min={min(nums)} max={max(nums)} unique={len(set(nums))}")
