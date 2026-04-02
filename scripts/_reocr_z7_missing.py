"""
Re-OCR the 2 problematic Zone 7 baengkhet files that only have 1 OCR record.
Verify actual PDF page count and attempt to extract all pages.
"""
import json, sys, os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

sys.path.insert(0, SCRIPT_DIR)
from ocr_multimodel import load_api_keys, process_page
from ocr_cloud_vision import pdf_bytes_to_png, download_pdf_from_drive, extract_metadata_from_drive_entry

drive_idx = json.load(open(os.path.join(DATA_DIR, 'drive_index_chaiyaphum.json'), encoding='utf-8'))
ocr = json.load(open(os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'), encoding='utf-8'))

# Find the 2 problematic files
target_names = [
    '\u0e15.\u0e17\u0e48\u0e32\u0e21\u0e30\u0e44\u0e1f\u0e2b\u0e27\u0e32\u0e19-\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15-\u0e2b\u0e19\u0e48\u0e27\u0e22\u0e17\u0e35\u0e48 1-11.pdf',
    '\u0e15.\u0e2b\u0e19\u0e2d\u0e07\u0e02\u0e32\u0e21-\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15-\u0e2b\u0e19\u0e48\u0e27\u0e22\u0e17\u0e35\u0e48 1-14.pdf',
]

targets = []
for item in drive_idx:
    if item['name'] in target_names:
        targets.append(item)

print('Found %d target files' % len(targets))
for t in targets:
    print('  %s (fid=%s, size=%d)' % (t['name'], t['file_id'], t.get('size', 0)))

keys = load_api_keys()
if 'GEMINI_API_KEY' not in keys and 'GOOGLE_CLOUD_API_KEY' not in keys:
    print('ERROR: No API keys found!')
    sys.exit(1)

for entry in targets:
    name = entry['name']
    fid = entry['file_id']
    print()
    print('Processing: %s' % name)
    print('  Downloading...')

    try:
        api_key = keys.get('GOOGLE_CLOUD_API_KEY', '')
        pdf_bytes = download_pdf_from_drive(fid, api_key)
        if not pdf_bytes:
            print('  ERR: Download failed')
            continue
        print('  PDF size: %d bytes' % len(pdf_bytes))
    except Exception as e:
        print('  ERR: %s' % e)
        continue

    # Count pages
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        total_pages = len(doc)
        doc.close()
        print('  PDF has %d pages' % total_pages)
    except Exception as e:
        print('  ERR counting pages: %s' % e)
        total_pages = 1

    if total_pages <= 1:
        print('  Only %d page(s) in PDF - this file is genuinely incomplete in Drive' % total_pages)
        continue

    # OCR all front pages
    meta = extract_metadata_from_drive_entry(entry)
    file_path = entry.get('path', '')
    file_name = entry.get('name', '')
    file_label = '%s/%s' % (file_path, file_name) if file_path else file_name

    # Get already-done pages
    done_pages = set()
    for r in ocr:
        if r.get('file') == file_label:
            done_pages.add(r.get('page'))

    print('  Already done pages: %s' % sorted(done_pages))
    new_results = []

    # Process all front pages (odd pages: 1, 3, 5, ...)
    for pg_idx in range(0, total_pages, 2):
        page_num_1indexed = pg_idx + 1
        if page_num_1indexed in done_pages:
            print('  Page %d: already done, skipping' % page_num_1indexed)
            continue

        print('  Processing page %d...' % page_num_1indexed, end=' ')
        try:
            png_result = pdf_bytes_to_png(pdf_bytes, pg_idx, dpi=200)
            if not png_result or png_result[0] is None:
                print('PNG conversion failed')
                continue
            png_bytes = png_result[0]
        except Exception as e:
            print('PNG error: %s' % e)
            continue

        models = ['gemini'] if 'GEMINI_API_KEY' in keys else ['cloud_vision']
        result = process_page(png_bytes, keys, models, pg_idx, meta, file_label)
        if result:
            result['total_pages'] = total_pages
            result['drive_file_id'] = fid
            result['drive_view_url'] = entry.get('view_url')
            new_results.append(result)
            print('  -> station=%s voters=%s' % (result.get('station_no'), result.get('registered_voters')))
        else:
            print('  OCR failed')

    if new_results:
        print('  Got %d new records, appending...' % len(new_results))
        ocr.extend(new_results)

# Save
if any(True for item in ocr if item.get('drive_file_id') in [t['file_id'] for t in targets]):
    with open(os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'), 'w', encoding='utf-8') as f:
        json.dump(ocr, f, ensure_ascii=False, indent=2)
    print('\nSaved updated OCR data')
print('Done.')
