#!/usr/bin/env python3
import json, sys
from collections import defaultdict
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))

# Use ocr_station_no as station identifier
coverage = defaultdict(set)
for r in d:
    prov = r.get('province', '?')
    const = r.get('constituency', '?')
    vt = r.get('vote_type', '?')
    stn = r.get('ocr_station_no')
    if stn is not None:
        coverage[(prov, const, vt)].add(str(stn))

print(f"{'Province':<12} {'C':>2} {'VoteType':<16} {'Stns':>5}")
print('-' * 40)
for (prov, const, vt), stns in sorted(coverage.items()):
    print(f"{prov:<12} {const:>2} {vt:<16} {len(stns):>5}")

# Summary: constituency-level for แบ่งเขต only
print(f"\n=== Station count per constituency (แบ่งเขต) ===")
for (prov, const, vt), stns in sorted(coverage.items()):
    if vt == '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15':
        print(f"  {prov} \u0e40\u0e02\u0e15{const}: {len(stns)} stations")
