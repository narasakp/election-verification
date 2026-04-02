"""
Re-OCR missing middle pages for n=33 บัญชีรายชื่อ records.

Root cause: OCR pipeline skipped even-numbered middle pages in 3-page party list forms.
Example: merged_pages=[13,15] means page 14 (parties 11-34) was never OCR'd.

Strategy:
- Load 1,719 targets from _reocr_n33_targets.json
- Group by FID (274 unique PDFs)
- Download each PDF once, OCR the missing page
- Merge new candidates (parties 11-34) into the existing consolidated record
- Save updated OCR JSON files
"""
import json, sys, os, shutil
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

sys.path.insert(0, SCRIPT_DIR)
from ocr_multimodel import load_api_keys, process_page
from ocr_cloud_vision import pdf_bytes_to_png, download_pdf_from_drive

# ── Load data ──────────────────────────────────────────────────────────────
targets = json.load(open(os.path.join(DATA_DIR, '_reocr_n33_targets.json'), encoding='utf-8'))

ocr_files = {
    'phetchabun': os.path.join(DATA_DIR, 'ocr_multimodel_phetchabun.json'),
    'chaiyaphum': os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'),
    'tak':        os.path.join(DATA_DIR, 'ocr_multimodel_tak.json'),
}
ocr_data = {k: json.load(open(v, encoding='utf-8')) for k, v in ocr_files.items()}

# Build source lookup: (file, page) -> (prov_key, list_index)
src_lookup = {}
for prov, records in ocr_data.items():
    for idx, r in enumerate(records):
        src_lookup[(r.get('file', ''), r.get('page', 0))] = (prov, idx)

# ── API keys ───────────────────────────────────────────────────────────────
keys = load_api_keys()
if 'GEMINI_API_KEY' not in keys:
    print('ERROR: GEMINI_API_KEY not found')
    sys.exit(1)

# ── Group by FID ───────────────────────────────────────────────────────────
fid_groups = defaultdict(list)
for t in targets:
    fid_groups[t['fid']].append(t)

print(f'Targets: {len(targets)}  Unique PDFs: {len(fid_groups)}')

# ── Track new OCR records to insert ───────────────────────────────────────
new_records = {'chaiyaphum': [], 'phetchabun': [], 'tak': []}
updated = 0
failed = 0
still_zero = 0

# ── Re-OCR loop ────────────────────────────────────────────────────────────
for fid_idx, (fid, group) in enumerate(fid_groups.items()):
    pages = sorted(set(t['missing_page'] for t in group))
    prov_key = group[0]['prov_key']
    print(f'\n[{fid_idx+1}/{len(fid_groups)}] fid={fid} ({prov_key}) — {len(pages)} missing pages: {pages}')

    # Download PDF once
    try:
        api_key = keys.get('GOOGLE_CLOUD_API_KEY', '')
        pdf_bytes = download_pdf_from_drive(fid, api_key)
        if not pdf_bytes:
            print('  ERR: Download failed')
            failed += len(group)
            continue
        print(f'  Downloaded {len(pdf_bytes):,} bytes')
    except Exception as e:
        print(f'  ERR download: {e}')
        failed += len(group)
        continue

    # Count pages
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        total_pages = len(doc)
        doc.close()
    except Exception:
        total_pages = 999

    # OCR each missing page
    for missing_page in pages:
        page_0idx = missing_page - 1
        if missing_page > total_pages:
            print(f'  Page {missing_page} out of range ({total_pages})')
            failed += sum(1 for t in group if t['missing_page'] == missing_page)
            continue

        print(f'  OCR page {missing_page}/{total_pages}...', end=' ')
        try:
            png_result = pdf_bytes_to_png(pdf_bytes, page_0idx, dpi=200)
            if not png_result or png_result[0] is None:
                print('PNG fail')
                failed += sum(1 for t in group if t['missing_page'] == missing_page)
                continue
            png_bytes = png_result[0]
        except Exception as e:
            print(f'PNG err: {e}')
            failed += sum(1 for t in group if t['missing_page'] == missing_page)
            continue

        # Get file label from a target for this page
        sample_target = next(t for t in group if t['missing_page'] == missing_page)
        file_label = sample_target['file']

        try:
            result = process_page(png_bytes, keys, ['gemini'], page_0idx, {}, file_label)
        except Exception as e:
            print(f'OCR err: {e}')
            failed += sum(1 for t in group if t['missing_page'] == missing_page)
            continue

        if not result:
            print('no result')
            failed += sum(1 for t in group if t['missing_page'] == missing_page)
            continue

        new_cands = result.get('candidates', [])
        print(f'-> {len(new_cands)} candidates')

        if len(new_cands) == 0:
            still_zero += sum(1 for t in group if t['missing_page'] == missing_page)
            continue

        # For each target using this page, merge candidates into existing record
        page_targets = [t for t in group if t['missing_page'] == missing_page]
        for t in page_targets:
            fl = t['file']
            # Find the consolidated record in OCR data
            # The consolidated record is at the first merged page
            first_page = min(t['known_pages'])
            entry = src_lookup.get((fl, first_page))
            if not entry:
                print(f'    WARN: source record not found for {t["review_id"]}')
                failed += 1
                continue

            prov, idx = entry
            src_rec = ocr_data[prov][idx]
            existing_cands = src_rec.get('candidates', [])

            # Merge: keep existing, add new ones (avoid duplicates by number)
            existing_nums = {c.get('number') for c in existing_cands}
            to_add = [c for c in new_cands if c.get('number') not in existing_nums]

            if to_add:
                merged = sorted(existing_cands + to_add, key=lambda c: c.get('number', 999))
                src_rec['candidates'] = merged
                src_rec['_reocr_n33'] = True
                updated += 1
            else:
                # All numbers already present — maybe wrong page
                print(f'    WARN: no new candidates added for {t["review_id"]} (all numbers already present)')
                failed += 1

print(f'\n{"="*60}')
print(f'Updated: {updated}  Failed: {failed}  Still-zero: {still_zero}')

# ── Save updated OCR files ─────────────────────────────────────────────────
if updated > 0:
    prov_updated = set()
    for prov, records in ocr_data.items():
        if any(r.get('_reocr_n33') for r in records):
            prov_updated.add(prov)

    for prov in prov_updated:
        path = ocr_files[prov]
        backup = path + '.pre_reocr_n33'
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
            print(f'Backup: {backup}')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(ocr_data[prov], f, ensure_ascii=False, indent=2)
        n_fixed = sum(1 for r in ocr_data[prov] if r.get('_reocr_n33'))
        print(f'Saved {prov}: {n_fixed} records updated')
else:
    print('No updates — OCR files unchanged')

print('Done.')
