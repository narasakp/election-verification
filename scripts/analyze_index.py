#!/usr/bin/env python3
"""Analyze the rebuilt ss518_index.json for failure stats."""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
idx = json.load(open(os.path.join(DATA_DIR, 'ss518_index.json'), 'r', encoding='utf-8'))

print(f"Provinces: {idx['completed']}")
print(f"Total PDFs: {idx['total_pdfs']}")

fail_provs = []
for p in idx['provinces']:
    f = p.get('failed', 0)
    if f > 0:
        fail_provs.append((p['slug'], f, p.get('pdf_count', 0), p.get('downloaded', 0)))

fail_provs.sort(key=lambda x: -x[1])
total_fail = sum(x[1] for x in fail_provs)
total_dl = sum(p.get('downloaded', 0) for p in idx['provinces'])

print(f"Total downloaded: {total_dl}")
print(f"Total failed: {total_fail}")
print(f"Provinces with failures: {len(fail_provs)}")
print()
for s, f, t, d in fail_provs:
    print(f"  {s:30s} failed={f:3d}/{t:3d}  downloaded={d}")
