#!/usr/bin/env python3
"""Diagnose issues #3-#7 from the anomaly checklist."""
import json, sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))
print(f"Total items: {len(d)}\n")

# ======================================================================
# #3: ไม่ระบุ vote_type
# ======================================================================
print("=" * 60)
print("#3: ไม่ระบุ vote_type")
print("=" * 60)
unknown_vt = [r for r in d if (r.get('vote_type') or '') in ('', 'ไม่ระบุ', 'unknown')]
print(f"Count: {len(unknown_vt)}")

# Province breakdown
prov = Counter(r.get('province', '?') for r in unknown_vt)
print(f"By province: {dict(prov.most_common())}")

# Check filenames
fname_samples = Counter()
for r in unknown_vt:
    f = r.get('file', '?').replace('\\', '/')
    fname = f.split('/')[-1]
    fname_samples[fname] += 1
print(f"\nTop filenames:")
for fn, c in fname_samples.most_common(15):
    print(f"  [{c}] {fn}")

# Check folder paths for clues
print(f"\nSample paths (10):")
for r in unknown_vt[:10]:
    f = r.get('file', '?').replace('\\', '/')
    parts = f.split('/')
    print(f"  pg={r.get('page','?')} tp={r.get('total_pages','?')} .../{'/'.join(parts[-3:])}")

# Check if they have candidates or ballot data
has_cands = sum(1 for r in unknown_vt if r.get('candidates'))
has_ballot = sum(1 for r in unknown_vt if r.get('registered_voters') is not None)
print(f"\nHas candidates: {has_cands}/{len(unknown_vt)}")
print(f"Has ballot data: {has_ballot}/{len(unknown_vt)}")

# Check candidate counts
if has_cands:
    cand_dist = Counter(len(r.get('candidates', [])) for r in unknown_vt if r.get('candidates'))
    print(f"Candidate count dist: {dict(cand_dist.most_common(10))}")

# ======================================================================
# #4: No ballot data
# ======================================================================
print(f"\n{'=' * 60}")
print("#4: No ballot data")
print("=" * 60)
ballot_fields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 'invalid_ballots', 'remaining_ballots']
no_ballot = [r for r in d if all(r.get(f) is None for f in ballot_fields)]
print(f"Count: {len(no_ballot)} ({len(no_ballot)/len(d)*100:.1f}%)")

# By vote type
vt_dist = Counter(r.get('vote_type', '?') for r in no_ballot)
print(f"By vote_type: {dict(vt_dist.most_common())}")

# By province
prov_dist = Counter(r.get('province', '?') for r in no_ballot)
print(f"By province: {dict(prov_dist.most_common())}")

# Check if they have candidates
has_cands_nb = sum(1 for r in no_ballot if r.get('candidates'))
print(f"Has candidates: {has_cands_nb}/{len(no_ballot)}")

# Is back page?
is_back = sum(1 for r in no_ballot if r.get('is_back_page'))
print(f"is_back_page: {is_back}/{len(no_ballot)}")

# Sample
print(f"\nSamples (10):")
for r in no_ballot[:10]:
    f = r.get('file', '?').replace('\\', '/').split('/')
    print(f"  vt={r.get('vote_type','?')} stn={r.get('station_no','?')} cands={len(r.get('candidates',[]))} .../{'/'.join(f[-2:])}")

# ======================================================================
# #5: No candidates
# ======================================================================
print(f"\n{'=' * 60}")
print("#5: No candidates")
print("=" * 60)
no_cands = [r for r in d if not r.get('candidates')]
print(f"Count: {len(no_cands)} ({len(no_cands)/len(d)*100:.1f}%)")

# By vote type
vt_dist5 = Counter(r.get('vote_type', '?') for r in no_cands)
print(f"By vote_type: {dict(vt_dist5.most_common())}")

# By province
prov_dist5 = Counter(r.get('province', '?') for r in no_cands)
print(f"By province: {dict(prov_dist5.most_common())}")

# Check if they have ballot data
has_ballot5 = sum(1 for r in no_cands if any(r.get(f) is not None for f in ballot_fields))
print(f"Has ballot data: {has_ballot5}/{len(no_cands)}")

# is_back_page?
is_back5 = sum(1 for r in no_cands if r.get('is_back_page'))
print(f"is_back_page: {is_back5}/{len(no_cands)}")

# No ballot AND no candidates (totally empty)
totally_empty = [r for r in d if not r.get('candidates') and all(r.get(f) is None for f in ballot_fields)]
print(f"\nTotally empty (no ballot + no candidates): {len(totally_empty)}")
vt_empty = Counter(r.get('vote_type', '?') for r in totally_empty)
print(f"  By vote_type: {dict(vt_empty.most_common())}")

# ======================================================================
# #6: Cross-reference
# ======================================================================
print(f"\n{'=' * 60}")
print("#6: Cross-reference data")
print("=" * 60)
has_ect = sum(1 for r in d if r.get('ect_candidates'))
has_xref = sum(1 for r in d if r.get('_candidate_mismatch') or r.get('_candidates_auto_fixed'))
print(f"Has ECT candidates: {has_ect}")
print(f"Auto-fixed: {sum(1 for r in d if r.get('_candidates_auto_fixed'))}")
print(f"Mismatches: {sum(1 for r in d if r.get('_candidate_mismatch'))}")

# ======================================================================
# #7: Station coverage
# ======================================================================
print(f"\n{'=' * 60}")
print("#7: Station coverage per constituency")
print("=" * 60)
# Count unique stations per (province, constituency, vote_type)
coverage = defaultdict(set)
for r in d:
    prov = r.get('province', '?')
    const = r.get('constituency', '?')
    vt = r.get('vote_type', '?')
    stn = r.get('station_no')
    if stn and vt in ('แบ่งเขต', 'บัญชีรายชื่อ'):
        coverage[(prov, const, vt)].add(stn)

print(f"{'Province':<15} {'Const':>5} {'VoteType':<15} {'Stations':>8}")
print("-" * 50)
for (prov, const, vt), stns in sorted(coverage.items()):
    print(f"{prov:<15} {const:>5} {vt:<15} {len(stns):>8}")
