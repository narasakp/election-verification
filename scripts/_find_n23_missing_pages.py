#!/usr/bin/env python3
"""Find missing pages for n=23 party list items that need OCR."""
import json, os, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(ROOT, 'data')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')

review = json.load(open(REVIEW_PATH, encoding='utf-8'))
sources = {}
drive_indices = {}
for slug in ['chaiyaphum', 'tak', 'phetchabun']:
    path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    if os.path.exists(path):
        sources[slug] = json.load(open(path, encoding='utf-8'))
    di_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    if os.path.exists(di_path):
        drive_indices[slug] = json.load(open(di_path, encoding='utf-8'))

# Build source lookup by file
src_by_file = {}
for slug, records in sources.items():
    for r in records:
        f = r.get('file', '')
        if f not in src_by_file:
            src_by_file[f] = {'slug': slug, 'records': []}
        src_by_file[f]['records'].append(r)

# Build drive index lookup
drive_by_file = {}
for slug, index in drive_indices.items():
    for entry in index:
        f = entry.get('file', '')
        drive_by_file[f] = entry

# Find n=23 party list items
n23 = [r for r in review 
       if r.get('vote_type') == 'บัญชีรายชื่อ' 
       and len(r.get('candidates', [])) == 23
       and not r.get('_consolidated')]  # only non-consolidated (single page)

print(f"n=23 non-consolidated items: {len(n23)}")

# For each, find what pages are missing
tasks = []  # (file, page, slug, drive_id, total_pages)
files_analyzed = set()

for item in n23:
    f = item.get('file', '')
    tp = item.get('total_pages')
    stn = item.get('ocr_station_no') or item.get('station_no')
    pg = item.get('page')
    is_6pp = item.get('_6pp_layout', False)
    
    if not f or not tp or not stn:
        continue
    
    src_info = src_by_file.get(f)
    if not src_info:
        continue
    
    slug = src_info['slug']
    existing_pages = set(r.get('page') for r in src_info['records'])
    
    # Determine pages per station
    pps = 6 if is_6pp else 4
    stn_int = int(stn) if str(stn).isdigit() else 0
    if stn_int <= 0:
        continue
    
    base = (stn_int - 1) * pps  # 0-indexed start
    
    # Expected data pages for this station (excluding back page)
    if is_6pp:
        # Positions 3,4,5 are party list in 6pp layout
        expected_data = [base + 3, base + 4, base + 5]
    else:
        # Positions 1,2,3 are data in 4pp layout
        expected_data = [base + 1, base + 2, base + 3]
    
    # Find missing pages
    for epg in expected_data:
        if epg > 0 and epg <= tp and epg not in existing_pages:
            # Get drive file ID
            drive_entry = drive_by_file.get(f)
            drive_id = drive_entry.get('id', '') if drive_entry else ''
            
            task_key = (f, epg)
            if task_key not in files_analyzed:
                files_analyzed.add(task_key)
                tasks.append({
                    'file': f,
                    'page': epg,
                    'slug': slug,
                    'drive_id': drive_id,
                    'total_pages': tp,
                    'station': stn_int,
                })

# Also check n=23 CONSOLIDATED items (merged but still only 23 cands)
n23_c = [r for r in review 
         if r.get('vote_type') == 'บัญชีรายชื่อ' 
         and len(r.get('candidates', [])) == 23
         and r.get('_consolidated')]

print(f"n=23 consolidated items: {len(n23_c)}")

for item in n23_c:
    f = item.get('file', '')
    tp = item.get('total_pages')
    stn = item.get('ocr_station_no') or item.get('station_no')
    merged = item.get('_merged_pages', [])
    is_6pp = item.get('_6pp_layout', False)
    
    if not f or not tp or not stn:
        continue
    
    src_info = src_by_file.get(f)
    if not src_info:
        continue
    
    slug = src_info['slug']
    existing_pages = set(r.get('page') for r in src_info['records'])
    
    pps = 6 if is_6pp else 4
    stn_int = int(stn) if str(stn).isdigit() else 0
    if stn_int <= 0:
        continue
    
    base = (stn_int - 1) * pps
    if is_6pp:
        expected_data = [base + 3, base + 4, base + 5]
    else:
        expected_data = [base + 1, base + 2, base + 3]
    
    for epg in expected_data:
        if epg > 0 and epg <= tp and epg not in existing_pages:
            drive_entry = drive_by_file.get(f)
            drive_id = drive_entry.get('id', '') if drive_entry else ''
            task_key = (f, epg)
            if task_key not in files_analyzed:
                files_analyzed.add(task_key)
                tasks.append({
                    'file': f,
                    'page': epg,
                    'slug': slug,
                    'drive_id': drive_id,
                    'total_pages': tp,
                    'station': stn_int,
                })

print(f"\nTotal missing pages to OCR: {len(tasks)}")
by_slug = Counter(t['slug'] for t in tasks)
print(f"By province: {dict(by_slug)}")

no_drive = sum(1 for t in tasks if not t['drive_id'])
print(f"Without drive_id: {no_drive}")

# Save tasks for dispatch
out_path = os.path.join(DATA_DIR, '_n23_missing_tasks.json')
with open(out_path, 'w', encoding='utf-8') as fp:
    json.dump(tasks, fp, ensure_ascii=False, indent=2)
print(f"\nSaved tasks to {out_path}")

# Show sample
for t in tasks[:5]:
    print(f"  {t['slug']} p={t['page']}/{t['total_pages']} stn={t['station']} ...{t['file'][-50:]}")
