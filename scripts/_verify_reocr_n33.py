"""
Post-OCR verification for n=33 re-OCR results.

Checks:
1. How many บัญชีรายชื่อ records still have n=33 (should drop significantly)
2. How many now have n=57 (full 3-page merge)
3. How many have _reocr_n33 flag (updated)
4. Candidate count distribution before/after

Run after _reocr_n33_missing_page.py + prepare_review_data.py.
"""
import json, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# ── Load OCR data ──────────────────────────────────────────────────────────
ocr_files = {
    'phetchabun': os.path.join(DATA_DIR, 'ocr_multimodel_phetchabun.json'),
    'chaiyaphum': os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json'),
    'tak':        os.path.join(DATA_DIR, 'ocr_multimodel_tak.json'),
}

print('=== OCR Source Files ===')
from collections import Counter
for prov, path in ocr_files.items():
    data = json.load(open(path, encoding='utf-8'))
    party_list = [r for r in data if r.get('vote_type') == 'บัญชีรายชื่อ']
    cand_counts = Counter(len(r.get('candidates', [])) for r in party_list)
    n_reocr = sum(1 for r in party_list if r.get('_reocr_n33'))
    print(f'\n  {prov}: {len(party_list)} บัญชีรายชื่อ records, {n_reocr} updated by re-OCR')
    print(f'  Candidate count distribution (top 10):')
    for n, count in sorted(cand_counts.items(), key=lambda x: -x[1])[:10]:
        marker = ' ← was 33' if n == 57 else (' ← still 33' if n == 33 else '')
        print(f'    n={n:3d}: {count:4d} records{marker}')

# ── Load review data ───────────────────────────────────────────────────────
review_path = os.path.join(PROJECT_ROOT, 'review-app/public/data/review_data.json')
if not os.path.exists(review_path):
    print('\nreview_data.json not found — run prepare_review_data.py first')
    sys.exit(0)

review = json.load(open(review_path, encoding='utf-8'))
party_review = [r for r in review if r.get('vote_type') == 'บัญชีรายชื่อ']

print(f'\n=== review_data.json ===')
print(f'  Total บัญชีรายชื่อ items: {len(party_review)}')

cand_counts = Counter(len(r.get('candidates', [])) for r in party_review)
print(f'  Candidate count distribution (key values):')
for n in [0, 10, 23, 24, 33, 56, 57]:
    count = cand_counts.get(n, 0)
    print(f'    n={n:3d}: {count:4d} records')

print(f'\n  n<10 (cover/sig pages):    {sum(v for k,v in cand_counts.items() if k < 10):4d}')
print(f'  n=10-24 (single page):     {sum(v for k,v in cand_counts.items() if 10 <= k <= 24):4d}')
print(f'  n=33 (still missing pg2):  {cand_counts.get(33, 0):4d}')
print(f'  n=34-56 (partial):         {sum(v for k,v in cand_counts.items() if 34 <= k <= 56):4d}')
print(f'  n=57 (fully merged):       {cand_counts.get(57, 0):4d}')
print(f'  n>57 (over-extracted):     {sum(v for k,v in cand_counts.items() if k > 57):4d}')

# ── Province breakdown ─────────────────────────────────────────────────────
print(f'\n=== By Province ===')
by_prov = {}
for r in party_review:
    p = r.get('province', '?')
    n = len(r.get('candidates', []))
    if p not in by_prov:
        by_prov[p] = Counter()
    by_prov[p][n] += 1

for prov, counts in sorted(by_prov.items()):
    total = sum(counts.values())
    n33 = counts.get(33, 0)
    n57 = counts.get(57, 0)
    print(f'  {prov}: total={total}, n=57: {n57}, n=33: {n33}')
