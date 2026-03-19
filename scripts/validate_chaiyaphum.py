# -*- coding: utf-8 -*-
"""
Validate OCR data quality for Chaiyaphum province.
Checks ballot math, missing data, candidate mismatches.

Usage: python scripts/validate_chaiyaphum.py
"""
import json
import os
import sys
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

BALLOT_FIELDS = [
    'registered_voters', 'turnout', 'ballots_received',
    'valid_ballots', 'invalid_ballots', 'no_vote_ballots',
    'remaining_ballots', 'total_votes',
]


def load_data():
    path = os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_coverage(front):
    """Analyze field coverage by vote type."""
    by_vt = defaultdict(list)
    for r in front:
        vt = r.get('vote_type') or 'unknown'
        by_vt[vt].append(r)

    print("=" * 60)
    print("1. FIELD COVERAGE BY VOTE TYPE")
    print("=" * 60)
    for vt, items in sorted(by_vt.items(), key=lambda x: -len(x[1])):
        print("\n  [%s] %d records:" % (vt, len(items)))
        for f in BALLOT_FIELDS:
            has = sum(1 for r in items if r.get(f) is not None)
            pct = 100 * has / len(items) if items else 0
            bar = "#" * int(pct / 5)
            print("    %-22s %4d/%4d (%3.0f%%) %s" % (f, has, len(items), pct, bar))
        # candidates
        has_c = sum(1 for r in items if r.get('candidates'))
        avg_c = 0
        if has_c:
            avg_c = sum(len(r.get('candidates', [])) for r in items if r.get('candidates')) / has_c
        print("    %-22s %4d/%4d (%3.0f%%) avg=%.1f" % ('candidates', has_c, len(items), 100 * has_c / len(items), avg_c))


def analyze_no_ballot_data(front):
    """Analyze records with no ballot metadata."""
    no_data = [r for r in front if all(
        r.get(f) is None for f in ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 'invalid_ballots']
    )]
    with_data = [r for r in front if r.get('valid_ballots') is not None]

    print("\n" + "=" * 60)
    print("2. NO BALLOT DATA ANALYSIS")
    print("=" * 60)
    print("  Total front pages: %d" % len(front))
    print("  With ballot data:  %d" % len(with_data))
    print("  No ballot data:    %d" % len(no_data))

    vt_counter = Counter(r.get('vote_type', '?') for r in no_data)
    print("\n  No-data by vote_type:")
    for vt, cnt in vt_counter.most_common():
        print("    %-20s %d" % (vt, cnt))

    # Check if no-data records have OTHER useful fields
    has_tv = sum(1 for r in no_data if r.get('total_votes') is not None)
    has_cands = sum(1 for r in no_data if r.get('candidates'))
    has_station = sum(1 for r in no_data if r.get('station_no') is not None)
    print("\n  No-data records that DO have:")
    print("    total_votes:  %d" % has_tv)
    print("    candidates:   %d" % has_cands)
    print("    station_no:   %d" % has_station)

    # Conclusion
    bl_nodata = sum(1 for r in no_data if r.get('vote_type') == '\u0e1a\u0e31\u0e0d\u0e0a\u0e35\u0e23\u0e32\u0e22\u0e0a\u0e37\u0e48\u0e2d')
    if bl_nodata > len(no_data) * 0.9:
        print("\n  >> CONCLUSION: %.0f%% of no-data records are party-list (\u0e1a\u0e31\u0e0d\u0e0a\u0e35\u0e23\u0e32\u0e22\u0e0a\u0e37\u0e48\u0e2d)." % (100 * bl_nodata / len(no_data)))
        print("     These forms often have candidates+votes but no ballot metadata")
        print("     on the front page. This is EXPECTED for multi-station PDFs.")

    return no_data, with_data


def validate_ballot_math(with_data):
    """Validate ballot equation and other math checks."""
    print("\n" + "=" * 60)
    print("3. BALLOT MATH VALIDATION")
    print("=" * 60)

    results = {
        'ballot_eq': [],       # ballots_received != valid + invalid + novote + remaining
        'turnout_over': [],    # turnout > registered
        'tv_vs_cands': [],     # total_votes != sum(candidate votes)
        'tv_over_valid': [],   # total_votes > valid_ballots
        'negative_vals': [],   # any negative value
    }

    for r in with_data:
        rid = "%s p%s" % (r.get('file', '')[-50:], r.get('page', '?'))
        br = r.get('ballots_received')
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        rv = r.get('registered_voters')
        to = r.get('turnout')
        tv = r.get('total_votes')

        # Check 1: ballot equation
        if all(x is not None for x in [br, vb, ib, nv, rb]):
            calc = vb + ib + nv + rb
            if calc != br:
                diff = br - calc
                results['ballot_eq'].append({
                    'id': rid, 'br': br, 'vb': vb, 'ib': ib, 'nv': nv, 'rb': rb,
                    'calc': calc, 'diff': diff, 'record': r,
                })

        # Check 2: turnout > registered
        if rv is not None and to is not None and to > rv:
            results['turnout_over'].append({
                'id': rid, 'registered': rv, 'turnout': to, 'diff': to - rv,
            })

        # Check 3: total_votes vs sum(candidate votes)
        cands = r.get('candidates', [])
        if tv is not None and cands:
            cv = [c.get('votes') for c in cands if c.get('votes') is not None]
            if cv:
                s = sum(cv)
                if s != tv:
                    results['tv_vs_cands'].append({
                        'id': rid, 'total_votes': tv, 'sum_cands': s, 'diff': tv - s,
                        'n_cands': len(cands), 'n_with_votes': len(cv),
                    })

        # Check 4: total_votes > valid_ballots
        if tv is not None and vb is not None and tv > vb:
            results['tv_over_valid'].append({
                'id': rid, 'total_votes': tv, 'valid_ballots': vb, 'diff': tv - vb,
            })

        # Check 5: negative values
        for f in BALLOT_FIELDS:
            val = r.get(f)
            if val is not None and isinstance(val, (int, float)) and val < 0:
                results['negative_vals'].append({'id': rid, 'field': f, 'value': val})

    # Report
    checks = [
        ('ballot_eq', 'Ballot equation (br != vb+ib+nv+rb)'),
        ('turnout_over', 'Turnout > registered voters'),
        ('tv_vs_cands', 'total_votes != sum(candidate votes)'),
        ('tv_over_valid', 'total_votes > valid_ballots'),
        ('negative_vals', 'Negative values'),
    ]

    total_checked = len(with_data)
    print("  Records with ballot data: %d\n" % total_checked)

    for key, label in checks:
        items = results[key]
        pct = 100 * len(items) / total_checked if total_checked else 0
        status = "PASS" if len(items) == 0 else ("WARN" if pct < 5 else "FAIL")
        print("  [%s] %s: %d (%.1f%%)" % (status, label, len(items), pct))
        # Show top 3 examples
        for item in items[:3]:
            detail = {k: v for k, v in item.items() if k not in ('record',)}
            print("         %s" % detail)
        if len(items) > 3:
            print("         ... +%d more" % (len(items) - 3))

    # Deeper analysis on ballot_eq
    if results['ballot_eq']:
        diffs = [abs(x['diff']) for x in results['ballot_eq']]
        print("\n  Ballot equation diff stats:")
        print("    min=%d, max=%d, median=%d, mean=%.0f" % (
            min(diffs), max(diffs), sorted(diffs)[len(diffs) // 2], sum(diffs) / len(diffs)))
        # Distribution
        buckets = Counter()
        for d in diffs:
            if d <= 1:
                buckets['0-1'] += 1
            elif d <= 5:
                buckets['2-5'] += 1
            elif d <= 20:
                buckets['6-20'] += 1
            elif d <= 100:
                buckets['21-100'] += 1
            else:
                buckets['100+'] += 1
        print("    distribution: %s" % dict(buckets))

    # Deeper analysis on tv_vs_cands
    if results['tv_vs_cands']:
        print("\n  total_votes vs sum(cands) breakdown:")
        # How many have missing candidate votes?
        missing_votes = sum(1 for x in results['tv_vs_cands'] if x['n_cands'] != x['n_with_votes'])
        all_have_votes = sum(1 for x in results['tv_vs_cands'] if x['n_cands'] == x['n_with_votes'])
        print("    Some candidates have no votes: %d" % missing_votes)
        print("    All candidates have votes (genuine mismatch): %d" % all_have_votes)

    return results


def analyze_candidates(front):
    """Analyze candidate data quality."""
    print("\n" + "=" * 60)
    print("4. CANDIDATE ANALYSIS")
    print("=" * 60)

    # Load ECT reference
    ect_path = os.path.join(DATA_DIR, 'ect_candidates_reference.json')
    ect_ref = {}
    if os.path.exists(ect_path):
        with open(ect_path, 'r', encoding='utf-8') as f:
            ect_ref = json.load(f)

    bk = [r for r in front if r.get('vote_type') == '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15']
    print("  \u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15 records: %d" % len(bk))

    if not ect_ref:
        print("  No ECT reference found, skipping candidate validation")
        return

    prov_ref = ect_ref.get('\u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34', {})
    print("  ECT zones: %s" % sorted(prov_ref.keys(), key=int))

    # Check each constituency
    mismatch_details = []
    for r in bk:
        cons = r.get('constituency')
        if cons is None:
            continue
        cons_str = str(cons)
        ect_cands = prov_ref.get(cons_str, [])
        if not ect_cands:
            continue

        ocr_cands = r.get('candidates', [])
        ect_count = len(ect_cands)
        ocr_count = len(ocr_cands)

        if ocr_count != ect_count:
            mismatch_details.append({
                'file': r.get('file', '')[-50:],
                'page': r.get('page'),
                'cons': cons,
                'ect': ect_count,
                'ocr': ocr_count,
                'diff': ocr_count - ect_count,
            })

    print("\n  Candidate count mismatch (OCR vs ECT): %d" % len(mismatch_details))
    if mismatch_details:
        # Distribution by diff
        diff_counter = Counter(x['diff'] for x in mismatch_details)
        print("  Diff distribution: %s" % dict(sorted(diff_counter.items())))

        # By constituency
        cons_counter = Counter(x['cons'] for x in mismatch_details)
        print("  By constituency:")
        for c, cnt in sorted(cons_counter.items()):
            ect_n = len(prov_ref.get(str(c), []))
            print("    zone %s (ECT=%d): %d mismatches" % (c, ect_n, cnt))

        # Show worst examples
        print("\n  Worst mismatches:")
        worst = sorted(mismatch_details, key=lambda x: abs(x['diff']), reverse=True)[:5]
        for w in worst:
            print("    zone %s p%s: OCR=%d ECT=%d (diff=%+d)" % (
                w['cons'], w['page'], w['ocr'], w['ect'], w['diff']))

    # Check for null votes in candidates
    null_votes = 0
    total_cands = 0
    for r in bk:
        for c in r.get('candidates', []):
            total_cands += 1
            if c.get('votes') is None:
                null_votes += 1
    print("\n  Candidate votes: %d total, %d null (%.1f%%)" % (
        total_cands, null_votes, 100 * null_votes / total_cands if total_cands else 0))


def generate_report(front, no_data, with_data, math_results):
    """Generate a JSON report for review app consumption."""
    flagged = []

    # Flag records with ballot math errors
    for item in math_results.get('ballot_eq', []):
        rec = item.get('record', {})
        flagged.append({
            'file': rec.get('file', ''),
            'page': rec.get('page'),
            'issue': 'ballot_equation',
            'detail': 'br=%s != vb+ib+nv+rb=%s (diff=%s)' % (item['br'], item['calc'], item['diff']),
            'severity': 'high' if abs(item['diff']) > 10 else 'medium',
        })

    for item in math_results.get('turnout_over', []):
        flagged.append({
            'file': item['id'],
            'page': None,
            'issue': 'turnout_over_registered',
            'detail': 'turnout=%s > registered=%s' % (item['turnout'], item['registered']),
            'severity': 'high',
        })

    for item in math_results.get('tv_over_valid', []):
        flagged.append({
            'file': item['id'],
            'page': None,
            'issue': 'total_votes_over_valid',
            'detail': 'total_votes=%s > valid=%s' % (item['total_votes'], item['valid_ballots']),
            'severity': 'medium',
        })

    report_path = os.path.join(DATA_DIR, 'validation_chaiyaphum.json')
    report = {
        'province': 'chaiyaphum',
        'total_front_pages': len(front),
        'with_ballot_data': len(with_data),
        'no_ballot_data': len(no_data),
        'ballot_eq_errors': len(math_results.get('ballot_eq', [])),
        'turnout_errors': len(math_results.get('turnout_over', [])),
        'tv_cand_mismatches': len(math_results.get('tv_vs_cands', [])),
        'tv_over_valid': len(math_results.get('tv_over_valid', [])),
        'flagged_count': len(flagged),
        'flagged': flagged[:500],  # limit size
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n  Saved validation report: %s (%d flagged items)" % (report_path, len(flagged)))


def main():
    print("Loading Chaiyaphum OCR data...")
    ocr = load_data()
    front = [r for r in ocr if not r.get('is_back_page')]
    print("Total: %d records, %d front pages, %d back pages\n" % (
        len(ocr), len(front), len(ocr) - len(front)))

    # Task 2: Coverage
    analyze_coverage(front)

    # Task 3: No ballot data
    no_data, with_data = analyze_no_ballot_data(front)

    # Task 2: Ballot math
    math_results = validate_ballot_math(with_data)

    # Task 4: Candidates
    analyze_candidates(front)

    # Generate JSON report
    generate_report(front, no_data, with_data, math_results)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  Front pages:      %d" % len(front))
    print("  With ballot data: %d (%.0f%%)" % (len(with_data), 100 * len(with_data) / len(front)))
    print("  No ballot data:   %d (%.0f%% - mostly party-list)" % (len(no_data), 100 * len(no_data) / len(front)))
    n_errors = (len(math_results['ballot_eq']) + len(math_results['turnout_over'])
                + len(math_results['tv_over_valid']))
    print("  Math errors:      %d (%.1f%% of records with data)" % (
        n_errors, 100 * n_errors / len(with_data) if with_data else 0))
    print("  Cand vote mismatch: %d" % len(math_results['tv_vs_cands']))


if __name__ == '__main__':
    main()
