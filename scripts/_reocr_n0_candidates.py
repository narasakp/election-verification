"""
Re-OCR records that have ballot data but zero candidates extracted.
Targets: เพชรบูรณ์ Z4(28)/Z5(59), ตาก Z2(7), ชัยภูมิ(3) = 96 records / 24 unique PDFs.

Strategy:
- Download each unique PDF once
- For each target page, extract PNG and re-OCR with Gemini
- Update candidates field in the source OCR JSON (do NOT add new records)
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
review = json.load(open(os.path.join(PROJECT_ROOT, 'review-app/public/data/review_data.json'), encoding='utf-8'))

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
        key = (r.get('file', ''), r.get('page', 0))
        src_lookup[key] = (prov, idx)

# ── Identify n=0 targets ───────────────────────────────────────────────────
targets = []
for r in review:
    if r.get('vote_type') != 'แบ่งเขต':
        continue
    if len(r.get('candidates', [])) != 0:
        continue
    if not (r.get('turnout') or r.get('valid_ballots')):
        continue
    fl = r.get('file', '')
    pg = r.get('page', 1)
    entry = src_lookup.get((fl, pg)) or src_lookup.get((fl, 1))
    if not entry:
        print(f'WARN: no source match for {r["id"]}')
        continue
    prov_key, idx = entry
    src_rec = ocr_data[prov_key][idx]
    fid = src_rec.get('drive_file_id')
    if not fid:
        print(f'WARN: no fid for {r["id"]}')
        continue
    targets.append({
        'review_id': r['id'],
        'file': fl,
        'src_page': src_rec.get('page', 1),   # 1-indexed page in source PDF
        'fid': fid,
        'prov_key': prov_key,
        'src_idx': idx,
        'province': r.get('province', ''),
        'constituency': r.get('constituency', ''),
        'turnout': r.get('turnout'),
    })

print(f'Re-OCR targets: {len(targets)}')

# Group by FID to download each PDF only once
fid_groups = defaultdict(list)
for t in targets:
    fid_groups[t['fid']].append(t)
print(f'Unique PDFs: {len(fid_groups)}')

# ── API keys ───────────────────────────────────────────────────────────────
keys = load_api_keys()
if 'GEMINI_API_KEY' not in keys:
    print('ERROR: GEMINI_API_KEY not found')
    sys.exit(1)

# ── Re-OCR loop ────────────────────────────────────────────────────────────
updated = 0
failed = 0

for fid, group in fid_groups.items():
    pages_str = [str(t['src_page']) for t in group]
    print(f'\nPDF fid={fid} — {len(group)} pages to re-OCR: {pages_str}')

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
    except Exception as e:
        print(f'  ERR counting pages: {e}')
        total_pages = 999

    # Process each target page in this PDF
    for t in group:
        page_1indexed = t['src_page']
        page_0indexed = page_1indexed - 1
        print(f'  Page {page_1indexed}/{total_pages}: {t["review_id"]} (zone={t["constituency"]} turn={t["turnout"]})')

        if page_1indexed > total_pages:
            print(f'    ERR: page {page_1indexed} > total {total_pages}')
            failed += 1
            continue

        # Convert to PNG
        try:
            png_result = pdf_bytes_to_png(pdf_bytes, page_0indexed, dpi=200)
            if not png_result or png_result[0] is None:
                print('    ERR: PNG conversion failed')
                failed += 1
                continue
            png_bytes = png_result[0]
        except Exception as e:
            print(f'    ERR PNG: {e}')
            failed += 1
            continue

        # Re-OCR with Gemini
        try:
            result = process_page(png_bytes, keys, ['gemini'], page_0indexed, {}, t['file'])
        except Exception as e:
            print(f'    ERR OCR: {e}')
            failed += 1
            continue

        if not result:
            print('    OCR returned no result')
            failed += 1
            continue

        cands = result.get('candidates', [])
        print(f'    -> candidates={len(cands)}, turnout={result.get("turnout")}')

        if len(cands) == 0:
            print('    Still n=0 after re-OCR, skipping update')
            failed += 1
            continue

        # Update source record
        src_rec = ocr_data[t['prov_key']][t['src_idx']]
        src_rec['candidates'] = cands
        src_rec['_reocr_n0'] = True
        updated += 1
        print(f'    Updated {t["prov_key"]}[{t["src_idx"]}] candidates={len(cands)}')

print(f'\n{"="*50}')
print(f'Updated: {updated}  Failed/still-0: {failed}')

# ── Save updated OCR files ─────────────────────────────────────────────────
if updated > 0:
    for prov_key, path in ocr_files.items():
        # Check if this province had any updates
        had_update = any(
            ocr_data[prov_key][t['src_idx']].get('_reocr_n0')
            for t in targets if t['prov_key'] == prov_key
        )
        if had_update:
            backup = path + '.pre_reocr_n0'
            if not os.path.exists(backup):
                shutil.copy2(path, backup)
                print(f'Backup: {backup}')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ocr_data[prov_key], f, ensure_ascii=False, indent=2)
            print(f'Saved: {path}')
else:
    print('No updates — OCR files unchanged')

print('Done.')
