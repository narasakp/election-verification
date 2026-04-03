#!/usr/bin/env python3
import json, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))
u = [r for r in d if r.get('vote_type') in ('\u0e44\u0e21\u0e48\u0e23\u0e30\u0e1a\u0e38', '', None)]
print(f"Count: {len(u)}")
for r in u:
    f = (r.get('file') or '')[-80:]
    n = len(r.get('candidates') or [])
    prov = r.get('province', '?')
    const = r.get('constituency', '?')
    print(f"  file=...{f}")
    print(f"  cands={n} prov={prov} const={const}")
