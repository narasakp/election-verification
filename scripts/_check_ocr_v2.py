# -*- coding: utf-8 -*-
"""
Accurate OCR completion check — compares Drive index (post-split) vs OCR records.
Does NOT rely on total_pages metadata (which comes from pre-split compilation PDFs).
"""
import json, os
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

PROVINCES = {
    'chaiyaphum': {'ocr': 'ocr_multimodel_chaiyaphum.json', 'drive': 'drive_index_chaiyaphum.json'},
    'tak':        {'ocr': 'ocr_multimodel_tak.json',        'drive': 'drive_index_tak.json'},
    'phetchabun': {'ocr': 'ocr_multimodel_phetchabun.json', 'drive': 'drive_index_phetchabun.json'},
}

for slug, files in PROVINCES.items():
    print(f"\n{'='*60}")
    print(f"  {slug.upper()}")
    print(f"{'='*60}")

    # --- Load Drive index ---
    drive_path = os.path.join(DATA, files['drive'])
    if not os.path.exists(drive_path):
        print(f"  Drive index NOT FOUND: {drive_path}")
        continue
    drive_idx = json.load(open(drive_path, 'r', encoding='utf-8'))
    drive_pdfs = [e for e in drive_idx if e.get('name', '').lower().endswith('.pdf')]
    print(f"  Drive PDFs:     {len(drive_pdfs):,}")
    
    # Show Drive entry structure
    if drive_pdfs:
        sample = drive_pdfs[0]
        print(f"  Entry keys:     {list(sample.keys())}")
    
    # Build file_label set from Drive
    def file_label(entry):
        p = entry.get('path', '')
        n = entry.get('name', '')
        return f"{p}/{n}" if p else n
    
    drive_labels = set(file_label(e) for e in drive_pdfs)
    print(f"  Unique labels:  {len(drive_labels):,}")

    # --- Load OCR results ---
    ocr_path = os.path.join(DATA, files['ocr'])
    if not os.path.exists(ocr_path):
        print(f"  OCR file NOT FOUND: {ocr_path}")
        continue
    ocr_data = json.load(open(ocr_path, 'r', encoding='utf-8'))
    ocr_files = set(r.get('file', '') for r in ocr_data)
    ocr_pages = set((r.get('file', ''), r.get('page', 0)) for r in ocr_data)
    print(f"  OCR records:    {len(ocr_data):,}")
    print(f"  OCR files:      {len(ocr_files):,}")
    
    # --- Check: which Drive PDFs have NO OCR records? ---
    # Match by filename (Drive label may differ slightly from OCR 'file' field)
    # Try matching by basename
    ocr_basenames = defaultdict(list)
    for r in ocr_data:
        f = r.get('file', '')
        basename = f.rsplit('/', 1)[-1] if '/' in f else f
        ocr_basenames[basename].append(r)
    
    drive_basenames = {}
    for e in drive_pdfs:
        bl = file_label(e)
        basename = bl.rsplit('/', 1)[-1] if '/' in bl else bl
        drive_basenames[basename] = bl
    
    # Files in Drive but no OCR
    missing_files = []
    for basename, label in drive_basenames.items():
        if basename not in ocr_basenames:
            missing_files.append(label)
    
    print(f"\n  Drive files WITHOUT any OCR: {len(missing_files):,}")
    if missing_files:
        for f in missing_files[:10]:
            print(f"    - {f}")
        if len(missing_files) > 10:
            print(f"    ... and {len(missing_files) - 10} more")
    
    # --- Check: OCR records with is_back_page ---
    back_pages = sum(1 for r in ocr_data if r.get('is_back_page'))
    data_pages = len(ocr_data) - back_pages
    print(f"\n  Data pages:     {data_pages:,} (front/data)")
    print(f"  Back pages:     {back_pages:,} (signature/back)")
    
    # --- Coverage by page number ---
    page_dist = defaultdict(int)
    for r in ocr_data:
        page_dist[r.get('page', 0)] += 1
    print(f"\n  Page number distribution:")
    for pg in sorted(page_dist.keys())[:10]:
        print(f"    page {pg}: {page_dist[pg]:,} records")
    if len(page_dist) > 10:
        print(f"    ... ({len(page_dist)} distinct page numbers)")
    
    # --- Actual total_pages analysis (per-file, not from compilation) ---
    # For files that are station-level (total_pages <= 6), they should be fully processed
    # For files with total_pages > 6, they are likely compilations
    small_files = defaultdict(int)  # total_pages -> count of files
    compilation_files = 0
    for f in ocr_files:
        file_records = [r for r in ocr_data if r.get('file', '') == f]
        if not file_records:
            continue
        tp = max(r.get('total_pages', 0) for r in file_records)
        if tp <= 6:
            small_files[tp] += 1
        else:
            compilation_files += 1
    
    print(f"\n  Station-level files (tp<=6): {sum(small_files.values()):,}")
    for tp, cnt in sorted(small_files.items()):
        print(f"    tp={tp}: {cnt:,} files")
    print(f"  Compilation files (tp>6):   {compilation_files:,}")
    
    # --- Summary ---
    pct_files = (len(ocr_files) / len(drive_labels) * 100) if drive_labels else 0
    print(f"\n  >>> File coverage: {len(ocr_files):,} / {len(drive_labels):,} = {pct_files:.1f}%")
    if missing_files:
        print(f"  >>> MISSING: {len(missing_files):,} Drive PDFs have NO OCR data")

print(f"\n{'='*60}")
print("DONE")
