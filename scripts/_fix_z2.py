"""
Zone 2 vote permutation fix for Chaiyaphum.

OCR reads candidates with wrong position numbers:
  OCR position #1 = true candidate #9 (nayประเสริฐศักดิ์, ไทยก้าวใหม่)
  OCR position #2 = true candidate #2 (nang วาสนา, ประชาชน)
  OCR position #3 = true candidate #1 (nayเชิงชาย, เพื่อไทย)
  OCR position #4 = true candidate #8 (nayณรงค์, ประชาธิปัตย์)
  OCR position #5 = true candidate #5 (nayทัศนัย, ภูมิใจไทย)
  OCR position #6 = true candidate #6 (nayโสโชค, รวมไทยสร้างชาติ)
  OCR position #8 = true candidate #7 (nayถวัลย์, เศรษฐกิจ)

The candidate names are correct, but the position numbers don't match
official candidate numbers. We remap votes to the correct numbers.

remap: {true_no: ocr_no}
  1 -> 3
  2 -> 2
  5 -> 5
  6 -> 6
  7 -> 8
  8 -> 4
  9 -> 1
"""
import json, shutil, sys
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BANDWANG = '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15'
DATA_FILE = 'data/ocr_multimodel_chaiyaphum.json'
BACKUP_FILE = DATA_FILE + '.pre_z2fix'

# Load data
print('Loading OCR data...')
with open(DATA_FILE, encoding='utf-8') as f:
    ocr = json.load(f)

# Backup
print('Creating backup: %s' % BACKUP_FILE)
shutil.copy2(DATA_FILE, BACKUP_FILE)

# remap: {true_no: ocr_no}
# The OCR assigns votes to position ocr_no, but true candidate is true_no
REMAP = {
    1: 3,  # OCR position 3 has votes for true candidate 1
    2: 2,  # OCR position 2 has votes for true candidate 2
    5: 5,  # OCR position 5 has votes for true candidate 5
    6: 6,  # OCR position 6 has votes for true candidate 6
    7: 8,  # OCR position 8 has votes for true candidate 7
    8: 4,  # OCR position 4 has votes for true candidate 8
    9: 1,  # OCR position 1 has votes for true candidate 9
}
# Reverse: ocr_no -> true_no
OCR_TO_TRUE = {v: k for k, v in REMAP.items()}

# Candidate names and parties (true numbers)
TRUE_CAND_INFO = {
    1: ('\u0e19\u0e32\u0e22\u0e40\u0e0a\u0e34\u0e07\u0e0a\u0e32\u0e22 \u0e0a\u0e32\u0e25\u0e35\u0e23\u0e34\u0e19\u0e17\u0e23\u0e4c', '\u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e44\u0e17\u0e22'),
    2: ('\u0e19\u0e32\u0e07\u0e2a\u0e32\u0e27\u0e27\u0e32\u0e2a\u0e19\u0e32 \u0e2d\u0e22\u0e39\u0e48\u0e20\u0e31\u0e01\u0e14\u0e35', '\u0e1b\u0e23\u0e30\u0e0a\u0e32\u0e0a\u0e19'),
    5: ('\u0e19\u0e32\u0e22\u0e17\u0e31\u0e28\u0e19\u0e31\u0e22 \u0e2a\u0e38\u0e02\u0e1b\u0e23\u0e30\u0e2a\u0e32\u0e23', '\u0e20\u0e39\u0e21\u0e34\u0e43\u0e08\u0e44\u0e17\u0e22'),
    6: ('\u0e19\u0e32\u0e22\u0e42\u0e2a\u0e42\u0e0a\u0e04 \u0e2a\u0e39\u0e49\u0e42\u0e19\u0e19\u0e15\u0e32\u0e14', '\u0e23\u0e27\u0e21\u0e44\u0e17\u0e22\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e0a\u0e32\u0e15\u0e34'),
    7: ('\u0e19\u0e32\u0e22\u0e16\u0e27\u0e31\u0e25\u0e22\u0e4c \u0e2b\u0e07\u0e29\u0e4c\u0e44\u0e17\u0e22', '\u0e40\u0e28\u0e23\u0e29\u0e10\u0e01\u0e34\u0e08'),
    8: ('\u0e13\u0e23\u0e07\u0e04\u0e4c \u0e41\u0e02\u0e19\u0e2d\u0e01', '\u0e1b\u0e23\u0e30\u0e0a\u0e32\u0e18\u0e34\u0e1b\u0e31\u0e15\u0e22\u0e4c'),
    9: ('\u0e19\u0e32\u0e22\u0e1b\u0e23\u0e30\u0e40\u0e2a\u0e23\u0e34\u0e0d\u0e28\u0e31\u0e01\u0e14\u0e34\u0e4c \u0e02\u0e33\u0e2b\u0e34\u0e19\u0e15\u0e31\u0e49\u0e07', '\u0e44\u0e17\u0e22\u0e01\u0e49\u0e32\u0e27\u0e43\u0e2b\u0e21\u0e48'),
}

fixed_count = 0
total_z2 = 0

for r in ocr:
    if str(r.get('constituency', '')) != '2':
        continue
    if (r.get('vote_type') or '') != BANDWANG:
        continue
    if r.get('is_back_page'):
        continue
    if r.get('_vote_remap_applied'):
        continue

    total_z2 += 1
    cands = r.get('candidates') or []
    if not cands:
        continue

    # Build a map: ocr_no -> votes (and other fields)
    ocr_votes = {}
    for c in cands:
        no = c.get('number')
        if no is not None:
            ocr_votes[no] = c.get('votes', 0)

    # Build new candidate list with remapped numbers
    new_cands = []
    for c in cands:
        ocr_no = c.get('number')
        true_no = OCR_TO_TRUE.get(ocr_no, ocr_no)  # fallback to same if not in remap
        new_c = dict(c)
        new_c['number'] = true_no
        # Update name/party to match true candidate
        if true_no in TRUE_CAND_INFO:
            new_c['name'] = TRUE_CAND_INFO[true_no][0]
            new_c['party'] = TRUE_CAND_INFO[true_no][1]
        new_cands.append(new_c)

    # Sort by number
    new_cands.sort(key=lambda x: x.get('number', 99))

    r['candidates'] = new_cands
    r['_vote_remap_applied'] = 'z2_permutation'
    fixed_count += 1

print('Total Zone 2 banwang records: %d' % total_z2)
print('Fixed records: %d' % fixed_count)

# Verify
print('\nVerifying...')
from collections import defaultdict
agg = defaultdict(int)
z2_fixed = [r for r in ocr if str(r.get('constituency',''))=='2' and (r.get('vote_type') or '')==BANDWANG and not r.get('is_back_page')]
for r in z2_fixed:
    for c in (r.get('candidates') or []):
        no = c.get('number')
        v = c.get('votes')
        if no and v:
            try: agg[no] += int(v)
            except: pass

import csv
killernay = {}
with open('data/killernay_constituency_full.csv', encoding='utf-8-sig') as f:
    reader = csv.reader(f); next(reader)
    for row in reader:
        if row[0] == '36' and row[2] == '2':
            try: killernay[int(row[3])] = int(row[6])
            except: pass

print('Post-fix Zone 2 comparison:')
for no in sorted(set(list(agg.keys()) + list(killernay.keys()))):
    ours = agg.get(no, 0)
    kv = killernay.get(no, 0)
    diff = 100*(ours-kv)/max(kv,1) if kv else float('inf')
    print('  #%2d: ours=%7d  kill=%7d  diff=%+.0f%%' % (no, ours, kv, diff))

# Save
print('\nSaving...')
with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(ocr, f, ensure_ascii=False, indent=2)
print('Done. Saved to %s' % DATA_FILE)
