# -*- coding: utf-8 -*-
"""Analyze dispatch errors."""
import json
from collections import Counter

import os
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
errs = json.load(open(os.path.join(DATA_DIR, 'dispatch_missing_errors_chaiyaphum.json'), 'r', encoding='utf-8'))
print(f"Total errors: {len(errs)}")

c = Counter(e['error'][:50] for e in errs)
print("\nError types:")
for k, v in c.most_common(10):
    print(f"  {v:5d}  {k}")

# Show first few full errors
print("\nSample errors:")
for e in errs[:3]:
    print(f"  file: {e.get('file','')[-60:]}")
    print(f"  page: {e.get('page','')}")
    print(f"  error: {e.get('error','')[:100]}")
    print()
