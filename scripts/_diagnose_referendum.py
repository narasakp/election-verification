#!/usr/bin/env python3
"""Diagnose ประชามติ (referendum) items — real or misclassified?"""
import json, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))

# Find all vote types
vt_counts = Counter(r.get('vote_type', '?') for r in d)
print("=== Vote type distribution ===")
for vt, cnt in vt_counts.most_common():
    print(f"  {vt}: {cnt} ({cnt/len(d)*100:.1f}%)")

# Focus on ประชามติ
ref_items = [r for r in d if 'ประชามติ' in (r.get('vote_type') or '')]
print(f"\n=== ประชามติ items: {len(ref_items)} ===")

# Province breakdown
prov_counts = Counter(r.get('province', '?') for r in ref_items)
print("\nBy province:")
for p, c in prov_counts.most_common():
    print(f"  {p}: {c}")

# Constituency breakdown
const_counts = Counter(r.get('constituency', '?') for r in ref_items)
print("\nBy constituency:")
for c, cnt in sorted(const_counts.items()):
    print(f"  เขต {c}: {cnt}")

# Check filenames for clues
print("\n=== Sample filenames (first 20) ===")
file_samples = Counter()
for r in ref_items:
    f = r.get('file', '?')
    # Get just the filename
    fname = f.replace('\\', '/').split('/')[-1] if '/' in f.replace('\\', '/') else f
    file_samples[fname] += 1

for fname, cnt in file_samples.most_common(20):
    print(f"  [{cnt}] {fname}")

# Check source file paths for patterns
print("\n=== Sample full paths (first 10 unique patterns) ===")
seen_patterns = set()
for r in ref_items[:50]:
    f = r.get('file', '?')
    parts = f.replace('\\', '/').split('/')
    # Get last 3-4 path segments
    pattern = '/'.join(parts[-4:]) if len(parts) >= 4 else f
    if pattern not in seen_patterns:
        seen_patterns.add(pattern)
        print(f"  {pattern}")
    if len(seen_patterns) >= 15:
        break

# Check if they have candidates (referendum shouldn't have named candidates)
has_cands = sum(1 for r in ref_items if r.get('candidates'))
avg_cands = 0
if has_cands:
    cand_counts = [len(r.get('candidates', [])) for r in ref_items if r.get('candidates')]
    avg_cands = sum(cand_counts) / len(cand_counts) if cand_counts else 0

print(f"\n=== Data characteristics ===")
print(f"Has candidates: {has_cands} / {len(ref_items)} ({has_cands/len(ref_items)*100:.1f}%)")
if has_cands:
    cand_dist = Counter(len(r.get('candidates', [])) for r in ref_items if r.get('candidates'))
    print(f"  Candidate count distribution: {dict(cand_dist.most_common(10))}")
    print(f"  Avg candidates: {avg_cands:.1f}")

# Sample candidate names
print("\n=== Sample candidate names (from first 5 items with candidates) ===")
cnt = 0
for r in ref_items:
    cands = r.get('candidates', [])
    if cands:
        print(f"  stn={r.get('station_no','?')} file=...{r.get('file','')[-60:]}")
        for c in cands[:5]:
            print(f"    #{c.get('number','?')} {c.get('name','?')} votes={c.get('votes','?')}")
        if len(cands) > 5:
            print(f"    ... +{len(cands)-5} more")
        cnt += 1
        if cnt >= 5:
            break

# Check ballot data
has_ballot = sum(1 for r in ref_items if r.get('registered_voters') is not None or r.get('turnout') is not None)
print(f"\nHas ballot data: {has_ballot} / {len(ref_items)} ({has_ballot/len(ref_items)*100:.1f}%)")

# Check OCR text for clues
print("\n=== OCR text samples (first 5 items, first 200 chars) ===")
cnt = 0
for r in ref_items:
    txt = r.get('ocr_text', '')
    if txt:
        print(f"  [{r.get('station_no','?')}] {txt[:200]}")
        cnt += 1
        if cnt >= 5:
            break
