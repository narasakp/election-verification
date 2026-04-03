#!/usr/bin/env python3
"""Diagnose why บัญชีรายชื่อ consolidation produces few n=57 records."""
import json, os, sys, re
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load all OCR data
all_records = []
for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    path = os.path.join(DATA_DIR, fname)
    data = json.load(open(path, encoding='utf-8'))
    all_records.extend(data)

# Filter to บัญชีรายชื่อ only
bl = [r for r in all_records if r.get('vote_type') == 'บัญชีรายชื่อ']
print(f"Total บัญชีรายชื่อ source records: {len(bl)}")

# Check station_no availability
has_stn = sum(1 for r in bl if r.get('ocr_station_no') or r.get('station_no'))
no_stn = len(bl) - has_stn
print(f"  With station_no: {has_stn}")
print(f"  Without station_no: {no_stn}")

# Group by (file, station_no, vote_type) — same as consolidation logic
groups_with_stn = defaultdict(list)
groups_no_stn = defaultdict(list)

for r in bl:
    stn = r.get('ocr_station_no') or r.get('station_no')
    if stn:
        key = (r.get('file', ''), str(stn))
        groups_with_stn[key].append(r)
    else:
        key = r.get('file', '')
        groups_no_stn[key].append(r)

# Analyze groups with station_no
print(f"\n=== Groups WITH station_no ===")
group_sizes = Counter(len(v) for v in groups_with_stn.values())
print(f"  Total groups: {len(groups_with_stn)}")
print(f"  Size distribution: {dict(sorted(group_sizes.items()))}")

# For groups of size 1 — why couldn't they find peers?
singles = [(k, v[0]) for k, v in groups_with_stn.items() if len(v) == 1]
print(f"\n  Singles (no merge partner): {len(singles)}")
if singles:
    single_ncands = Counter(len(r.get('candidates', [])) for _, r in singles)
    print(f"  Single candidate counts: {dict(sorted(single_ncands.items(), key=lambda x: -x[1])[:10])}")

# For groups of size 2+, check page gaps
multi_groups = [(k, v) for k, v in groups_with_stn.items() if len(v) >= 2]
print(f"\n  Multi-page groups: {len(multi_groups)}")
gap_issues = 0
for key, recs in multi_groups:
    recs.sort(key=lambda r: r.get('page', 0) or 0)
    pages = [r.get('page', 0) or 0 for r in recs]
    max_gap = max(pages[i+1] - pages[i] for i in range(len(pages)-1))
    if max_gap > 2:
        gap_issues += 1
if gap_issues:
    print(f"  Groups with page gap > 2: {gap_issues}")

# Check consolidated candidate counts in multi groups
multi_cand_totals = []
for key, recs in multi_groups:
    seen = set()
    total = 0
    for r in recs:
        for c in (r.get('candidates') or []):
            cno = c.get('number')
            if cno and cno not in seen:
                seen.add(cno)
                total += 1
    multi_cand_totals.append(total)
cand_dist = Counter(multi_cand_totals)
print(f"  Would-be consolidated candidate counts:")
for n, cnt in sorted(cand_dist.items(), key=lambda x: -x[1])[:15]:
    marker = ' ✅' if n == 57 else (' ⚠️' if n >= 50 else '')
    print(f"    n={n}: {cnt} groups{marker}")

# Analyze groups WITHOUT station_no
print(f"\n=== Groups WITHOUT station_no ===")
print(f"  Total files (groups): {len(groups_no_stn)}")
total_no_stn_recs = sum(len(v) for v in groups_no_stn.values())
print(f"  Total records: {total_no_stn_recs}")

# Check if station_no can be inferred from filename
infer_patterns = 0
for r in bl:
    if not (r.get('ocr_station_no') or r.get('station_no')):
        fname = r.get('file', '')
        m = re.search(r'หน่วย(?:ที่)?\s*(\d+)', fname)
        if m:
            infer_patterns += 1
print(f"  Could infer station from filename: {infer_patterns}")

# Check: same file, different pages — are they same station?
print(f"\n=== Sample: file with multiple pages but no station_no ===")
shown = 0
for fkey, recs in sorted(groups_no_stn.items(), key=lambda x: -len(x[1]))[:3]:
    recs.sort(key=lambda r: r.get('page', 0) or 0)
    pages = [r.get('page') for r in recs]
    ncands = [len(r.get('candidates', [])) for r in recs]
    print(f"  File: ...{fkey[-80:]}") 
    print(f"    Pages: {pages[:20]}{'...' if len(pages) > 20 else ''}")
    print(f"    Cands: {ncands[:20]}{'...' if len(ncands) > 20 else ''}")
    shown += 1

# Summary: what would happen with better consolidation?
print(f"\n=== Potential improvement ===")
# Count how many n<57 could become n=57 if we merge all pages per (file, station)
could_be_57 = sum(1 for t in multi_cand_totals if t >= 55)
currently_57_groups = sum(1 for t in multi_cand_totals if t == 57)
print(f"  Multi-groups that already produce n=57: {currently_57_groups}")
print(f"  Multi-groups that could produce n>=55: {could_be_57}")
print(f"  Multi-groups total: {len(multi_groups)}")
