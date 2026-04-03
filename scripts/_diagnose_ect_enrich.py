#!/usr/bin/env python3
"""Check why ECT enrichment doesn't trim vision items."""
import json, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
ECT_PATH = os.path.join(ROOT, 'data', 'ect_candidates_reference.json')

review = json.load(open(REVIEW_PATH, encoding='utf-8'))
ect_ref = json.load(open(ECT_PATH, encoding='utf-8'))

print("=== ECT Reference Coverage ===")
for prov, zones in ect_ref.items():
    for zone, cands in zones.items():
        print(f"  {prov} zone {zone}: {len(cands)} candidates")

print(f"\n=== Items with >10 candidates (แบ่งเขต) ===")
over10 = [r for r in review if r.get('vote_type') == 'แบ่งเขต' and len(r.get('candidates', [])) > 10]
print(f"Total: {len(over10)}")

# Check if these have ECT enrichment
has_ect = sum(1 for r in over10 if r.get('ect_candidates'))
no_ect = len(over10) - has_ect
print(f"  With ect_candidates: {has_ect}")
print(f"  Without ect_candidates: {no_ect}")

# Check province and constituency
from collections import Counter
prov_cons = Counter((r.get('province','?'), r.get('constituency','?')) for r in over10)
print(f"\n  By province/zone:")
for (p,c), cnt in prov_cons.most_common(20):
    in_ref = 'YES' if p in ect_ref and str(c) in ect_ref.get(p,{}) else 'NO'
    print(f"    {p} zone {c}: {cnt} items (in ECT ref: {in_ref})")

# Sample items without ECT enrichment
no_ect_items = [r for r in over10 if not r.get('ect_candidates')]
if no_ect_items:
    print(f"\n=== Sample items WITHOUT ECT enrichment ===")
    for r in no_ect_items[:5]:
        print(f"  id={r.get('id')} prov={r.get('province')} cons={r.get('constituency')} src={r.get('_source_type')} cands={len(r.get('candidates',[]))} file=...{r.get('file','')[-60:]}")
        # Check candidate details
        for c in r.get('candidates', [])[:3]:
            print(f"    #{c.get('number')}: {c.get('name')} ({c.get('party')}) votes={c.get('votes')} matched={c.get('_ect_matched')} unmatched={c.get('_ect_unmatched')}")
