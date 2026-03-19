# -*- coding: utf-8 -*-
"""
Cloud Function: OCR Worker for สส.5/18 election forms.

Receives an HTTP request with file info, downloads PDF from Drive,
OCRs each page with Gemini (multi-model fallback), saves results
to Cloud Storage.

Deploy:
  gcloud functions deploy ocr-worker \
    --gen2 --runtime python311 --region asia-southeast1 \
    --source cloud/function \
    --entry-point handle_request \
    --trigger-http --allow-unauthenticated \
    --memory 512MB --timeout 540s \
    --set-env-vars GEMINI_API_KEY=xxx,GCS_BUCKET=election69-ocr-results-th
"""
import base64
import json
import os
import re
import time

import fitz  # PyMuPDF
import functions_framework
import requests
from google.cloud import storage

# ── Config ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "election69-ocr-results-th")

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
    """Build context-aware extraction prompt.

    Injects known metadata so the LLM doesn't have to guess
    constituency/province/vote_type from the image alone.
    """
    parts = [EXTRACTION_PROMPT_BASE]

    # Multi-station PDF context
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

    # Known metadata from file path (ground truth)
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


# ── PDF → PNG ─────────────────────────────────────────────────────────

def pdf_bytes_to_png(pdf_bytes, page_num=0, dpi=200):
    """Convert a single PDF page to PNG bytes in memory."""
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


# ── Download PDF from Google Drive ────────────────────────────────────

def download_pdf_from_drive(file_id, api_key=""):
    """Download a file from Google Drive by file_id."""
    # Try direct download first (publicly shared files)
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    if api_key:
        url += f"&key={api_key}"
    resp = requests.get(url, timeout=60)
    if resp.status_code == 200 and len(resp.content) > 100:
        return resp.content
    # Fallback: export link
    url2 = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp2 = requests.get(url2, timeout=60, allow_redirects=True)
    if resp2.status_code == 200 and len(resp2.content) > 100:
        return resp2.content
    return None


# ── JSON Repair ───────────────────────────────────────────────────────

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
    cand_match = re.search(r'"candidates"\s*:\s*\[', repaired)
    if cand_match:
        before = repaired[:cand_match.start()].rstrip().rstrip(',')
        before += '"candidates": []}'
        before = re.sub(r',\s*([}\]])', r'\1', before)
        try:
            return json.loads(before)
        except json.JSONDecodeError:
            pass
    return None


# ── Gemini OCR (multi-model fallback) ─────────────────────────────────

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
        resp = requests.post(url, json=payload, timeout=90)
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
    """OCR a single page image with multi-model Gemini fallback."""
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


# ── Metadata extraction from file label ───────────────────────────────

def extract_metadata(file_label):
    """Extract province/constituency/vote_type from file path."""
    meta = {"province": None, "constituency": None, "vote_type": None,
            "district": None, "sub_district": None}
    parts = file_label.replace('\\', '/').split('/')
    for p in parts:
        m = re.match(r'จังหวัด(.+)', p)
        if m:
            meta["province"] = m.group(1).strip()
        m = re.match(r'เขตเลือกตั้งที่\s*(\d+)', p)
        if m:
            meta["constituency"] = int(m.group(1))
        m = re.match(r'อำเภอ(.+)', p)
        if m:
            meta["district"] = m.group(1).strip()
    if 'แบ่งเขต' in file_label:
        meta["vote_type"] = "แบ่งเขต"
    elif 'บัญชีรายชื่อ' in file_label:
        meta["vote_type"] = "บัญชีรายชื่อ"
    return meta


# ── Save to Cloud Storage ─────────────────────────────────────────────

def save_to_gcs(bucket_name, blob_path, data):
    """Save JSON data to a GCS blob."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )


# ── Cloud Function entry point ────────────────────────────────────────

@functions_framework.http
def handle_request(request):
    """HTTP Cloud Function entry point.

    Expects JSON body:
    {
        "file_id": "Google Drive file ID",
        "file_label": "path/to/file.pdf",
        "province": "tak",
        "google_api_key": "optional Drive API key",
        "max_pages": 4,
        "page_num": null  // optional: process single page (0-indexed)
    }

    Returns JSON with status and results summary.
    """
    try:
        req = request.get_json(silent=True) or {}
    except Exception:
        return {"error": "Invalid JSON"}, 400

    file_id = req.get("file_id")
    file_label = req.get("file_label", "")
    province = req.get("province", "unknown")
    google_api_key = req.get("google_api_key", "")
    max_pages = req.get("max_pages", 4)
    page_num = req.get("page_num")  # None = all pages, int = single page

    if not file_id:
        return {"error": "file_id required"}, 400

    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not configured"}, 500

    try:
        return _process_request(file_id, file_label, province,
                                google_api_key, max_pages, page_num)
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()[-500:],
                "file_id": file_id}, 500


def _get_pdf_bytes(file_id, google_api_key):
    """Get PDF bytes, using GCS cache to avoid redundant Drive downloads."""
    cache_path = f"_pdf_cache/{file_id}.pdf"
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(cache_path)
        if blob.exists():
            return blob.download_as_bytes()
    except Exception:
        pass
    # Download from Drive
    pdf_bytes = download_pdf_from_drive(file_id, google_api_key)
    if pdf_bytes and len(pdf_bytes) > 100:
        # Validate it's actually a PDF
        if pdf_bytes[:4] == b'%PDF':
            try:
                blob = bucket.blob(cache_path)
                blob.upload_from_string(pdf_bytes, content_type='application/pdf')
            except Exception:
                pass
            return pdf_bytes
    return None


def _process_request(file_id, file_label, province, google_api_key,
                     max_pages, page_num):
    """Inner processing logic, wrapped by handle_request for error handling."""
    # 1) Download PDF (with GCS caching)
    pdf_bytes = _get_pdf_bytes(file_id, google_api_key)
    if not pdf_bytes:
        return {"error": "PDF download failed", "file_id": file_id}, 502

    # 2) Get total pages
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    doc.close()

    # Single page mode (split retry)
    if page_num is not None:
        page_num = int(page_num)
        if page_num >= total_pages:
            return {"status": "skip", "reason": "page out of range",
                    "file_id": file_id, "page_num": page_num,
                    "total_pages": total_pages}, 200
        pages_to_process_list = [page_num]
    else:
        pages_to_process_list = list(range(min(total_pages, max_pages)))

    # 3) Extract metadata
    meta = extract_metadata(file_label)

    # 4) OCR each page
    results = []
    for pg in pages_to_process_list:
        # Adaptive DPI
        png_bytes_page = None
        for dpi in [200, 150, 100]:
            try:
                png_result = pdf_bytes_to_png(pdf_bytes, pg, dpi=dpi)
                if png_result and png_result[0]:
                    png_bytes_page = png_result[0]
                    break
            except Exception:
                continue

        if not png_bytes_page:
            continue

        ocr_result = ocr_page(png_bytes_page, GEMINI_API_KEY,
                              meta=meta, page_num=pg,
                              total_pages=total_pages)
        if not ocr_result:
            continue

        # Build output record
        record = ocr_result.get('result', {})
        # Always override with file metadata (ground truth from file path)
        if meta.get('province'):
            record['province'] = meta['province']
        if meta.get('constituency'):
            record['constituency'] = meta['constituency']
        if meta.get('vote_type'):
            record['vote_type'] = meta['vote_type']

        output = {
            "file": file_label,
            "page": pg + 1,
            "total_pages": total_pages,
            "drive_file_id": file_id,
            "model": ocr_result.get('model'),
            "model_variant": ocr_result.get('model_variant'),
            **record,
        }
        results.append(output)

    # 5) Save to Cloud Storage
    # Single page mode: save as {province}/{file_id}_p{page}.json
    # Full mode: save as {province}/{file_id}.json
    if page_num is not None:
        blob_path = f"{province}/{file_id}_p{page_num}.json"
    else:
        blob_path = f"{province}/{file_id}.json"
    save_to_gcs(GCS_BUCKET, blob_path, results)

    return {
        "status": "ok",
        "file_id": file_id,
        "file_label": file_label,
        "pages_processed": len(results),
        "total_pages": total_pages,
        "blob_path": blob_path,
    }, 200
