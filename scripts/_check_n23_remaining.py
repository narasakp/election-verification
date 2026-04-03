#!/usr/bin/env python3
"""Check remaining n=23 items after 6pp fix."""
import json, os, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
review = json.load(open(REVIEW_PATH, encoding='utf-8'))

bad = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ' and len(r.get('candidates', [])) != 57]
n23 = [r for r in bad if len(r.get('candidates', [])) == 23]

print(f"Total n!=57: {len(bad)}")
print(f"n=23: {len(n23)}")
print(f"  by province: {dict(Counter(r.get('province') for r in n23))}")
print(f"  consolidated: {sum(1 for r in n23 if r.get('_consolidated'))}")
print(f"  6pp_layout: {sum(1 for r in n23 if r.get('_6pp_layout'))}")

# Show file patterns
files = set()
for r in n23:
    if not r.get('_6pp_layout'):
        files.add(r.get('file', ''))

print(f"\n  Non-6pp files with n=23 ({len(files)}):")
for f in sorted(files)[:10]:
    print(f"    ...{f[-70:]}")

# Check n=10 and n=24 too
for target_n in [10, 24, 8, 7]:
    items = [r for r in bad if len(r.get('candidates', [])) == target_n]
    if items:
        print(f"\nn={target_n}: {len(items)}")
        print(f"  6pp: {sum(1 for r in items if r.get('_6pp_layout'))}, pure: {sum(1 for r in items if not r.get('_6pp_layout'))}")
        prov = Counter(r.get('province') for r in items)
        print(f"  province: {dict(prov)}")

# n>57 analysis
ngt57 = [r for r in bad if len(r.get('candidates', [])) > 57]
print(f"\nn>57: {len(ngt57)}")
if ngt57:
    dist = Counter(len(r.get('candidates', [])) for r in ngt57)
    print(f"  distribution: {dict(sorted(dist.items()))}")
    # Check if they have duplicate candidate numbers
    dup_count = 0
    for r in ngt57:
        nums = [c.get('number') for c in r.get('candidates', []) if c.get('number') is not None]
        if len(nums) != len(set(nums)):
            dup_count += 1
    print(f"  with duplicate candidate numbers: {dup_count}")
