#!/usr/bin/env python3
"""Analyze which fields contribute most to review_data.json file size."""
import json, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 
                     'review-app', 'public', 'data', 'review_data.json')
data = json.load(open(path, 'r', encoding='utf-8'))
total_size = os.path.getsize(path)
print(f"Total: {total_size/1024/1024:.2f} MB, {len(data)} items")

# Measure size contribution per field
field_sizes = {}
for item in data:
    for key, val in item.items():
        s = len(json.dumps(val, ensure_ascii=False))
        field_sizes[key] = field_sizes.get(key, 0) + s

print(f"\nField sizes (top 20):")
for k, v in sorted(field_sizes.items(), key=lambda x: -x[1])[:20]:
    pct = v / sum(field_sizes.values()) * 100
    print(f"  {k:30s} {v/1024/1024:6.2f} MB ({pct:5.1f}%)")

# Check ocr_text field
ocr_text_count = sum(1 for item in data if item.get('ocr_text'))
ocr_text_size = sum(len(item.get('ocr_text', '') or '') for item in data)
print(f"\nocr_text: {ocr_text_count} items, {ocr_text_size/1024/1024:.2f} MB")

# Check candidates detail
cand_sizes = []
for item in data:
    cs = json.dumps(item.get('candidates', []), ensure_ascii=False)
    cand_sizes.append(len(cs))
print(f"candidates: avg {sum(cand_sizes)/len(cand_sizes)/1024:.1f} KB/item, total {sum(cand_sizes)/1024/1024:.2f} MB")

# Check _boundary_fill placeholders
bf_count = sum(1 for item in data for c in (item.get('candidates') or []) if c.get('_boundary_fill'))
print(f"_boundary_fill candidates: {bf_count}")

# Check indent overhead
compact = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
print(f"\nCompact (no indent): {len(compact)/1024/1024:.2f} MB")
indent2 = json.dumps(data, ensure_ascii=False, indent=2)
print(f"Indent=2 (current):  {len(indent2)/1024/1024:.2f} MB")
print(f"Savings from compact: {(len(indent2)-len(compact))/1024/1024:.2f} MB")

# Check removable fields
removable = ['ocr_text', 'confidence', 'model', 'model_variant', '_source_type',
             'image_url', 'is_back_page']
for field in removable:
    size = sum(len(json.dumps(item.get(field), ensure_ascii=False)) for item in data if item.get(field) is not None)
    count = sum(1 for item in data if item.get(field) is not None)
    print(f"  remove '{field}': save {size/1024/1024:.2f} MB ({count} items)")
