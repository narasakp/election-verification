#!/usr/bin/env python3
"""Quick analysis of current review_data.json state."""
import json, os
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), '..', 'review-app', 'public', 'data', 'review_data.json')

rd = json.load(open(DATA, 'r', encoding='utf-8'))
print(f"=== review_data.json ===")
print(f"Total items: {len(rd)}")
print(f"File size: {os.path.getsize(DATA)/1024/1024:.1f} MB")

# By province
provs = Counter(i.get('province','?') for i in rd)
print(f"\nBy province:")
for p, c in provs.most_common():
    print(f"  {p}: {c}")

# By vote_type
vt = Counter(i.get('vote_type','?') for i in rd)
print(f"\nBy vote_type:")
for v, c in vt.most_common():
    print(f"  {v}: {c}")

# Candidate counts for each vote_type
for vote_type in vt:
    items = [i for i in rd if i.get('vote_type') == vote_type]
    cand_counts = Counter(len(i.get('candidates', [])) for i in items)
    print(f"\n{vote_type} - candidate count distribution:")
    for n, cnt in cand_counts.most_common(10):
        print(f"  n={n}: {cnt} records")

# Check n=33 problem in source OCR files
print("\n=== Source OCR files ===")
for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    fpath = os.path.join(os.path.dirname(__file__), '..', 'data', fname)
    if os.path.exists(fpath):
        ocr = json.load(open(fpath, 'r', encoding='utf-8'))
        print(f"\n{fname}: {len(ocr)} records")
        bl = [r for r in ocr if r.get('vote_type') in ['บัญชีรายชื่อ', 'party_list']]
        if bl:
            bl_cands = Counter(len(r.get('candidates', [])) for r in bl)
            print(f"  บัญชีรายชื่อ: {len(bl)} records")
            for n, cnt in bl_cands.most_common(10):
                print(f"    n={n}: {cnt}")

# Check Phase 44 re-OCR status
reocr_log = os.path.join(os.path.dirname(__file__), '..', '_reocr_n33.log')
if os.path.exists(reocr_log):
    print(f"\n_reocr_n33.log exists ({os.path.getsize(reocr_log)} bytes)")
else:
    print(f"\n_reocr_n33.log: NOT FOUND")

targets = os.path.join(os.path.dirname(__file__), '..', 'data', '_reocr_n33_targets.json')
if os.path.exists(targets):
    t = json.load(open(targets, 'r', encoding='utf-8'))
    print(f"_reocr_n33_targets.json: {len(t)} targets")
else:
    print(f"_reocr_n33_targets.json: NOT FOUND")

# Check no_data / no_candidates
no_cands = [i for i in rd if not i.get('candidates')]
print(f"\nRecords with no candidates: {len(no_cands)}")
low_conf = [i for i in rd if i.get('confidence') == 'low']
print(f"Low confidence: {len(low_conf)}")
