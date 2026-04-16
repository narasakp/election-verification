"""Diagnose vote-candidate mapping across ALL provinces and constituencies.

Compares:
  1. ECT candidate reference (our ground truth for candidate list)
  2. Killernay constituency data (ground truth for vote totals per candidate)
  3. OCR station-level data (our data, possibly with wrong mapping)

Detects systematic permutations where OCR reads correct vote values
but assigns them to wrong candidate numbers.
"""
import csv
import json
import os
from collections import defaultdict
from itertools import permutations

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def load_killernay():
    """Load killernay constituency-level vote totals."""
    path = os.path.join(DATA_DIR, 'killernay_constituency_full.csv')
    result = {}  # { (province, zone): { cand_no: { name, party, votes } } }
    with open(path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            prov = row['จังหวัด']
            zone = row['เขต']
            try:
                no = int(row['หมายเลข'])
                votes = int(row['คะแนน'].replace(',', ''))
            except (ValueError, TypeError):
                continue
            key = (prov, zone)
            if key not in result:
                result[key] = {}
            result[key][no] = {
                'name': row['ชื่อผู้สมัคร'],
                'party': row['พรรค'],
                'votes': votes,
            }
    return result


def load_ect_ref():
    """Load ECT candidate reference."""
    path = os.path.join(DATA_DIR, 'ect_candidates_reference.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_review_data():
    """Load review data (station-level OCR)."""
    path = os.path.join(DATA_DIR, '..', 'review-app', 'public', 'data', 'review_data.json')
    if not os.path.exists(path):
        # Try postprocessed
        import glob
        files = glob.glob(os.path.join(DATA_DIR, 'ocr_multimodel_*.json')) + \
                glob.glob(os.path.join(DATA_DIR, 'postprocessed_*.json'))
        records = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as fh:
                records.extend(json.load(fh))
        return records
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_candidate_lists(ect_ref, killernay):
    """Compare ECT reference candidate list with killernay candidate list.
    Detect number-to-name mismatches."""
    print("=" * 80)
    print("STEP 1: Compare ECT ref vs Killernay candidate numbering")
    print("=" * 80)

    mismatches = []
    for prov in ect_ref:
        for zone in ect_ref[prov]:
            key = (prov, zone)
            if key not in killernay:
                continue

            ect_cands = {c['no']: c for c in ect_ref[prov][zone]}
            kill_cands = killernay[key]

            for no in sorted(set(ect_cands.keys()) & set(kill_cands.keys())):
                ect_name = ect_cands[no]['name']
                kill_name = kill_cands[no]['name']
                # Simple character overlap check
                common = sum(1 for ch in ect_name if ch in kill_name)
                ratio = common / max(len(ect_name), len(kill_name), 1)
                if ratio < 0.5:
                    mismatches.append({
                        'province': prov,
                        'zone': zone,
                        'no': no,
                        'ect_name': ect_name,
                        'ect_party': ect_cands[no]['party'],
                        'kill_name': kill_name,
                        'kill_party': kill_cands[no]['party'],
                        'overlap': ratio,
                    })

    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} candidate NUMBER mismatches between ECT ref and Killernay:\n")
        for m in mismatches:
            print(f"  {m['province']} เขต {m['zone']} #{m['no']:>2d}")
            print(f"    ECT:      {m['ect_name']} ({m['ect_party']})")
            print(f"    Killernay: {m['kill_name']} ({m['kill_party']})")
            print(f"    Name overlap: {m['overlap']:.1%}")
            print()
    else:
        print("\n✅ No candidate number mismatches between ECT ref and Killernay")

    return mismatches


def find_correct_mapping(ect_ref, killernay):
    """For each constituency, determine which numbering system is correct
    by finding how killernay numbers map to ECT numbers (by name matching)."""
    print("=" * 80)
    print("STEP 2: Build killernay→ECT number mapping per constituency")
    print("=" * 80)

    mappings = {}  # (prov, zone) -> { kill_no: ect_no }
    issues = []

    for prov in ect_ref:
        for zone in ect_ref[prov]:
            key = (prov, zone)
            if key not in killernay:
                continue

            ect_cands = ect_ref[prov][zone]
            kill_cands = killernay[key]

            # Match by name
            mapping = {}  # kill_no -> ect_no
            ect_by_name = {}
            for c in ect_cands:
                ect_by_name[c['name']] = c['no']

            for kill_no, kill_data in kill_cands.items():
                kill_name = kill_data['name']
                # Try exact match first
                if kill_name in ect_by_name:
                    mapping[kill_no] = ect_by_name[kill_name]
                    continue
                # Fuzzy match
                best_no = None
                best_ratio = 0
                for c in ect_cands:
                    common = sum(1 for ch in kill_name if ch in c['name'])
                    ratio = common / max(len(kill_name), len(c['name']), 1)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_no = c['no']
                if best_no and best_ratio >= 0.4:
                    mapping[kill_no] = best_no
                else:
                    issues.append(f"  {prov} เขต {zone}: Kill #{kill_no} '{kill_name}' — no ECT match")

            # Check if mapping is identity (no permutation needed)
            has_permutation = any(k != v for k, v in mapping.items())
            if has_permutation:
                mappings[key] = mapping
                print(f"\n  🔀 {prov} เขต {zone}: Numbering differs!")
                for kill_no in sorted(mapping.keys()):
                    ect_no = mapping[kill_no]
                    arrow = "→" if kill_no != ect_no else "="
                    flag = " ⚠️" if kill_no != ect_no else ""
                    kill_name = kill_cands[kill_no]['name']
                    print(f"    Kill #{kill_no:>2d} {arrow} ECT #{ect_no:>2d}  {kill_name}{flag}")

    if issues:
        print(f"\n  Unmatched candidates: {len(issues)}")
        for iss in issues[:10]:
            print(iss)

    if not mappings:
        print("\n✅ All constituencies have identical numbering between Killernay and ECT")

    return mappings


def aggregate_ocr_votes(records):
    """Aggregate OCR station-level votes per candidate, per constituency."""
    result = {}  # (prov, zone) -> { cand_no: total_votes, station_count }
    for r in records:
        if r.get('vote_type') != 'แบ่งเขต':
            continue
        prov = r.get('province', '')
        zone = str(r.get('constituency', ''))
        cands = r.get('candidates', [])
        if not cands:
            continue

        key = (prov, zone)
        if key not in result:
            result[key] = {'by_cand': defaultdict(int), 'stations': 0}
        result[key]['stations'] += 1

        for c in cands:
            no = c.get('number')
            votes = c.get('votes')
            if no is not None and votes is not None:
                result[key]['by_cand'][no] += votes

    return result


def detect_vote_permutations(ocr_agg, killernay, ect_ref):
    """Compare aggregated OCR totals against killernay to detect permutations."""
    print("\n" + "=" * 80)
    print("STEP 3: Compare OCR aggregated votes vs Killernay (detect permutations)")
    print("=" * 80)

    problems = []

    for key in sorted(ocr_agg.keys()):
        prov, zone = key
        if key not in killernay:
            continue

        ocr = ocr_agg[key]['by_cand']
        kill = killernay[key]
        stations = ocr_agg[key]['stations']

        # Compare per candidate
        mismatched = []
        for no in sorted(set(ocr.keys()) & set(kill.keys())):
            ocr_total = ocr[no]
            kill_total = kill[no]['votes']
            if kill_total == 0:
                continue
            error_pct = abs(ocr_total - kill_total) / kill_total * 100
            if error_pct > 20:  # More than 20% off
                mismatched.append({
                    'no': no,
                    'name': kill[no]['name'],
                    'ocr': ocr_total,
                    'kill': kill_total,
                    'error_pct': error_pct,
                })

        if mismatched:
            # Check if this is a permutation (OCR values match killernay but at wrong positions)
            ocr_vals = {no: ocr[no] for no in ocr}
            kill_vals = {no: kill[no]['votes'] for no in kill if no in ocr}

            # Try to find which permutation maps OCR → correct
            mismatched_nos = [m['no'] for m in mismatched]
            ocr_mis_vals = [ocr[n] for n in mismatched_nos]
            kill_mis_vals = [kill[n]['votes'] for n in mismatched_nos]

            # Check if OCR values are a permutation of killernay values
            perm_found = None
            if len(mismatched_nos) <= 5:  # Only check small permutations
                ocr_set = sorted(ocr_mis_vals)
                kill_set = sorted(kill_mis_vals)
                # Rough check: are the same set of values present?
                ratio_match = sum(1 for v in ocr_set if any(abs(v - kv) / max(kv, 1) < 0.15 for kv in kill_set))
                if ratio_match >= len(mismatched_nos) * 0.6:
                    perm_found = True

            problems.append({
                'province': prov,
                'zone': zone,
                'stations': stations,
                'mismatched': mismatched,
                'is_permutation': perm_found,
                'mismatched_nos': mismatched_nos,
            })

    if problems:
        print(f"\n⚠️  Found {len(problems)} constituencies with vote mismatches:\n")
        for p in problems:
            perm_tag = " 🔀 PERMUTATION" if p['is_permutation'] else ""
            print(f"  {p['province']} เขต {p['zone']} ({p['stations']} stations){perm_tag}")
            for m in p['mismatched']:
                direction = "↑" if m['ocr'] > m['kill'] else "↓"
                print(f"    #{m['no']:>2d} {m['name'][:25]:25s}  OCR={m['ocr']:>8,d}  Kill={m['kill']:>8,d}  {direction} {m['error_pct']:>6.1f}%")
            print()
    else:
        print("\n✅ No significant vote mismatches detected")

    return problems


def main():
    print("🔍 Vote-Candidate Mapping Diagnostic")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    ect_ref = load_ect_ref()
    print(f"  ECT ref: {sum(len(z) for z in ect_ref.values())} constituencies")

    killernay = load_killernay()
    print(f"  Killernay: {len(killernay)} constituencies")

    records = load_review_data()
    print(f"  OCR records: {len(records)}")

    # Step 1: Compare candidate lists
    print()
    number_mismatches = compare_candidate_lists(ect_ref, killernay)

    # Step 2: Build correct mapping
    print()
    numbering_maps = find_correct_mapping(ect_ref, killernay)

    # Step 3: Aggregate OCR and compare
    ocr_agg = aggregate_ocr_votes(records)
    print(f"\n  OCR aggregated: {len(ocr_agg)} constituencies")
    vote_problems = detect_vote_permutations(ocr_agg, killernay, ect_ref)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Number mismatches (ECT vs Killernay): {len(number_mismatches)}")
    print(f"  Numbering permutations needed: {len(numbering_maps)}")
    print(f"  Vote total mismatches: {len(vote_problems)}")
    perm_count = sum(1 for p in vote_problems if p['is_permutation'])
    print(f"  Of which likely permutations: {perm_count}")


if __name__ == '__main__':
    main()
