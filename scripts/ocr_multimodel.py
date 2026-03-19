# -*- coding: utf-8 -*-
"""
Multi-model OCR for สส.5/18 election forms.

Pipeline:
  PDF (from Drive) → PNG (in memory)
    ├─→ Gemini Flash 2.0:  image + prompt → structured JSON
    ├─→ Cloud Vision API:  image → text → parse → JSON
    └─→ Claude Sonnet:     image + prompt → structured JSON
         │
         ▼
    Cross-validate: compare all models → pick consensus
         │
         ▼
    Final structured JSON + confidence scores

Usage:
  python scripts/ocr_multimodel.py --drive --province "ตาก" --limit 5
  python scripts/ocr_multimodel.py --drive --province "ชัยภูมิ" --all --resume

Requires .env:
  GOOGLE_CLOUD_API_KEY=...   (Cloud Vision)
  GEMINI_API_KEY=...         (Gemini Flash)
  ANTHROPIC_API_KEY=...      (Claude, optional)
"""
import argparse
import base64
import json
import os
import re
import sys
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

sys.path.insert(0, SCRIPT_DIR)
from ocr_cloud_vision import (
    get_api_key, pdf_bytes_to_png, download_pdf_from_drive,
    extract_metadata_from_drive_entry, call_vision_api,
    parse_ss518_with_layout, PROVINCE_SLUGS
)
from ocr_preprocess import preprocess_png
from ocr_postprocess import auto_correct_ballots

# ── Structured prompt for LLM-based OCR ──────────────────────────────

EXTRACTION_PROMPT = """คุณเป็นผู้เชี่ยวชาญอ่านเอกสารเลือกตั้งไทย (แบบฟอร์ม สส.5/18)
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


# ── API Key Loading ──────────────────────────────────────────────────

def load_api_keys():
    """Load all API keys from env or .env file."""
    keys = {}
    env_path = os.path.join(PROJECT_ROOT, '.env')

    # Read from .env
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")

    # Merge with os.environ (env vars take precedence)
    for name in ['GOOGLE_CLOUD_API_KEY', 'GEMINI_API_KEY', 'ANTHROPIC_API_KEY']:
        val = os.environ.get(name) or env_vars.get(name)
        if val:
            keys[name] = val

    return keys


# ── JSON Repair ───────────────────────────────────────────────────────

def _repair_json(text):
    """Attempt to repair common malformed JSON from LLM responses."""
    if not text or not text.strip():
        return None
    # Extract the outermost { ... } or { ... (truncated)
    m = re.search(r'\{', text)
    if not m:
        return None
    s = text[m.start():]
    # Remove trailing garbage after last }
    last_brace = s.rfind('}')
    if last_brace >= 0:
        s = s[:last_brace + 1]
    else:
        # No closing brace — truncated response; close open structures
        pass
    # Fix trailing commas before } or ]
    s = re.sub(r',\s*([}\]])', r'\1', s)
    # Try parsing as-is first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Truncated string: find last unmatched quote, close it
    # Strategy: progressively close open structures
    repaired = s.rstrip()
    # Remove trailing incomplete key-value (e.g. "key": "val  or  "key": 12)
    repaired = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"{}\[\]]*$', '', repaired)
    # Close unclosed strings
    quote_count = repaired.count('"') - repaired.count('\\"')
    if quote_count % 2 != 0:
        repaired += '"'
    # Fix trailing commas again
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    # Count and close unclosed brackets
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    # Remove trailing comma before we close
    repaired = repaired.rstrip().rstrip(',')
    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    # Last resort: strip candidates array and close
    cand_match = re.search(r'"candidates"\s*:\s*\[', repaired)
    if cand_match:
        before_cands = repaired[:cand_match.start()].rstrip().rstrip(',')
        before_cands += '"candidates": []}'
        before_cands = re.sub(r',\s*([}\]])', r'\1', before_cands)
        try:
            return json.loads(before_cands)
        except json.JSONDecodeError:
            pass
    return None


# ── Model 1: Gemini Flash (multi-model fallback) ─────────────────────

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
]


def _call_gemini_once(png_b64, api_key, model, temperature):
    """Single attempt to call a Gemini model.
    Returns: dict on success, 'retry' on 503/429, None on hard failure."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": EXTRACTION_PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": png_b64}}
            ]
        }],
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
        return {'model': 'gemini', 'model_variant': model, 'result': result, 'raw': text}

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        if 'text' in dir():
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    result = json.loads(match.group())
                    return {'model': 'gemini', 'model_variant': model, 'result': result, 'raw': text}
                except json.JSONDecodeError:
                    pass
            repaired = _repair_json(text)
            if repaired:
                print(f"    [{model}] JSON repaired")
                return {'model': 'gemini', 'model_variant': model, 'result': repaired, 'raw': text}
        print(f"    [{model}] parse error: {e}")
        return None

    except requests.RequestException as e:
        print(f"    [{model}] API error: {e}")
        return 'retry'


def ocr_gemini(png_bytes, api_key, model=None, temperature=0.0):
    """Send image to Gemini with multi-model fallback + mega-retry.
    Strategy: cycle through all models quickly (no wait per model on 503),
    if all fail → wait 30s → retry whole cycle. Up to 4 mega-retries."""
    b64 = base64.b64encode(png_bytes).decode('utf-8')
    models_to_try = [model] if model else GEMINI_MODELS

    for mega in range(4):
        if mega > 0:
            wait = 30 * mega
            print(f"    [all models 503] waiting {wait}s (cycle {mega+1}/4)...")
            time.sleep(wait)

        for m in models_to_try:
            result = _call_gemini_once(b64, api_key, m, temperature)
            if result == 'retry':
                continue  # try next model immediately
            if result is not None:
                if m != models_to_try[0]:
                    print(f"    [fallback→{m}]", end='')
                return result
            # Hard failure (parse error etc.) — still try next model
            continue

    return None


# ── Model 2: Cloud Vision + Parser ───────────────────────────────────

def ocr_cloud_vision(png_bytes, api_key):
    """Send image to Cloud Vision API and parse with rule-based parser."""
    try:
        resp = call_vision_api(png_bytes, api_key)
        if not resp:
            return None

        parsed = parse_ss518_with_layout(resp)
        return {'model': 'cloud_vision', 'result': parsed, 'raw': resp}

    except Exception as e:
        print(f"    Cloud Vision error: {e}")
        return None


# ── Model 3: Claude ──────────────────────────────────────────────────

def _png_to_jpeg_for_claude(png_bytes, quality=85):
    """Convert PNG to JPEG for Claude API (5MB base64 limit ≈ 3.7MB raw).
    JPEG is typically 5-10x smaller than PNG for scanned documents."""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(png_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return png_bytes, "image/png"
        _, encoded = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        jpg_bytes = encoded.tobytes()
        # If still too large (>3.7MB raw → >5MB base64), resize
        if len(jpg_bytes) > 3_700_000:
            scale = (3_700_000 / len(jpg_bytes)) ** 0.5
            new_w = int(img.shape[1] * scale)
            new_h = int(img.shape[0] * scale)
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            _, encoded = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
            jpg_bytes = encoded.tobytes()
        return jpg_bytes, "image/jpeg"
    except Exception:
        return png_bytes, "image/png"


def ocr_claude(png_bytes, api_key, model="claude-sonnet-4-20250514"):
    """Send image to Claude and get structured JSON."""
    url = "https://api.anthropic.com/v1/messages"

    # Convert to JPEG for size (Claude has 5MB base64 limit)
    img_bytes, mime_type = _png_to_jpeg_for_claude(png_bytes)
    b64 = base64.b64encode(img_bytes).decode('utf-8')

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": EXTRACTION_PROMPT},
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": b64,
                }}
            ]
        }]
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=90)
            if resp.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"    Claude rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()

            text = data['content'][0]['text']
            # Extract JSON from response
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                return {'model': 'claude', 'result': result, 'raw': text}

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"    Claude parse error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
        except requests.RequestException as e:
            # Log response body for 400 errors
            body = ''
            if hasattr(e, 'response') and e.response is not None:
                try:
                    body = e.response.text[:200]
                except Exception:
                    pass
            print(f"    Claude API error (attempt {attempt+1}): {e} {body}")
            if attempt < 2:
                time.sleep(5)

    return None


# ── Cross-Validation ─────────────────────────────────────────────────

NUMERIC_FIELDS = [
    'registered_voters', 'turnout', 'ballots_received',
    'valid_ballots', 'invalid_ballots', 'no_vote_ballots',
    'remaining_ballots', 'total_votes', 'constituency', 'station_no',
]

TEXT_FIELDS = ['vote_type', 'province', 'district', 'sub_district']


def _safe_int(val):
    """Convert value to int, return None if not possible."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def cross_validate(model_results):
    """Compare results from multiple models, pick consensus values."""
    if not model_results:
        return None, {}

    # If only 1 model, return it directly
    if len(model_results) == 1:
        r = model_results[0]['result']
        conf = {f: 'single_model' for f in NUMERIC_FIELDS if r.get(f) is not None}
        return r, conf

    # Compare numeric fields across models
    final = {}
    confidence = {}

    for field in NUMERIC_FIELDS:
        values = {}
        for mr in model_results:
            v = _safe_int(mr['result'].get(field))
            if v is not None:
                values[mr['model']] = v

        if not values:
            final[field] = None
            continue

        # Count agreement
        val_counts = {}
        for model, v in values.items():
            val_counts.setdefault(v, []).append(model)

        # Pick value with most votes (majority)
        best_val, best_models = max(val_counts.items(), key=lambda x: len(x[1]))

        if len(best_models) >= 2:
            # 2+ models agree
            final[field] = best_val
            confidence[field] = f"high ({'+'.join(best_models)})"
        elif len(values) == 1:
            # Only 1 model has data
            final[field] = best_val
            confidence[field] = f"single ({best_models[0]})"
        else:
            # Models disagree — prefer Gemini > Claude > Cloud Vision
            priority = {'gemini': 3, 'claude': 2, 'cloud_vision': 1}
            best_model = max(values.keys(), key=lambda m: priority.get(m, 0))
            final[field] = values[best_model]
            all_vals = ', '.join(f"{m}={v}" for m, v in values.items())
            confidence[field] = f"disagree ({all_vals}) → {best_model}"

    # Text fields — prefer Gemini
    for field in TEXT_FIELDS:
        values = {}
        for mr in model_results:
            v = mr['result'].get(field)
            if v:
                values[mr['model']] = str(v).strip()
        if values:
            priority = {'gemini': 3, 'claude': 2, 'cloud_vision': 1}
            best_model = max(values.keys(), key=lambda m: priority.get(m, 0))
            final[field] = values[best_model]
        else:
            final[field] = None

    # Candidates — merge logic
    final['candidates'] = _merge_candidates(model_results)
    final['is_back_page'] = any(mr['result'].get('is_back_page') for mr in model_results)

    return final, confidence


def _merge_candidates(model_results):
    """Merge candidate lists from multiple models."""
    all_cands = {}  # number → list of (model, candidate_dict)

    for mr in model_results:
        cands = mr['result'].get('candidates', [])
        if not cands:
            continue
        for c in cands:
            num = _safe_int(c.get('number'))
            if num is None:
                continue
            all_cands.setdefault(num, []).append((mr['model'], c))

    merged = []
    for num in sorted(all_cands.keys()):
        entries = all_cands[num]

        # Pick name: prefer longest non-null
        names = [(m, c.get('name', '')) for m, c in entries if c.get('name')]
        name = max(names, key=lambda x: len(x[1]))[1] if names else None

        # Pick party: majority vote
        parties = [c.get('party', '') for _, c in entries if c.get('party')]
        party = max(set(parties), key=parties.count) if parties else None

        # Pick votes: majority or Gemini preference
        votes_by_model = {m: _safe_int(c.get('votes')) for m, c in entries if _safe_int(c.get('votes')) is not None}
        if votes_by_model:
            val_counts = {}
            for m, v in votes_by_model.items():
                val_counts.setdefault(v, []).append(m)
            best_val, _ = max(val_counts.items(), key=lambda x: len(x[1]))
            votes = best_val
        else:
            votes = None

        merged.append({
            'number': num,
            'name': name,
            'party': party,
            'votes': votes,
            'models_agree': len(set(votes_by_model.values())) <= 1 if votes_by_model else False,
        })

    return merged


# ── Process Single Page ──────────────────────────────────────────────

def process_page(png_bytes, keys, models_to_use, page_num, meta, file_label,
                 preprocess=True, self_consistency=0):
    """Process a single page with multiple models and cross-validate.
    
    Args:
        self_consistency: If > 0, run Gemini N extra times with temperature=0.3
                          for majority voting (self-consistency technique).
    """
    # Apply image preprocessing for better OCR accuracy
    if preprocess:
        png_bytes = preprocess_png(png_bytes, deskew=True, denoise=True,
                                   enhance_contrast=True, sharpen=True)
    results = []

    for model_name in models_to_use:
        if model_name == 'gemini' and 'GEMINI_API_KEY' in keys:
            # Primary Gemini call (temperature=0)
            r = ocr_gemini(png_bytes, keys['GEMINI_API_KEY'])
            if r:
                results.append(r)
                print(f"    [Gemini]", end='')
            
            # Self-consistency: extra Gemini calls with temperature=0.1
            for sc_i in range(self_consistency):
                r_sc = ocr_gemini(png_bytes, keys['GEMINI_API_KEY'], temperature=0.1)
                if r_sc:
                    r_sc['model'] = f'gemini_sc{sc_i+1}'
                    results.append(r_sc)
                    print(f" SC{sc_i+1}", end='')
                time.sleep(0.5)  # Brief pause between calls

        elif model_name == 'cloud_vision' and 'GOOGLE_CLOUD_API_KEY' in keys:
            r = ocr_cloud_vision(png_bytes, keys['GOOGLE_CLOUD_API_KEY'])
            if r:
                results.append(r)
                print(f"    [CloudVision]", end='')

        elif model_name == 'claude' and 'ANTHROPIC_API_KEY' in keys:
            r = ocr_claude(png_bytes, keys['ANTHROPIC_API_KEY'])
            if r:
                results.append(r)
                print(f"    [Claude]", end='')

    print()

    if not results:
        return None

    # Cross-validate
    final, confidence = cross_validate(results)

    # Merge with file metadata
    output = {
        'file': file_label,
        'page': page_num + 1,
        **meta,
        **final,
        '_confidence': confidence,
        '_models_used': [r['model'] for r in results],
        '_models_count': len(results),
    }

    # Apply mathematical auto-correction
    output, _ = auto_correct_ballots(output)

    return output


# ── Main Loop ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-model OCR สส.5/18")
    parser.add_argument("--drive", action="store_true", help="Stream from Google Drive")
    parser.add_argument("--province", required=True, help="Province name (Thai or slug)")
    parser.add_argument("--limit", type=int, help="Max files to process")
    parser.add_argument("--max-pages", type=int, default=3, help="Max pages per PDF")
    parser.add_argument("--resume", action="store_true", help="Skip already processed files")
    parser.add_argument("--all", action="store_true", help="Process all files")
    parser.add_argument("--models", default="gemini,cloud_vision",
                        help="Comma-separated models: gemini,cloud_vision,claude")
    parser.add_argument("--self-consistency", type=int, default=0,
                        help="Run Gemini N extra times with temp=0.3 for majority voting (e.g. 2)")
    args = parser.parse_args()

    # Resolve province
    province = args.province
    slug = PROVINCE_SLUGS.get(province) or province
    for prov_name, prov_slug in PROVINCE_SLUGS.items():
        if prov_slug == province:
            province = prov_name
            slug = prov_slug
            break

    # Load API keys
    keys = load_api_keys()
    models_to_use = [m.strip() for m in args.models.split(',')]

    print(f"[Province] {province} ({slug})")
    print(f"[Models] {', '.join(models_to_use)}")
    print("API Keys:")
    for k, v in keys.items():
        print(f"  {k}: {v[:12]}...")

    # Check required keys
    model_key_map = {
        'gemini': 'GEMINI_API_KEY',
        'cloud_vision': 'GOOGLE_CLOUD_API_KEY',
        'claude': 'ANTHROPIC_API_KEY',
    }
    active_models = []
    for m in models_to_use:
        required_key = model_key_map.get(m)
        if required_key and required_key in keys:
            active_models.append(m)
        else:
            print(f"  WARN: Skipping {m} (no {required_key})")
    models_to_use = active_models

    if not models_to_use:
        print("ERROR: No models available! Add API keys to .env")
        sys.exit(1)

    print(f"[OK] Active models: {', '.join(models_to_use)}\n")

    # Load Drive index
    index_path = os.path.join(DATA_DIR, f'drive_index_{slug}.json')
    if not os.path.exists(index_path):
        print(f"ERROR: Drive index not found: {index_path}")
        sys.exit(1)

    with open(index_path, 'r', encoding='utf-8') as f:
        drive_index = json.load(f)
    print(f"[Index] {len(drive_index)} PDFs")

    # Output file
    out_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    existing = []
    done_files = set()
    if args.resume and os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        done_files = set(r.get('file') for r in existing)
        print(f"[Resume] {len(existing)} items, {len(done_files)} files done")

    # Filter
    entries = [e for e in drive_index if e.get('name', '').lower().endswith('.pdf')]
    if not args.all:
        entries = entries[:args.limit or 5]
    def _file_label(e):
        p = e.get('path', '')
        n = e.get('name', '')
        return f"{p}/{n}" if p else n
    entries = [e for e in entries if _file_label(e) not in done_files]
    print(f"[Queue] Files to process: {len(entries)}\n")

    results = list(existing)
    api_calls = 0

    for idx, entry in enumerate(entries):
        # Use path/name to make file_label unique (path alone = directory)
        _path = entry.get('path', '')
        _name = entry.get('name', '')
        file_label = f"{_path}/{_name}" if _path else _name
        file_id = entry['file_id']
        meta = extract_metadata_from_drive_entry(entry)

        print(f"[{idx+1}/{len(entries)}] {file_label}")

        # Download PDF
        try:
            api_key = keys.get('GOOGLE_CLOUD_API_KEY', '')
            pdf_bytes = download_pdf_from_drive(file_id, api_key)
            if not pdf_bytes:
                print("  ERR: Download failed")
                continue
        except Exception as e:
            print(f"  ERR: Download error: {e}")
            continue

        # Count pages
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(doc)
            doc.close()
        except Exception:
            total_pages = 1

        max_p = min(total_pages, args.max_pages)
        # Adaptive DPI: lower for large PDFs to avoid memory errors
        base_dpi = 200 if total_pages > 20 else 300
        print(f"  Pages: {total_pages}, processing: {max_p}, dpi: {base_dpi}")

        for page_num in range(max_p):
            png_bytes_page = None
            for dpi in [base_dpi, 150, 100]:
                try:
                    png_result = pdf_bytes_to_png(pdf_bytes, page_num, dpi=dpi)
                    if png_result is not None and png_result[0] is not None:
                        png_bytes_page = png_result[0]
                        break
                except Exception as e:
                    if dpi == 100:
                        print(f"  p{page_num+1}: ERR {e}")
                    else:
                        print(f"  p{page_num+1}: DPI {dpi} failed, trying lower...")
            if png_bytes_page is None:
                print(f"  p{page_num+1}: ERR PNG conversion failed at all DPIs")
                continue

            # Rate limit guard for large PDFs
            if total_pages > 20 and page_num > 0:
                time.sleep(3)

            print(f"  p{page_num+1}:", end='')
            sc = getattr(args, 'self_consistency', 0)
            result = process_page(png_bytes_page, keys, models_to_use,
                                  page_num, meta, file_label,
                                  self_consistency=sc)
            api_calls += len(models_to_use) + sc

            if result:
                result['total_pages'] = total_pages
                result['drive_file_id'] = file_id
                result['drive_view_url'] = entry.get('view_url')
                results.append(result)

                # Summary
                station = result.get('station_no')
                voters = result.get('registered_voters')
                n_cands = len(result.get('candidates', []))
                total = result.get('total_votes')
                n_models = result.get('_models_count', 0)
                print(f"    → station={station} voters={voters} cands={n_cands} "
                      f"total={total} models={n_models}")

        # Save incrementally (every file to avoid data loss)
        if True:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    # Final save
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"=== Summary ===")
    print(f"{'='*60}")
    print(f"  API calls: ~{api_calls}")
    print(f"  Results: {len(results)} items")
    print(f"  Output: {out_path}")


if __name__ == '__main__':
    main()
