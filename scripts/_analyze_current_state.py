#!/usr/bin/env python3
"""Analyze current state of review_data.json for planning next steps."""
import json, os, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REVIEW_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
d = json.load(open(REVIEW_PATH, encoding='utf-8'))

print(f"=== REVIEW DATA OVERVIEW ===")
print(f"Total items: {len(d)}")

# Source type
src = Counter(r.get('_source_type', '?') for r in d)
print(f"\nSource: {dict(src)}")

# Vote type
vt = Counter(r.get('vote_type', '?') for r in d)
print(f"Vote type: {dict(vt)}")

# Province
prov = Counter(r.get('province', '?') for r in d)
print(f"Province: {dict(prov)}")

# Data quality
no_ballot = sum(1 for r in d if all(r.get(f) is None for f in 
    ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots']))
no_cands = sum(1 for r in d if not r.get('candidates'))
with_cands = len(d) - no_cands
ect = sum(1 for r in d if r.get('ect_candidates'))
mm = sum(1 for r in d if r.get('_candidate_mismatch'))
auto_fixed = sum(1 for r in d if r.get('_candidates_auto_fixed'))

print(f"\n=== DATA QUALITY ===")
print(f"No ballot data: {no_ballot} ({no_ballot*100/len(d):.1f}%)")
print(f"No candidates: {no_cands} ({no_cands*100/len(d):.1f}%)")
print(f"With candidates: {with_cands} ({with_cands*100/len(d):.1f}%)")
print(f"ECT enriched: {ect} ({ect*100/len(d):.1f}%)")
print(f"Candidate mismatches: {mm}")
print(f"Auto-fixed candidates: {auto_fixed}")

# Candidate count distribution by vote type
print(f"\n=== CANDIDATE COUNT DISTRIBUTION ===")
for vote_type in ['แบ่งเขต', 'บัญชีรายชื่อ']:
    items = [r for r in d if r.get('vote_type') == vote_type]
    cand_counts = Counter(len(r.get('candidates', [])) for r in items)
    print(f"\n{vote_type} ({len(items)} items):")
    for n, cnt in sorted(cand_counts.items()):
        pct = cnt * 100 / len(items)
        bar = '#' * int(pct / 2)
        print(f"  n={n:3d}: {cnt:5d} ({pct:5.1f}%) {bar}")

# Station coverage per province/constituency
print(f"\n=== STATION COVERAGE ===")
stations = defaultdict(lambda: defaultdict(set))
for r in d:
    p = r.get('province', '')
    c = str(r.get('constituency', ''))
    vtype = r.get('vote_type', '')
    stn = r.get('ocr_station_no') or r.get('station_no') or ''
    if stn:
        stations[(p, c)][vtype].add(str(stn))

for (p, c), vt_data in sorted(stations.items()):
    baeng = len(vt_data.get('แบ่งเขต', set()))
    banchi = len(vt_data.get('บัญชีรายชื่อ', set()))
    print(f"  {p} เขต {c}: แบ่งเขต={baeng} stn, บัญชีฯ={banchi} stn")

# PDF URL availability
has_pdf = sum(1 for r in d if r.get('pdf_url') or r.get('drive_view_url'))
print(f"\n=== PDF VIEWER ===")
print(f"Items with PDF URL: {has_pdf} ({has_pdf*100/len(d):.1f}%)")

# Ballot data completeness
fields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 
          'invalid_ballots', 'no_vote_ballots', 'remaining_ballots', 'total_votes']
print(f"\n=== BALLOT FIELD COMPLETENESS ===")
for f in fields:
    has = sum(1 for r in d if r.get(f) is not None)
    print(f"  {f}: {has} ({has*100/len(d):.1f}%)")

# Cross-reference data
xref_path = os.path.join(ROOT, 'review-app', 'public', 'data', 'cross_reference_sources.json')
if os.path.exists(xref_path):
    xref = json.load(open(xref_path, encoding='utf-8'))
    print(f"\n=== CROSS-REFERENCE ===")
    print(f"Cross-reference entries: {len(xref)}")
else:
    print(f"\n=== CROSS-REFERENCE ===")
    print(f"cross_reference_sources.json: NOT FOUND")

# File size
fsize = os.path.getsize(REVIEW_PATH)
print(f"\n=== FILE SIZE ===")
print(f"review_data.json: {fsize/1024/1024:.2f} MB")
