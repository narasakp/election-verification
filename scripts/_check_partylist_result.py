#!/usr/bin/env python3
"""Check party list n=57 ratio after fix."""
import json, os, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = json.load(open(os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json'), encoding='utf-8'))

print(f"Total items: {len(d)}")
vt = Counter(r.get('vote_type', '?') for r in d)
print(f"Vote types: {dict(vt)}")

pl = [r for r in d if r.get('vote_type') == 'บัญชีรายชื่อ']
print(f"\nบัญชีรายชื่อ: {len(pl)} items")

if pl:
    dist = Counter(len(r.get('candidates', [])) for r in pl)
    total = len(pl)
    n57 = dist.get(57, 0)
    print(f"n=57: {n57} ({n57*100/total:.1f}%)")
    print(f"\nFull distribution (n>=3 occurrences):")
    for n, c in sorted(dist.items()):
        if c >= 3:
            print(f"  n={n:3d}: {c:5d} ({c*100/total:5.1f}%)")

    # By province
    print(f"\nn=57 by province:")
    for prov in sorted(set(r.get('province','?') for r in pl)):
        items = [r for r in pl if r.get('province') == prov]
        n57p = sum(1 for r in items if len(r.get('candidates',[])) == 57)
        print(f"  {prov}: {n57p}/{len(items)} ({n57p*100/len(items):.1f}%)")
else:
    # Check if vote_type uses different name
    print("\nNo บัญชีรายชื่อ found! Checking all vote_type values:")
    for vtype, cnt in vt.most_common():
        print(f"  '{vtype}': {cnt}")
    # Check for partial matches
    for r in d[:5]:
        print(f"  Sample vote_type: '{r.get('vote_type')}'")
