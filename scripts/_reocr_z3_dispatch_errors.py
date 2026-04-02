"""
Re-OCR Zone 3 pages that failed during cloud dispatch.
dispatch_missing_errors_chaiyaphum.json has 2 Zone 3 errors.
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

errors = json.load(open(os.path.join(DATA_DIR, 'dispatch_missing_errors_chaiyaphum.json'), encoding='utf-8'))
drive_idx = json.load(open(os.path.join(DATA_DIR, 'drive_index_chaiyaphum.json'), encoding='utf-8'))
ocr = json.load(open(os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'), encoding='utf-8'))

# Get Zone 3 errors
z3_errors = [e for e in errors if '\u0e40\u0e02\u0e15\u0e40\u0e25\u0e37\u0e2d\u0e01\u0e15\u0e31\u0e49\u0e07\u0e17\u0e35\u0e48 3' in e.get('file', '')]
print('Zone 3 dispatch errors: %d' % len(z3_errors))
for e in z3_errors:
    print('  file=%s page=%d' % (e.get('file', '')[-60:], e.get('page')))

# Build lookup of done pages
done_pages_map = {}
for r in ocr:
    fl = r.get('file', '')
    pg = r.get('page', 0)
    done_pages_map.setdefault(fl, set()).add(pg)

keys = load_api_keys()
if 'GEMINI_API_KEY' not in keys and 'GOOGLE_CLOUD_API_KEY' not in keys:
    print('ERROR: No API keys found!')
    sys.exit(1)

new_results = []

for err in z3_errors:
    file_label = err.get('file', '')
    page_1indexed = err.get('page')  # 1-indexed
    page_0indexed = page_1indexed - 1  # convert to 0-indexed for pdf_bytes_to_png

    print()
    print('Re-OCR: file=%s page=%d' % (file_label[-60:], page_1indexed))

    # Find drive file id
    entry = None
    for item in drive_idx:
        p = item.get('path', '')
        n = item.get('name', '')
        fl = '%s/%s' % (p, n) if p else n
        if fl == file_label:
            entry = item
            break
        # Also try partial match
        if n in file_label or file_label.endswith(n):
            entry = item
            break

    if not entry:
        print('  ERR: Entry not found in drive_index for file: %s' % file_label)
        # Try fuzzy match
        for item in drive_idx:
            if item.get('name', '') in file_label:
                entry = item
                print('  Fuzzy match: %s' % item['name'])
                break

    if not entry:
        print('  ERR: Skipping')
        continue

    # Check if already done
    done = done_pages_map.get(file_label, set())
    if page_1indexed in done:
        print('  Already done, skipping')
        continue

    fid = entry['file_id']
    print('  Downloading fid=%s...' % fid)

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
        print('  PDF has %d pages, re-OCRing page %d' % (total_pages, page_1indexed))
    except Exception as e:
        print('  ERR counting pages: %s' % e)
        total_pages = page_1indexed

    if page_1indexed > total_pages:
        print('  Page %d out of range (%d total pages)' % (page_1indexed, total_pages))
        continue

    # Convert page to PNG
    try:
        png_result = pdf_bytes_to_png(pdf_bytes, page_0indexed, dpi=200)
        if not png_result or png_result[0] is None:
            print('  ERR: PNG conversion failed')
            continue
        png_bytes = png_result[0]
    except Exception as e:
        print('  ERR: PNG: %s' % e)
        continue

    # OCR
    meta = extract_metadata_from_drive_entry(entry)
    models = ['gemini'] if 'GEMINI_API_KEY' in keys else ['cloud_vision']
    print('  OCR with %s...' % models)
    result = process_page(png_bytes, keys, models, page_0indexed, meta, file_label)

    if result:
        result['total_pages'] = total_pages
        result['drive_file_id'] = fid
        result['drive_view_url'] = entry.get('view_url')
        new_results.append(result)
        print('  -> station=%s voters=%s vote_type=%s' % (result.get('station_no'), result.get('registered_voters'), result.get('vote_type')))
    else:
        print('  OCR returned no result')

print()
print('New results: %d' % len(new_results))
if new_results:
    ocr.extend(new_results)
    out_path = os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(ocr, f, ensure_ascii=False, indent=2)
    print('Saved to %s' % out_path)
print('Done.')
