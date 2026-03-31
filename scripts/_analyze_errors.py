# -*- coding: utf-8 -*-
"""Analyze dispatch error logs to classify and count error types."""
import json, os
from collections import Counter, defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

for prov in ['tak', 'phetchabun']:
    err_path = os.path.join(DATA, f'dispatch_missing_errors_{prov}.json')
    if not os.path.exists(err_path):
        print(f"\n{prov}: no error log")
        continue
    
    errors = json.load(open(err_path, 'r', encoding='utf-8'))
    print(f"\n{'='*60}")
    print(f"  {prov.upper()} — {len(errors)} errors")
    print(f"{'='*60}")
    
    # Classify by error type
    types = Counter()
    pdf_fail_files = set()
    for e in errors:
        msg = e.get('error', '') or e.get('response', '') or str(e)
        if 'PDF download failed' in msg:
            types['PDF download failed (502)'] += 1
            pdf_fail_files.add(e.get('file_id', ''))
        elif '503' in msg or 'Service Unavailable' in msg:
            types['Service Unavailable (503)'] += 1
        elif '429' in msg or 'rate' in msg.lower():
            types['Rate limited (429)'] += 1
        else:
            types[msg[:60]] += 1
    
    for t, cnt in types.most_common():
        print(f"  {cnt:5d}  {t}")
    
    if pdf_fail_files:
        print(f"\n  Unique PDFs with download failure: {len(pdf_fail_files)}")
    
    # Count 503 errors that are retryable
    retryable = sum(1 for e in errors if '503' in str(e.get('error', '')) or 'Service Unavailable' in str(e.get('error', '') or e.get('response', '')))
    pdf_fails = sum(1 for e in errors if 'PDF download failed' in str(e.get('error', '') or e.get('response', '')))
    print(f"\n  Retryable (503):       {retryable}")
    print(f"  PDF download failed:   {pdf_fails}")
    print(f"  Other:                 {len(errors) - retryable - pdf_fails}")

print(f"\n{'='*60}")
print("DONE")
