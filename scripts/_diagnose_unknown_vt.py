#!/usr/bin/env python3
"""Deep diagnose of ไม่ระบุ items - what signals can we use to reclassify?"""
import json, sys, re
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))
unknown = [r for r in d if r.get('vote_type') in ('ไม่ระบุ', '', None)]
print(f"ไม่ระบุ items: {len(unknown)}\n")

# Categorize by available signals
cats = {
    'cand_2_referendum': [],   # 2 candidates = เห็นชอบ/ไม่เห็นชอบ
    'cand_gt10_partylist': [], # >10 candidates = บัญชีรายชื่อ
    'fname_referendum': [],     # filename has อส/4.7/4-7 etc
    'fname_has_clue': [],       # some other clue in filename
    'no_clue': [],              # nothing to go on
}

for r in unknown:
    f = r.get('file', '')
    cands = r.get('candidates') or []
    n = len(cands)
    cand_names = [c.get('name') or '' for c in cands]
    
    # Check candidate names for referendum
    has_referendum_cands = any('เห็นชอบ' in name for name in cand_names if name)
    
    # Check filename for referendum patterns  
    fname_has_ref = bool(re.search(r'อส[.\s]*4|อ\.?\s*ส\.?\s*4|4[/\-ทับ_\.]+7', f))
    
    if has_referendum_cands:
        cats['cand_2_referendum'].append(r)
    elif fname_has_ref:
        cats['fname_referendum'].append(r)
    elif n > 10:
        cats['cand_gt10_partylist'].append(r)
    else:
        cats['no_clue'].append(r)

for cat, items in cats.items():
    print(f"\n=== {cat}: {len(items)} items ===")
    if not items:
        continue
    # Show samples
    for r in items[:5]:
        f = r.get('file', '').replace('\\', '/').split('/')
        cands = r.get('candidates') or []
        cand_names = [c.get('name', '') for c in cands[:3]]
        ballot = 'Y' if r.get('registered_voters') is not None else 'N'
        print(f"  n_cands={len(cands)} ballot={ballot} .../{'/'.join(f[-2:])}")
        if cand_names:
            print(f"    cands: {cand_names}")

# For no_clue items, check OCR text for clues
print(f"\n=== Analyzing {len(cats['no_clue'])} no_clue items ===")
no_clue = cats['no_clue']

# Check if OCR text has clues
for r in no_clue[:10]:
    f = r.get('file', '').replace('\\', '/').split('/')
    ocr = r.get('ocr_text', '')[:150]
    ocr_vt = r.get('ocr_vote_type', '')
    cands = r.get('candidates') or []
    print(f"\n  .../{'/'.join(f[-2:])}")
    print(f"  n_cands={len(cands)} ocr_vt='{ocr_vt}'")
    if cands:
        for c in cands[:3]:
            print(f"    #{c.get('number','?')} {c.get('name','?')} votes={c.get('votes','?')}")
    if ocr:
        print(f"  ocr_text: {ocr[:100]}...")

# Check page numbers - are these multi-page items at specific positions?
print(f"\n=== Page position analysis for no_clue ===")
page_dist = Counter(r.get('page', '?') for r in no_clue)
print(f"Page distribution: {dict(page_dist.most_common(10))}")
tp_dist = Counter(r.get('total_pages', '?') for r in no_clue)
print(f"Total pages dist: {dict(tp_dist.most_common(10))}")
