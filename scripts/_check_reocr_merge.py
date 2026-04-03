#!/usr/bin/env python3
"""Check if re-OCR n=33 actually added candidates to source records."""
import json, os, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

for fname in ['ocr_multimodel_chaiyaphum.json', 'ocr_multimodel_tak.json', 'ocr_multimodel_phetchabun.json']:
    path = os.path.join(DATA_DIR, fname)
    data = json.load(open(path, encoding='utf-8'))
    
    reocr = [r for r in data if r.get('_reocr_n33')]
    if not reocr:
        print(f'{fname}: no _reocr_n33 records')
        continue
    
    cand_counts = Counter(len(r.get('candidates', [])) for r in reocr)
    print(f'\n{fname}: {len(reocr)} _reocr_n33 records')
    print(f'  Candidate counts in updated records:')
    for n, cnt in sorted(cand_counts.items(), key=lambda x: -x[1])[:10]:
        print(f'    n={n}: {cnt}')
    
    # Compare with backup
    backup = path + '.pre_reocr_n33'
    if os.path.exists(backup):
        old = json.load(open(backup, encoding='utf-8'))
        old_lookup = {(r.get('file',''), r.get('page',0)): len(r.get('candidates',[])) for r in old}
        improved = 0
        same = 0
        for r in reocr:
            key = (r.get('file',''), r.get('page',0))
            old_n = old_lookup.get(key, 0)
            new_n = len(r.get('candidates', []))
            if new_n > old_n:
                improved += 1
            else:
                same += 1
        print(f'  vs backup: {improved} improved, {same} same')
