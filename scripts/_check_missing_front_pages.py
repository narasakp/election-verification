# -*- coding: utf-8 -*-
"""
Count EXACTLY how many front (data) pages are missing per province.
Front pages = odd pages (1, 3, 5, ...) for multi-station PDFs.
"""
import json, os
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

PROVINCES = ['chaiyaphum', 'tak', 'phetchabun']

for slug in PROVINCES:
    ocr_path = os.path.join(DATA, f'ocr_multimodel_{slug}.json')
    ocr_data = json.load(open(ocr_path, 'r', encoding='utf-8'))

    # Group by file
    by_file = defaultdict(list)
    for r in ocr_data:
        by_file[r.get('file', '')].append(r)

    total_front_expected = 0
    total_front_done = 0
    total_front_missing = 0
    missing_detail = []

    for fname, records in by_file.items():
        tp = max(r.get('total_pages', 0) for r in records)
        done_pages = set(r.get('page', 0) for r in records)

        # Front pages = odd: 1, 3, 5, ...
        front_pages = set(range(1, tp + 1, 2))
        front_done = front_pages & done_pages
        front_missing = front_pages - done_pages

        total_front_expected += len(front_pages)
        total_front_done += len(front_done)
        total_front_missing += len(front_missing)

        if front_missing:
            missing_detail.append({
                'file': fname,
                'total_pages': tp,
                'front_expected': len(front_pages),
                'front_done': len(front_done),
                'front_missing': sorted(front_missing),
            })

    pct = (total_front_done / total_front_expected * 100) if total_front_expected else 0

    print(f"\n{'='*60}")
    print(f"  {slug.upper()}")
    print(f"{'='*60}")
    print(f"  Total files:          {len(by_file):,}")
    print(f"  Front pages expected: {total_front_expected:,}")
    print(f"  Front pages done:     {total_front_done:,}")
    print(f"  Front pages MISSING:  {total_front_missing:,}")
    print(f"  Completion:           {pct:.1f}%")
    print(f"  Files with missing:   {len(missing_detail):,}")

    if missing_detail:
        # Breakdown: compilation vs station-level
        comp_missing = [m for m in missing_detail if m['total_pages'] > 6]
        station_missing = [m for m in missing_detail if m['total_pages'] <= 6]
        comp_pages = sum(len(m['front_missing']) for m in comp_missing)
        station_pages = sum(len(m['front_missing']) for m in station_missing)

        print(f"\n  Compilation files (tp>6):  {len(comp_missing):,} files, {comp_pages:,} missing pages")
        print(f"  Station files (tp<=6):     {len(station_missing):,} files, {station_pages:,} missing pages")

        # Show first 10 missing
        print(f"\n  Sample missing (station-level):")
        for m in station_missing[:8]:
            print(f"    {m['file']}")
            print(f"      tp={m['total_pages']} done={m['front_done']} missing={m['front_missing']}")

        print(f"\n  Sample missing (compilation):")
        for m in comp_missing[:5]:
            print(f"    {m['file']}")
            print(f"      tp={m['total_pages']} done={m['front_done']}/{m['front_expected']} missing_count={len(m['front_missing'])}")

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
