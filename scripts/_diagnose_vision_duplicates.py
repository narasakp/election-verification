#!/usr/bin/env python3
"""Check if vision-only multi-station items are duplicates of existing multimodel items."""
import json, os, sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
review = json.load(open(REVIEW_PATH, encoding='utf-8'))

# Group by (province, constituency, vote_type, station_no) 
station_items = defaultdict(list)
for r in review:
    prov = r.get('province', '')
    cons = r.get('constituency', '')
    vt = r.get('vote_type', '')
    stn = r.get('ocr_station_no') or r.get('station_no') or ''
    key = (prov, str(cons), vt, str(stn))
    station_items[key].append(r)

# Find vision-only multi-station items
vision_multi = [r for r in review 
                if r.get('_source_type') == 'vision'
                and (r.get('total_pages') or 0) > 4]

print(f"=== Vision multi-station items: {len(vision_multi)} ===")

# For each, check if a multimodel item exists for the same station
has_multimodel = 0
no_multimodel = 0
no_station = 0

for r in vision_multi:
    prov = r.get('province', '')
    cons = str(r.get('constituency', ''))
    vt = r.get('vote_type', '')
    stn = str(r.get('ocr_station_no') or r.get('station_no') or '')
    
    if not stn:
        no_station += 1
        continue
    
    key = (prov, cons, vt, stn)
    siblings = station_items.get(key, [])
    multimodel_sibs = [s for s in siblings if s.get('_source_type') != 'vision' and s.get('id') != r.get('id')]
    
    if multimodel_sibs:
        has_multimodel += 1
    else:
        no_multimodel += 1

print(f"  With multimodel equivalent: {has_multimodel} (DUPLICATES)")
print(f"  Without multimodel: {no_multimodel} (UNIQUE)")
print(f"  No station_no: {no_station}")

# Show unique files by province
unique_files = set()
for r in vision_multi:
    prov = r.get('province', '')
    cons = str(r.get('constituency', ''))
    vt = r.get('vote_type', '')
    stn = str(r.get('ocr_station_no') or r.get('station_no') or '')
    key = (prov, cons, vt, stn)
    siblings = station_items.get(key, [])
    multimodel_sibs = [s for s in siblings if s.get('_source_type') != 'vision' and s.get('id') != r.get('id')]
    if not multimodel_sibs:
        unique_files.add(r.get('file', ''))

if unique_files:
    print(f"\n=== Unique vision files (no multimodel equivalent): {len(unique_files)} ===")
    for f in sorted(unique_files)[:20]:
        print(f"  {f[-80:]}")

# Check station coverage: for chaiyaphum zone 1, show all items
print(f"\n=== ชัยภูมิ zone 1 แบ่งเขต station 1: all items ===")
for r in review:
    if (r.get('province') == 'ชัยภูมิ' and str(r.get('constituency')) == '1' 
        and r.get('vote_type') == 'แบ่งเขต'
        and str(r.get('ocr_station_no') or r.get('station_no') or '') == '1'):
        src = r.get('_source_type', '?')
        cands = len(r.get('candidates', []))
        f = r.get('file', '')[-60:]
        print(f"  id={r['id']} src={src} cands={cands} file=...{f}")

# Overall: how many vision items in total?
all_vision = [r for r in review if r.get('_source_type') == 'vision']
print(f"\n=== Vision items total: {len(all_vision)} ===")
print(f"  Multi-station (tp>4): {len(vision_multi)}")
print(f"  Single-station (tp<=4): {len(all_vision) - len(vision_multi)}")
