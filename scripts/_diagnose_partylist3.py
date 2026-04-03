#!/usr/bin/env python3
"""Find where the missing party list pages are."""
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

# Pick a specific file to trace ALL pages
target_file = None
for slug, records in sources.items():
    for r in records:
        f = r.get('file', '')
        if 'ต.ห้วยบง-บัญชีรายชื่อ-หน่วยที่ 1-14' in f:
            target_file = f
            break
    if target_file:
        break

if target_file:
    print(f"=== ALL pages for: ...{target_file[-60:]} ===")
    for slug, records in sources.items():
        all_pages = [r for r in records if r.get('file') == target_file]
        all_pages.sort(key=lambda r: r.get('page', 0))
        
        if all_pages:
            tp = all_pages[0].get('total_pages', '?')
            print(f"  Source: {slug}, total_pages={tp}, records={len(all_pages)}")
            
            # Show ALL pages
            seen_pages = set()
            for r in all_pages:
                p = r.get('page', 0)
                seen_pages.add(p)
                nc = len(r.get('candidates', []))
                back = r.get('is_back_page', False)
                stn = r.get('station_no') or r.get('ocr_station_no') or '?'
                vt = r.get('vote_type', '?')
                calc_stn = (p - 1) // 4 + 1 if tp and int(tp) > 4 else '?'
                print(f"    p={p:2d} back={back} stn_ocr={stn} stn_calc={calc_stn} cands={nc:2d} vt={vt}")
            
            # Which pages are missing?
            if isinstance(tp, int):
                all_expected = set(range(1, tp + 1))
                missing = sorted(all_expected - seen_pages)
                print(f"\n    Missing pages: {missing[:30]}")
                print(f"    Total missing: {len(missing)} / {tp}")
                
                # Back pages
                back_pages = [r.get('page') for r in all_pages if r.get('is_back_page')]
                print(f"    Back pages: {sorted(back_pages)}")
                
                # Front pages
                front_pages = [r.get('page') for r in all_pages if not r.get('is_back_page')]
                print(f"    Front pages: {sorted(front_pages)}")
                
                # Expected data pages per station (not back)
                # For บัญชีรายชื่อ: 4pp/stn, pages 1-3 are data, page 4 is back
                expected_front = []
                for stn in range(1, tp // 4 + 1):
                    base = (stn - 1) * 4
                    expected_front.extend([base + 1, base + 2, base + 3])
                missing_front = sorted(set(expected_front) - set(front_pages))
                print(f"    Expected front pages: {expected_front[:30]}...")
                print(f"    Missing front pages: {missing_front[:30]}")
                print(f"    Total missing front: {len(missing_front)}")

# Now check overall: how many front pages are missing across all files?
print("\n\n=== OVERALL: missing front pages for บัญชีรายชื่อ ===")
for slug, records in sources.items():
    # Group by file
    by_file = defaultdict(list)
    for r in records:
        if 'บัญชีรายชื่อ' in (r.get('vote_type') or r.get('file') or ''):
            by_file[r.get('file', '')].append(r)
    
    total_missing = 0
    total_expected = 0
    files_with_missing = 0
    
    for f, recs in by_file.items():
        tp = max((r.get('total_pages') or 0) for r in recs)
        if not tp or tp <= 4:
            continue
        
        front_pages = set(r.get('page') for r in recs if not r.get('is_back_page'))
        
        # Expected front pages (3 per station)
        n_stations = tp // 4
        expected = set()
        for stn_idx in range(n_stations):
            base = stn_idx * 4
            expected.update([base + 1, base + 2, base + 3])
        
        missing = expected - front_pages
        if missing:
            files_with_missing += 1
            total_missing += len(missing)
        total_expected += len(expected)
    
    print(f"  {slug}: {total_missing} missing front pages / {total_expected} expected ({files_with_missing} files)")
