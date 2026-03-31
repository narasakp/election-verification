# -*- coding: utf-8 -*-
"""Find which PDFs failed to download and which pages still have 503 errors.
Outputs actionable lists for re-downloading and re-OCR."""
import json, os, re
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

for prov in ['tak', 'phetchabun']:
    err_path = os.path.join(DATA, f'dispatch_missing_errors_{prov}.json')
    if not os.path.exists(err_path):
        print(f"{prov}: no error log"); continue

    errors = json.load(open(err_path, 'r', encoding='utf-8'))

    pdf_fail = []   # (file_path, page, drive_file_id)
    svc_503 = []    # (file_path, page)

    for e in errors:
        msg = e.get('error', '')
        fname = e.get('file', '')
        page = e.get('page', 0)
        m = re.search(r'file_id["\s:]+["\']?([A-Za-z0-9_-]{20,})', msg)
        fid = m.group(1) if m else ''

        if 'PDF download failed' in msg:
            pdf_fail.append((fname, page, fid))
        elif '503' in msg or 'Service Unavailable' in msg:
            svc_503.append((fname, page))

    # ── Group PDF failures by file_id ──
    by_fid = defaultdict(list)
    for fname, page, fid in pdf_fail:
        by_fid[fid].append((fname, page))

    # ── Group 503 by file name ──
    by_503 = defaultdict(list)
    for fname, page in svc_503:
        by_503[fname].append(page)

    # ── Also check drive index for these file_ids ──
    idx_path = os.path.join(DATA, f'drive_index_{prov}.json')
    drive_idx = json.load(open(idx_path, 'r', encoding='utf-8')) if os.path.exists(idx_path) else []
    fid_to_drive = {d.get('file_id', ''): d for d in drive_idx}

    print(f"\n{'='*70}")
    print(f"  {prov.upper()}")
    print(f"{'='*70}")
    print(f"  PDF download failed: {len(pdf_fail)} pages, {len(by_fid)} unique file_ids")
    print(f"  503 errors:          {len(svc_503)} pages, {len(by_503)} unique files")

    if by_fid:
        print(f"\n  --- PDF DOWNLOAD FAILURES ---")
        for fid, entries in sorted(by_fid.items(), key=lambda x: -len(x[1])):
            n_pages = len(entries)
            sample_name = entries[0][0][:70]
            drive_entry = fid_to_drive.get(fid, {})
            drive_name = drive_entry.get('name', '?')
            drive_url = drive_entry.get('download_url', drive_entry.get('view_url', ''))
            print(f"\n  file_id: {fid}")
            print(f"  Drive name: {drive_name}")
            print(f"  Path: {sample_name}")
            print(f"  Missing pages: {n_pages}")
            print(f"  Drive URL: {drive_url[:100]}")

    if by_503:
        print(f"\n  --- 503 ERRORS (retryable) ---")
        for fname, pages in sorted(by_503.items(), key=lambda x: -len(x[1])):
            print(f"  {len(pages):3d} pages — {fname[:80]}")
            # Find file_id from drive index
            for d in drive_idx:
                if d.get('name', '') in fname or fname in d.get('path', ''):
                    print(f"          file_id: {d.get('file_id', '?')}")
                    break

print(f"\n{'='*70}")
print("DONE — use these file_ids to download PDFs from Drive backup")
