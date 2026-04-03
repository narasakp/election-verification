#!/usr/bin/env python3
"""Diagnose why 986 groups produce n=56 instead of n=57."""
import json, os, sys
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

all_records = []
for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    data = json.load(open(os.path.join(DATA_DIR, fname), encoding='utf-8'))
    all_records.extend(data)

bl = [r for r in all_records if r.get('vote_type') == 'บัญชีรายชื่อ']

# Group by (file, station_no)
groups = defaultdict(list)
for r in bl:
    stn = r.get('ocr_station_no') or r.get('station_no')
    if stn:
        key = (r.get('file', ''), str(stn))
        groups[key].append(r)

# Find n=56 groups
n56_groups = []
for key, recs in groups.items():
    if len(recs) < 2:
        continue
    seen = set()
    for r in recs:
        for c in (r.get('candidates') or []):
            cno = c.get('number') or c.get('candidate_no')
            if cno:
                seen.add(cno)
    if len(seen) == 56:
        n56_groups.append((key, recs))

print(f"n=56 groups: {len(n56_groups)}")

# Which candidate number is missing?
missing_numbers = Counter()
for key, recs in n56_groups:
    seen = set()
    for r in recs:
        for c in (r.get('candidates') or []):
            cno = c.get('number') or c.get('candidate_no')
            if cno:
                seen.add(cno)
    for expected in range(1, 58):
        if expected not in seen:
            missing_numbers[expected] += 1

print(f"\nMissing candidate numbers (top 20):")
for num, cnt in missing_numbers.most_common(20):
    print(f"  #{num}: missing in {cnt} groups")

# Check: do records have candidates with number=None?
null_number_count = 0
null_has_votes = 0
sample_nulls = []
for key, recs in n56_groups[:50]:
    for r in recs:
        for c in (r.get('candidates') or []):
            cno = c.get('number') or c.get('candidate_no')
            if cno is None:
                null_number_count += 1
                if c.get('votes') is not None and c.get('votes') != 0:
                    null_has_votes += 1
                if len(sample_nulls) < 5:
                    sample_nulls.append(c)

print(f"\nCandidates with number=None in n=56 groups: {null_number_count}")
print(f"  Of those, with real votes: {null_has_votes}")
if sample_nulls:
    print(f"  Samples:")
    for c in sample_nulls:
        print(f"    {c}")

# Check: do pages have overlapping candidate numbers?
overlap_counts = Counter()
for key, recs in n56_groups[:200]:
    recs.sort(key=lambda r: r.get('page', 0) or 0)
    page_sets = []
    for r in recs:
        nums = set()
        for c in (r.get('candidates') or []):
            cno = c.get('number') or c.get('candidate_no')
            if cno:
                nums.add(cno)
        page_sets.append(nums)
    
    # Check pairwise overlap
    for i in range(len(page_sets)):
        for j in range(i+1, len(page_sets)):
            overlap = page_sets[i] & page_sets[j]
            if overlap:
                overlap_counts[len(overlap)] += 1

if overlap_counts:
    print(f"\nOverlapping candidate numbers between pages:")
    for sz, cnt in sorted(overlap_counts.items()):
        print(f"  {sz} overlapping numbers: {cnt} page pairs")

# Check page count distribution in n=56 groups
page_count_dist = Counter(len(recs) for _, recs in n56_groups)
print(f"\nPages per n=56 group: {dict(sorted(page_count_dist.items()))}")

# Check per-page candidate counts for n=56 groups
print(f"\nPer-page candidate counts in n=56 groups (first 10):")
for key, recs in n56_groups[:10]:
    recs.sort(key=lambda r: r.get('page', 0) or 0)
    pages = [r.get('page') for r in recs]
    ncands = [len(r.get('candidates', [])) for r in recs]
    reocr = [r.get('_reocr_n33', False) for r in recs]
    print(f"  pages={pages} cands={ncands} reocr={reocr}")
