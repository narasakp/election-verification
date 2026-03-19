# -*- coding: utf-8 -*-
"""
Local OCR for stubborn pages that fail on Cloud Function (503).
Reads PDFs from local cache, calls Gemini API directly, saves to GCS.

Usage:
  python cloud/ocr_local.py --province chaiyaphum
  python cloud/ocr_local.py --province chaiyaphum --limit 5 --delay 3
"""
import argparse
import base64
import json
import os
import re
import sys
import time
from collections import defaultdict

import fitz  # PyMuPDF
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PDF_CACHE_DIR = os.path.join(DATA_DIR, '_pdf_cache_tmp')

GCS_BUCKET = "election69-ocr-results-th"

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
]

EXTRACTION_PROMPT_BASE = """คุณเป็นผู้เชี่ยวชาญอ่านเอกสารเลือกตั้งไทย (แบบฟอร์ม สส.5/18)
อ่านภาพแล้วตอบเป็น JSON ตาม schema นี้:

{"vote_type":"แบ่งเขต|บัญชีรายชื่อ","province":"...","constituency":1,"district":"...","sub_district":"...","station_no":1,"registered_voters":850,"turnout":720,"ballots_received":850,"valid_ballots":692,"invalid_ballots":5,"no_vote_ballots":23,"remaining_ballots":130,"candidates":[{"number":1,"name":"...","party":"...","votes":285}],"total_votes":692,"is_back_page":false}

คำจำกัดความ:
- ballots_received = บัตรที่ได้รับมาทั้งหมด (ก่อนแจก)
- valid_ballots = บัตรดี, invalid_ballots = บัตรเสีย, no_vote_ballots = ไม่ประสงค์ลงคะแนน
- remaining_ballots = บัตรเหลือ = ballots_received - turnout

ตรวจสอบ: ballots_received = valid + invalid + no_vote + remaining, turnout ≤ registered_voters
ถ้ามีตัวเลขอาราบิกและตัวหนังสือไทยไม่ตรงกัน ให้ใช้ค่าที่ใหญ่กว่า
ถ้าอ่านไม่ออก ใส่ null / ถ้าเป็นหน้าหลัง(ลายเซ็น) ตั้ง is_back_page:true
บัญชีรายชื่อ: name มักเป็น null, number คือเลขพรรค
อ่านผู้สมัครให้ครบทุกแถว อย่าข้ามแถวที่คะแนนเป็น 0
ตอบเป็น JSON เท่านั้น"""


def build_prompt(meta=None, page_num=None, total_pages=None):
    """Build context-aware extraction prompt."""
    parts = [EXTRACTION_PROMPT_BASE]

    if total_pages and total_pages > 4:
        parts.append(
            "\n\n** สำคัญ: ไฟล์ PDF นี้มี %d หน้า รวมหลายหน่วยเลือกตั้ง "
            "(หน้าคี่=ข้อมูล, หน้าคู่=ลายเซ็น) "
            "อ่านเฉพาะข้อมูลของหน่วยเดียวที่อยู่ในหน้านี้เท่านั้น "
            "ห้ามนำข้อมูลจากหน่วยอื่นในหน้าอื่นมาปน" % total_pages
        )

    if page_num is not None:
        parts.append(
            "\nคุณกำลังอ่านหน้าที่ %d จาก %d หน้า"
            % (page_num + 1, total_pages or 0)
        )

    if meta:
        hints = []
        if meta.get('province'):
            hints.append('province="%s"' % meta['province'])
        if meta.get('constituency'):
            hints.append('constituency=%d' % meta['constituency'])
        if meta.get('vote_type'):
            hints.append('vote_type="%s"' % meta['vote_type'])
        if meta.get('district'):
            hints.append('district="%s"' % meta['district'])
        if hints:
            parts.append(
                "\n\nข้อมูลที่ทราบแน่นอนจากชื่อไฟล์ (ใช้ค่านี้เสมอ ห้ามเปลี่ยน): "
                + ", ".join(hints)
            )

    return "\n".join(parts)

PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
    "tak": "tak", "chaiyaphum": "chaiyaphum", "phetchabun": "phetchabun",
}


def load_env():
    env = {}
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def _repair_json(text):
    """Attempt to repair common malformed JSON from LLM responses."""
    if not text or not text.strip():
        return None
    m = re.search(r'\{', text)
    if not m:
        return None
    s = text[m.start():]
    last_brace = s.rfind('}')
    if last_brace >= 0:
        s = s[:last_brace + 1]
    s = re.sub(r',\s*([}\]])', r'\1', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    repaired = s.rstrip()
    repaired = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"{}\[\]]*$', '', repaired)
    quote_count = repaired.count('"') - repaired.count('\\"')
    if quote_count % 2 != 0:
        repaired += '"'
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    repaired = repaired.rstrip().rstrip(',')
    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    return None


def pdf_bytes_to_png(pdf_bytes, page_num=0, dpi=200):
    """Convert a single PDF page to PNG bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    if page_num >= total:
        doc.close()
        return None, total
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes, total


def _call_gemini_once(png_b64, api_key, model, temperature=0.0,
                     prompt=None):
    """Single Gemini API call. Returns dict|'retry'|None."""
    if prompt is None:
        prompt = build_prompt()
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": png_b64}}
        ]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=300)
        if resp.status_code in (429, 503):
            return 'retry'
        resp.raise_for_status()
        data = resp.json()
        text = data['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(text)
        return {'model': 'gemini', 'model_variant': model, 'result': result}
    except (json.JSONDecodeError, KeyError, IndexError):
        if 'text' in dir():
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return {'model': 'gemini', 'model_variant': model,
                            'result': json.loads(match.group())}
                except json.JSONDecodeError:
                    pass
            repaired = _repair_json(text)
            if repaired:
                return {'model': 'gemini', 'model_variant': model,
                        'result': repaired}
        return None
    except requests.RequestException:
        return 'retry'


def ocr_page(png_bytes, api_key, meta=None, page_num=None,
             total_pages=None):
    """OCR a single page with multi-model Gemini fallback."""
    b64 = base64.b64encode(png_bytes).decode('utf-8')
    prompt = build_prompt(meta=meta, page_num=page_num,
                          total_pages=total_pages)
    for cycle in range(3):
        if cycle > 0:
            time.sleep(10 * cycle)
        for model in GEMINI_MODELS:
            result = _call_gemini_once(b64, api_key, model, prompt=prompt)
            if result == 'retry':
                continue
            if result is not None:
                return result
    return None


def extract_metadata(file_label):
    """Extract province/constituency/vote_type from file path."""
    meta = {"province": None, "constituency": None, "vote_type": None,
            "district": None, "sub_district": None}
    parts = file_label.replace('\\', '/').split('/')
    for p in parts:
        m = re.match(r'จังหวัด(.+)', p)
        if m:
            meta["province"] = m.group(1).strip()
        m2 = re.match(r'เขตเลือกตั้งที่\s*(\d+)', p)
        if m2:
            meta["constituency"] = int(m2.group(1))
        m3 = re.match(r'อำเภอ(.+)', p)
        if m3:
            meta["district"] = m3.group(1).strip()
    if 'แบ่งเขต' in file_label:
        meta["vote_type"] = "แบ่งเขต"
    elif 'บัญชีรายชื่อ' in file_label:
        meta["vote_type"] = "บัญชีรายชื่อ"
    return meta


def save_to_gcs(blob_path, data):
    """Save JSON data to GCS blob."""
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )


def build_missing_tasks(slug):
    """Find missing front pages, return list of tasks."""
    ocr_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    existing = json.load(open(ocr_path, encoding='utf-8'))

    idx_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    drive_index = json.load(open(idx_path, encoding='utf-8'))

    # Build done_pages lookup (1-indexed)
    done_pages = defaultdict(set)
    file_total = {}
    for item in existing:
        fl = item.get('file', '')
        pg = item.get('page', 0)
        done_pages[fl].add(pg)
        tp = item.get('total_pages')
        if tp and (fl not in file_total or tp > file_total[fl]):
            file_total[fl] = tp

    # Build label -> entry map
    label_to_entry = {}
    for fi in drive_index:
        if not fi.get('name', '').lower().endswith('.pdf'):
            continue
        fl = fi['path'] + '/' + fi['name']
        label_to_entry[fl] = fi

    # Find missing front pages
    tasks = []
    for fl, entry in label_to_entry.items():
        tp = file_total.get(fl)
        done = done_pages.get(fl, set())
        if tp is None or tp <= 4:
            if tp and len(done) >= tp // 2:
                continue
            if tp is None:
                continue
        all_target = set(range(1, tp + 1, 2))  # front pages (1-indexed odd)
        missing = sorted(all_target - done)
        for page_1indexed in missing:
            tasks.append({
                'file_id': entry['file_id'],
                'file_label': fl,
                'page_num': page_1indexed - 1,  # 0-indexed for processing
                'page_1indexed': page_1indexed,
                'total_pages': tp,
            })

    return tasks


def main():
    parser = argparse.ArgumentParser(description="Local OCR for stubborn pages")
    parser.add_argument("--province", required=True)
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between Gemini calls (default: 2)")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    slug = PROVINCE_SLUGS.get(args.province, args.province)
    env = load_env()
    gemini_key = env.get('GEMINI_API_KEY', '')
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY not found in .env")
        sys.exit(1)

    tasks = build_missing_tasks(slug)
    print(f"[Province]  {slug}")
    print(f"[Missing]   {len(tasks)} front pages")
    print(f"[PDF cache] {PDF_CACHE_DIR}")
    print(f"[Delay]     {args.delay}s between calls")

    # Check local PDF cache availability
    cached_fids = set()
    for f in os.listdir(PDF_CACHE_DIR) if os.path.exists(PDF_CACHE_DIR) else []:
        if f.endswith('.pdf'):
            cached_fids.add(f[:-4])

    tasks_with_cache = [t for t in tasks if t['file_id'] in cached_fids]
    tasks_no_cache = [t for t in tasks if t['file_id'] not in cached_fids]
    print(f"[Cached]    {len(tasks_with_cache)} pages have local PDF")
    if tasks_no_cache:
        print(f"[No cache]  {len(tasks_no_cache)} pages missing local PDF (skipped)")

    tasks = tasks_with_cache
    if args.limit > 0:
        tasks = tasks[:args.limit]
    print(f"[Process]   {len(tasks)} pages")

    if not tasks:
        print("Nothing to do!")
        return

    print()
    success = 0
    failed = 0
    start = time.time()

    for i, task in enumerate(tasks):
        fid = task['file_id']
        fl = task['file_label']
        pn = task['page_num']
        label = fl[-55:]
        print(f"  [{i+1}/{len(tasks)}] p{pn+1} ...{label}", end="", flush=True)

        # 1) Load PDF from local cache
        pdf_path = os.path.join(PDF_CACHE_DIR, f"{fid}.pdf")
        pdf_bytes = open(pdf_path, 'rb').read()

        # 2) Convert to PNG (adaptive DPI)
        png_bytes_page = None
        total_pages = 0
        for dpi in [150, 100]:
            try:
                result = pdf_bytes_to_png(pdf_bytes, pn, dpi=dpi)
                if result and result[0]:
                    png_bytes_page = result[0]
                    total_pages = result[1]
                    break
            except Exception:
                continue

        if not png_bytes_page:
            print(" -> SKIP (PNG failed)")
            failed += 1
            continue

        # 3) OCR with Gemini (context-aware prompt)
        meta = extract_metadata(fl)
        ocr_result = ocr_page(png_bytes_page, gemini_key,
                              meta=meta, page_num=pn,
                              total_pages=task.get('total_pages'))
        if not ocr_result:
            print(" -> SKIP (OCR failed)")
            failed += 1
            continue

        # 4) Build output record (same format as CF)
        record = ocr_result.get('result', {})
        # Always override with file metadata (ground truth from file path)
        if meta.get('province'):
            record['province'] = meta['province']
        if meta.get('constituency'):
            record['constituency'] = meta['constituency']
        if meta.get('vote_type'):
            record['vote_type'] = meta['vote_type']

        output = {
            "file": fl,
            "page": pn + 1,
            "total_pages": total_pages,
            "drive_file_id": fid,
            "model": ocr_result.get('model'),
            "model_variant": ocr_result.get('model_variant'),
            **record,
        }

        # 5) Save to GCS (same path as CF would)
        blob_path = f"{slug}/{fid}_p{pn}.json"
        try:
            save_to_gcs(blob_path, [output])
            print(f" -> OK (saved to GCS)")
            success += 1
        except Exception as e:
            print(f" -> OK (OCR done, GCS save failed: {str(e)[:40]})")
            success += 1  # OCR succeeded even if GCS save failed

        # Delay between calls
        if i < len(tasks) - 1:
            time.sleep(args.delay)

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {success}/{len(tasks)}")
    print(f"  Failed:  {failed}")
    print(f"\nNext: python cloud/collect.py --province {slug} --merge")


if __name__ == '__main__':
    main()
