#!/usr/bin/env python3
"""Check how many items still have multi-page PDFs after split."""
import json, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))

total = len(d)
split = sum(1 for r in d if r.get('_orig_total_pages'))
still_multi = sum(1 for r in d if (r.get('total_pages') or 1) > 2)
no_pdf = sum(1 for r in d if not r.get('pdf_url'))

print(f"Total items: {total}")
print(f"Split to single-page: {split}")
print(f"Still multi-page (tp>2): {still_multi}")
print(f"No pdf_url: {no_pdf}")

if still_multi > 0:
    tp_counts = Counter((r.get('total_pages') or 1) for r in d if (r.get('total_pages') or 1) > 2)
    print(f"\nRemaining multi-page distribution:")
    for tp, cnt in sorted(tp_counts.items()):
        print(f"  tp={tp}: {cnt}")
    
    # Province breakdown
    prov_counts = Counter(r.get('province', '?') for r in d if (r.get('total_pages') or 1) > 2)
    print(f"\nBy province:")
    for p, c in prov_counts.most_common():
        print(f"  {p}: {c}")
