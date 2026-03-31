"""Check OCR completion status for all 3 provinces."""
import json, os

DATA = os.path.join(os.path.dirname(__file__), '..', 'data')

# Load OCR results
provinces = {
    'chaiyaphum': 'ocr_multimodel_chaiyaphum.json',
    'tak': 'ocr_multimodel_tak.json',
    'phetchabun': 'ocr_multimodel_phetchabun.json',
}

# Load Drive index for expected PDF counts
drive_idx = json.load(open(os.path.join(DATA, 'ss518_drive_index.json'), 'r', encoding='utf-8'))
drive_provinces = {p['slug']: p for p in drive_idx.get('provinces', [])}

print("=" * 70)
print("OCR STATUS CHECK")
print("=" * 70)

for prov, fname in provinces.items():
    fpath = os.path.join(DATA, fname)
    if not os.path.exists(fpath):
        print(f"\n{prov}: FILE NOT FOUND ({fname})")
        continue
    
    records = json.load(open(fpath, 'r', encoding='utf-8'))
    files = set(r.get('file', '') for r in records)
    pages = set((r.get('file', ''), r.get('page', '')) for r in records)
    
    # Count pages per file for total page estimate
    total_pages_sum = sum(r.get('total_pages', 1) for r in records if r.get('file', '') in files)
    # Deduplicate: get total_pages per unique file
    file_total_pages = {}
    for r in records:
        f = r.get('file', '')
        tp = r.get('total_pages', None)
        if f and tp:
            file_total_pages[f] = max(file_total_pages.get(f, 0), int(tp))
    
    expected_pages = sum(file_total_pages.values())
    
    # Drive info
    dp = drive_provinces.get(prov, {})
    drive_pdfs = dp.get('pdf_count', '?')
    drive_uploaded = dp.get('uploaded', '?')
    
    # Check for missing pages
    missing_pages = []
    for f, tp in file_total_pages.items():
        ocr_pages = set(r.get('page', 0) for r in records if r.get('file', '') == f)
        for p in range(1, tp + 1):
            if p not in ocr_pages:
                missing_pages.append((f, p, tp))
    
    # Files with no records at all (from Drive index)
    ocr_files_set = set(r.get('file', '') for r in records)
    
    pct = (len(pages) / expected_pages * 100) if expected_pages > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"  {prov.upper()}")
    print(f"{'='*50}")
    print(f"  OCR records:      {len(records):,}")
    print(f"  Unique files:     {len(files):,}")
    print(f"  Unique pages:     {len(pages):,}")
    print(f"  Expected pages:   {expected_pages:,} (from total_pages in records)")
    print(f"  Drive PDFs:       {drive_pdfs}")
    print(f"  Drive uploaded:   {drive_uploaded}")
    print(f"  Completion:       {pct:.1f}%")
    print(f"  Missing pages:    {len(missing_pages)}")
    
    # Summarize missing by pattern
    if missing_pages:
        # Count how many are "last page" (page == total_pages, often signature page)
        last_page_missing = sum(1 for f, p, tp in missing_pages if p == tp)
        mid_page_missing = len(missing_pages) - last_page_missing
        print(f"  Missing last-page: {last_page_missing} (often signature/non-data)")
        print(f"  Missing mid-page:  {mid_page_missing} (likely data pages)")

print(f"\n{'='*70}")
print("DONE")
