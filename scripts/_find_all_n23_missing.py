#!/usr/bin/env python3
"""Find ALL missing pages for n=23 party list items — general approach."""
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

# Build source lookup
src_by_file = defaultdict(list)
slug_by_file = {}
for slug, records in sources.items():
    for r in records:
        f = r.get('file', '')
        src_by_file[f].append(r)
        slug_by_file[f] = slug

# Check 6pp flags in review data
n23_all = [r for r in review 
           if r.get('vote_type') == 'บัญชีรายชื่อ' 
           and len(r.get('candidates', [])) == 23]
print(f"Total n=23: {len(n23_all)}")
print(f"  _6pp_layout=True: {sum(1 for r in n23_all if r.get('_6pp_layout'))}")
print(f"  _consolidated: {sum(1 for r in n23_all if r.get('_consolidated'))}")

# For each n=23 item, find the file and check what pages are missing
tasks = []
seen = set()

for item in n23_all:
    f = item.get('file', '')
    tp = item.get('total_pages') or 0
    stn = str(item.get('ocr_station_no') or item.get('station_no') or '')
    pg = item.get('page')
    is_6pp = item.get('_6pp_layout', False)
    
    if not f or not tp or not stn or not stn.isdigit():
        continue
    
    stn_int = int(stn)
    pps = 6 if is_6pp else 4
    base = (stn_int - 1) * pps  # 0-indexed
    
    # All pages for this station
    station_pages = list(range(base + 1, min(base + pps + 1, tp + 1)))
    
    # Existing pages in source for this file
    existing = set(r.get('page') for r in src_by_file.get(f, []))
    
    # Missing pages (excluding known back-page positions)
    for mpg in station_pages:
        if mpg in existing:
            continue
        key = (f, mpg)
        if key in seen:
            continue
        seen.add(key)
        tasks.append({
            'file': f,
            'page': mpg,
            'total_pages': tp,
            'station': stn_int,
            'slug': slug_by_file.get(f, '?'),
            'is_6pp': is_6pp,
        })

print(f"\nTotal missing pages: {len(tasks)}")
by_slug = Counter(t['slug'] for t in tasks)
print(f"  By province: {dict(by_slug)}")
by_6pp = Counter(t['is_6pp'] for t in tasks)
print(f"  6pp: {by_6pp.get(True, 0)}, 4pp: {by_6pp.get(False, 0)}")

# Check: which positions are missing?
pos_counts = Counter()
for t in tasks:
    pps = 6 if t['is_6pp'] else 4
    pos = (t['page'] - 1) % pps + 1
    pos_counts[f"pos{pos}({'6pp' if t['is_6pp'] else '4pp'})"] += 1
print(f"  Position distribution: {dict(sorted(pos_counts.items()))}")

# Unique files
files = set(t['file'] for t in tasks)
print(f"  Unique files: {len(files)}")

# Save
out_path = os.path.join(DATA_DIR, '_n23_all_missing_tasks.json')
with open(out_path, 'w', encoding='utf-8') as fp:
    json.dump(tasks, fp, ensure_ascii=False, indent=2)
print(f"\nSaved {len(tasks)} tasks to {out_path}")

# Sample
print("\nSamples:")
for t in tasks[:8]:
    pos = (t['page'] - 1) % (6 if t['is_6pp'] else 4) + 1
    print(f"  {t['slug']} p={t['page']}/{t['total_pages']} stn={t['station']} pos={pos} {'6pp' if t['is_6pp'] else '4pp'} ...{t['file'][-50:]}")
