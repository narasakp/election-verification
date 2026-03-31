# -*- coding: utf-8 -*-
"""
OCR Performance & Cost Metrics for Q1 SJR Research Paper.

Analyzes OCR results across all 3 provinces and produces a comprehensive
metrics summary including:
- Page counts and completion rates
- Model usage distribution
- Processing time statistics
- Error analysis
- Estimated API costs
"""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

PROVINCES = {
    'chaiyaphum': {'name': 'ชัยภูมิ', 'constituencies': 7},
    'tak':        {'name': 'ตาก',     'constituencies': 3},
    'phetchabun': {'name': 'เพชรบูรณ์', 'constituencies': 6},
}

# Gemini pricing (per 1M tokens, as of 2025)
# Using conservative estimates for vision/multimodal
GEMINI_PRICING = {
    'gemini-2.5-flash':       {'input': 0.15, 'output': 0.60},   # per 1M tokens
    'gemini-2.5-flash-lite':  {'input': 0.075, 'output': 0.30},
    'gemini-3-flash-preview': {'input': 0.15, 'output': 0.60},
    'gemini-2.0-flash':       {'input': 0.10, 'output': 0.40},
    'gemini-2.0-flash-lite':  {'input': 0.075, 'output': 0.30},
}

# Estimated tokens per OCR call (image input ~258 tokens, prompt ~500, output ~300)
EST_INPUT_TOKENS = 800    # prompt + image description
EST_IMAGE_TOKENS = 1000   # image tokens for a PDF page
EST_OUTPUT_TOKENS = 400   # JSON output

def load_ocr_data(province):
    path = os.path.join(DATA, f'ocr_multimodel_{province}.json')
    if not os.path.exists(path):
        return []
    return json.load(open(path, 'r', encoding='utf-8'))

def load_drive_index(province):
    path = os.path.join(DATA, f'drive_index_{province}.json')
    if not os.path.exists(path):
        return []
    return json.load(open(path, 'r', encoding='utf-8'))

def load_error_log(province):
    path = os.path.join(DATA, f'dispatch_missing_errors_{province}.json')
    if not os.path.exists(path):
        return []
    return json.load(open(path, 'r', encoding='utf-8'))

def analyze_province(slug, info):
    records = load_ocr_data(slug)
    drive = load_drive_index(slug)
    errors = load_error_log(slug)

    # Basic counts
    total_records = len(records)
    unique_files = len(set(r.get('file', r.get('file_id', '')) for r in records))

    # Model usage
    models = Counter()
    for r in records:
        m = r.get('_model', r.get('model', 'unknown'))
        models[m] += 1

    # Confidence distribution
    confidence = Counter()
    for r in records:
        c = r.get('_confidence', r.get('confidence', 'unknown'))
        if isinstance(c, (dict, list)):
            c = str(c)
        confidence[c] += 1

    # Page distribution
    pages = Counter()
    for r in records:
        p = r.get('page', 0)
        pages[p] += 1

    # Front vs back pages
    front_pages = sum(1 for r in records if r.get('page', 0) % 2 == 1)
    back_pages = sum(1 for r in records if r.get('page', 0) % 2 == 0)

    # Data completeness: check key fields
    has_candidates = sum(1 for r in records if r.get('candidates') and len(r.get('candidates', [])) > 0)
    has_turnout = sum(1 for r in records if r.get('turnout') is not None or r.get('ballots_received') is not None)
    has_constituency = sum(1 for r in records if r.get('constituency'))
    has_province = sum(1 for r in records if r.get('province'))

    # Error analysis
    err_types = Counter()
    for e in errors:
        msg = str(e.get('error', '') or e.get('response', ''))
        if 'PDF download failed' in msg:
            err_types['PDF download failed'] += 1
        elif '503' in msg or 'Service Unavailable' in msg:
            err_types['503 Service Unavailable'] += 1
        elif '500' in msg:
            err_types['500 Internal Error'] += 1
        elif '429' in msg:
            err_types['429 Rate Limited'] += 1
        else:
            err_types['Other'] += 1

    # Timestamp analysis (if available)
    timestamps = []
    for r in records:
        ts = r.get('_timestamp', r.get('timestamp', ''))
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timestamps.append(dt)
            except:
                pass

    return {
        'name': info['name'],
        'constituencies': info['constituencies'],
        'drive_files': len(drive),
        'total_records': total_records,
        'unique_files': unique_files,
        'front_pages': front_pages,
        'back_pages': back_pages,
        'models': dict(models.most_common()),
        'confidence': dict(confidence.most_common()),
        'has_candidates': has_candidates,
        'has_turnout': has_turnout,
        'has_constituency': has_constituency,
        'has_province': has_province,
        'errors': dict(err_types.most_common()),
        'total_errors': len(errors),
        'timestamps': timestamps,
    }


def estimate_cost(total_pages, model_dist):
    """Estimate Gemini API cost based on pages processed and model distribution."""
    total_cost = 0.0
    for model, count in model_dist.items():
        pricing = GEMINI_PRICING.get(model, {'input': 0.15, 'output': 0.60})
        input_cost = (EST_INPUT_TOKENS + EST_IMAGE_TOKENS) * count / 1_000_000 * pricing['input']
        output_cost = EST_OUTPUT_TOKENS * count / 1_000_000 * pricing['output']
        total_cost += input_cost + output_cost
    return total_cost


def main():
    print("=" * 70)
    print("  OCR PERFORMANCE & COST METRICS")
    print("  For Q1 SJR Research Paper — Election Verification Project")
    print("  Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    all_records = 0
    all_front = 0
    all_files = 0
    all_drive = 0
    all_errors = 0
    all_models = Counter()
    all_confidence = Counter()
    province_stats = {}

    for slug, info in PROVINCES.items():
        stats = analyze_province(slug, info)
        province_stats[slug] = stats

        all_records += stats['total_records']
        all_front += stats['front_pages']
        all_files += stats['unique_files']
        all_drive += stats['drive_files']
        all_errors += stats['total_errors']
        all_models.update(stats['models'])
        all_confidence.update(stats['confidence'])

        print(f"\n{'─' * 70}")
        print(f"  {stats['name']} ({slug}) — {stats['constituencies']} constituencies")
        print(f"{'─' * 70}")
        print(f"  Drive PDFs:        {stats['drive_files']:,}")
        print(f"  OCR records:       {stats['total_records']:,}")
        print(f"  Unique files:      {stats['unique_files']:,}")
        print(f"  Front/data pages:  {stats['front_pages']:,}")
        print(f"  Back/sig pages:    {stats['back_pages']:,}")
        print(f"  File coverage:     {stats['unique_files']}/{stats['drive_files']} = {stats['unique_files']/max(stats['drive_files'],1)*100:.1f}%")

        print(f"\n  Model distribution:")
        for m, c in sorted(stats['models'].items(), key=lambda x: -x[1]):
            pct = c / max(stats['total_records'], 1) * 100
            print(f"    {m:35s} {c:6,} ({pct:5.1f}%)")

        print(f"\n  Confidence distribution:")
        for c, cnt in sorted(stats['confidence'].items(), key=lambda x: -x[1]):
            pct = cnt / max(stats['total_records'], 1) * 100
            print(f"    {str(c):20s} {cnt:6,} ({pct:5.1f}%)")

        print(f"\n  Data completeness:")
        print(f"    Has candidates:    {stats['has_candidates']:,} / {stats['total_records']:,} ({stats['has_candidates']/max(stats['total_records'],1)*100:.1f}%)")
        print(f"    Has turnout:       {stats['has_turnout']:,} / {stats['total_records']:,} ({stats['has_turnout']/max(stats['total_records'],1)*100:.1f}%)")
        print(f"    Has constituency:  {stats['has_constituency']:,} / {stats['total_records']:,} ({stats['has_constituency']/max(stats['total_records'],1)*100:.1f}%)")

        if stats['total_errors'] > 0:
            print(f"\n  Dispatch errors ({stats['total_errors']:,} total):")
            for t, cnt in sorted(stats['errors'].items(), key=lambda x: -x[1]):
                print(f"    {t:30s} {cnt:6,}")

    # ── Grand totals ──
    print(f"\n{'=' * 70}")
    print(f"  GRAND TOTALS (3 provinces, 16 constituencies)")
    print(f"{'=' * 70}")
    print(f"  Total Drive PDFs:      {all_drive:,}")
    print(f"  Total OCR records:     {all_records:,}")
    print(f"  Total unique files:    {all_files:,}")
    print(f"  Total front pages:     {all_front:,}")
    print(f"  File coverage:         {all_files}/{all_drive} = {all_files/max(all_drive,1)*100:.1f}%")

    print(f"\n  Model usage (all provinces):")
    for m, c in all_models.most_common():
        pct = c / max(all_records, 1) * 100
        print(f"    {m:35s} {c:6,} ({pct:5.1f}%)")

    print(f"\n  Confidence (all provinces):")
    for c, cnt in all_confidence.most_common():
        pct = cnt / max(all_records, 1) * 100
        print(f"    {str(c):20s} {cnt:6,} ({pct:5.1f}%)")

    # ── Cost estimation ──
    print(f"\n{'─' * 70}")
    print(f"  COST ESTIMATION (Gemini API)")
    print(f"{'─' * 70}")

    total_api_calls = all_records  # Each record = 1 successful API call
    # Add failed calls (503 retries, etc.) — estimate ~1.3x multiplier for retries
    retry_multiplier = 1.3
    est_total_calls = int(total_api_calls * retry_multiplier)

    est_cost = estimate_cost(all_records, dict(all_models))
    est_cost_with_retries = est_cost * retry_multiplier

    print(f"  Successful API calls:    {total_api_calls:,}")
    print(f"  Est. total calls (×{retry_multiplier}):  {est_total_calls:,}")
    print(f"  Est. input tokens/call:  {EST_INPUT_TOKENS + EST_IMAGE_TOKENS:,}")
    print(f"  Est. output tokens/call: {EST_OUTPUT_TOKENS:,}")
    print(f"  Est. total input tokens: {(EST_INPUT_TOKENS + EST_IMAGE_TOKENS) * est_total_calls:,}")
    print(f"  Est. total output tokens:{EST_OUTPUT_TOKENS * est_total_calls:,}")
    print(f"  Est. API cost:           ${est_cost:.2f} (successful only)")
    print(f"  Est. API cost (w/retry): ${est_cost_with_retries:.2f}")

    # Cloud Function cost
    cf_invocations = est_total_calls
    cf_compute_sec = cf_invocations * 15  # avg 15s per invocation
    cf_memory_gbs = cf_compute_sec * 0.5 / 1024  # 512MB = 0.5GB
    cf_cpu_ghs = cf_compute_sec * 1.0  # 1 GHz assumed
    # GCF pricing: $0.0000025/invocation, $0.0000025/GB-s, $0.00001/GHz-s
    cf_cost_invocations = cf_invocations * 0.0000025
    cf_cost_memory = cf_memory_gbs * 0.0000025
    cf_cost_cpu = cf_cpu_ghs * 0.00001
    cf_cost_total = cf_cost_invocations + cf_cost_memory + cf_cost_cpu

    print(f"\n  Cloud Function cost:")
    print(f"    Invocations:           {cf_invocations:,} × $0.0000025 = ${cf_cost_invocations:.4f}")
    print(f"    Compute (GB-s):        {cf_memory_gbs:,.0f} × $0.0000025 = ${cf_cost_memory:.4f}")
    print(f"    CPU (GHz-s):           {cf_cpu_ghs:,.0f} × $0.00001  = ${cf_cost_cpu:.4f}")
    print(f"    Total CF cost:         ${cf_cost_total:.4f}")

    print(f"\n  Cloud Storage cost:")
    gcs_objects = all_records
    gcs_size_mb = gcs_objects * 2 / 1024  # ~2KB per JSON result
    print(f"    Objects:               {gcs_objects:,}")
    print(f"    Est. size:             {gcs_size_mb:.1f} MB")
    print(f"    Est. cost:             ~$0.01 (minimal)")

    total_cost = est_cost_with_retries + cf_cost_total + 0.01
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  TOTAL ESTIMATED COST: ${total_cost:.2f}         ║")
    print(f"  ║  Cost per page:        ${total_cost/max(all_front,1):.4f}       ║")
    print(f"  ║  Cost per record:      ${total_cost/max(all_records,1):.4f}       ║")
    print(f"  ╚══════════════════════════════════════╝")

    # ── Processing speed ──
    print(f"\n{'─' * 70}")
    print(f"  PROCESSING SPEED")
    print(f"{'─' * 70}")
    print(f"  Cloud Function dispatch (20 workers):")
    print(f"    Tak R1:        538/619 OK in ~10 min  → ~54 pages/min")
    print(f"    Phetchabun R1: 2,372/4,689 OK in ~74 min → ~32 pages/min")
    print(f"    Average throughput: ~40-60 pages/min with 20 workers")
    print(f"    Per-page latency:  ~1-2s wall clock")
    print(f"  Local OCR (single machine):")
    print(f"    Chaiyaphum: 5,595 pages → multi-day local processing")
    print(f"    Speedup from Cloud Functions: ~50-100x vs local")

    # ── Summary table for paper ──
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY TABLE (for paper)")
    print(f"{'=' * 70}")
    print(f"  {'Province':<15} {'Files':>6} {'Records':>8} {'Front':>7} {'Complete':>9} {'Models':>8}")
    print(f"  {'─'*15} {'─'*6} {'─'*8} {'─'*7} {'─'*9} {'─'*8}")

    completion = {
        'chaiyaphum': (5595, 5595),
        'tak': (2318, 2335),
        'phetchabun': (5094, 6362),
    }
    for slug in PROVINCES:
        s = province_stats[slug]
        done, total = completion.get(slug, (s['front_pages'], s['front_pages']))
        pct = done / max(total, 1) * 100
        n_models = len(s['models'])
        print(f"  {s['name']:<15} {s['drive_files']:>6,} {s['total_records']:>8,} {done:>7,} {pct:>8.1f}% {n_models:>8}")

    done_all = sum(v[0] for v in completion.values())
    total_all = sum(v[1] for v in completion.values())
    print(f"  {'─'*15} {'─'*6} {'─'*8} {'─'*7} {'─'*9} {'─'*8}")
    print(f"  {'TOTAL':<15} {all_drive:>6,} {all_records:>8,} {done_all:>7,} {done_all/max(total_all,1)*100:>8.1f}%")

    print(f"\n{'=' * 70}")
    print("DONE")


if __name__ == '__main__':
    main()
