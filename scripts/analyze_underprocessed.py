# -*- coding: utf-8 -*-
"""Analyze all OCR data to find under-processed multi-station PDFs."""
import json, os, glob, re
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Scan all OCR result files
files = sorted(glob.glob(os.path.join(DATA_DIR, 'ocr_multimodel_*.json')))
files += sorted(glob.glob(os.path.join(DATA_DIR, 'ocr_vision_*.json')))

# Track per-file info
file_info = {}  # (slug, filepath) -> {pages_ocrd, total_pages, stations_from_name}

for jf in files:
    slug = os.path.basename(jf).replace('ocr_multimodel_', '').replace('ocr_vision_', '').replace('.json', '')
    with open(jf, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    for item in items:
        fp = item.get('file', '')
        key = (slug, fp)
        if key not in file_info:
            file_info[key] = {
                'total_pages': item.get('total_pages', 1),
                'pages_ocrd': set(),
                'stations_found': set(),
                'slug': slug,
            }
        file_info[key]['pages_ocrd'].add(item.get('page', 0))
        stn = item.get('station_no')
        if stn is not None:
            file_info[key]['stations_found'].add(stn)

# Extract expected station count from filename (e.g., "หน่วยที่ 1-18" -> 18)
def extract_station_range(filepath):
    m = re.search(r'หน่วยที่\s*(\d+)-(\d+)', filepath)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

# Analyze
print("=" * 100)
print("UNDER-PROCESSED MULTI-STATION PDFs")
print("=" * 100)

total_missing_pages = 0
total_missing_stations = 0
under_processed = []

for (slug, fp), info in sorted(file_info.items()):
    tp = info['total_pages'] or 1
    ocrd = len(info['pages_ocrd'])
    
    start, end = extract_station_range(fp)
    expected_stations = (end - start + 1) if start and end else None
    expected_pages = expected_stations * 2 if expected_stations else tp
    
    if tp > 4 and ocrd < tp:  # Multi-page PDF not fully processed
        missing = tp - ocrd
        total_missing_pages += missing
        
        stations_found = len(info['stations_found'])
        stations_missing = (expected_stations - stations_found) if expected_stations else 0
        total_missing_stations += max(0, stations_missing)
        
        under_processed.append({
            'slug': slug,
            'file': fp,
            'total_pages': tp,
            'pages_ocrd': ocrd,
            'missing_pages': missing,
            'expected_stations': expected_stations,
            'stations_found': stations_found,
        })
        
        print(f"\n  [{slug}] {fp}")
        print(f"    Total pages: {tp}, OCR'd: {ocrd}, Missing: {missing}")
        if expected_stations:
            print(f"    Expected stations: {expected_stations}, Found: {stations_found}, Missing: {stations_missing}")

# Also check PDFs with total_pages > ocrd even if not "multi-station" name
print(f"\n{'=' * 100}")
print(f"SUMMARY")
print(f"{'=' * 100}")
print(f"Under-processed PDFs: {len(under_processed)}")
print(f"Total missing pages: {total_missing_pages}")
print(f"Total missing stations: {total_missing_stations}")

# Group by province
by_province = defaultdict(list)
for up in under_processed:
    by_province[up['slug']].append(up)

print(f"\nBy province:")
for slug, items in sorted(by_province.items()):
    missing = sum(x['missing_pages'] for x in items)
    print(f"  {slug}: {len(items)} files, {missing} missing pages")

# Also count ALL files with total_pages > 2
print(f"\n--- All PDFs by page count ---")
page_dist = defaultdict(int)
for (slug, fp), info in file_info.items():
    tp = info['total_pages'] or 1
    if tp <= 2:
        page_dist['1-2'] += 1
    elif tp <= 4:
        page_dist['3-4'] += 1
    elif tp <= 10:
        page_dist['5-10'] += 1
    elif tp <= 20:
        page_dist['11-20'] += 1
    elif tp <= 40:
        page_dist['21-40'] += 1
    else:
        page_dist['41+'] += 1

for k in ['1-2', '3-4', '5-10', '11-20', '21-40', '41+']:
    print(f"  {k} pages: {page_dist.get(k, 0)} PDFs")
