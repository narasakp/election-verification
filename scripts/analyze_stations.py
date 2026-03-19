# -*- coding: utf-8 -*-
"""
Station-level anomaly detection & cross-validation with killernay data.

Checks:
  1. Ballot reconciliation: บัตรรับ = บัตรดี + บัตรเสีย + ไม่เลือกใคร + บัตรเหลือ
  2. Turnout consistency: มาแสดงตน ≤ ผู้มีสิทธิ์
  3. Vote total check: รวมคะแนนผู้สมัคร ≤ บัตรดี
  4. Cross-validate: sum station votes per constituency vs killernay
  5. Benford's Law on first digits

Usage:
  python scripts/analyze_stations.py
  python scripts/analyze_stations.py --province tak
"""
import argparse
import collections
import csv
import glob
import json
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Expected Benford distribution for first digits 1-9
BENFORD_EXPECTED = {d: math.log10(1 + 1/d) for d in range(1, 10)}


def load_ocr_results(province_slug=None):
    if province_slug:
        pattern = os.path.join(DATA_DIR, f'ocr_vision_{province_slug}.json')
    else:
        pattern = os.path.join(DATA_DIR, 'ocr_vision_*.json')
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No OCR files found: {pattern}")
        return []
    results = []
    for f in files:
        slug = os.path.basename(f).replace('ocr_vision_', '').replace('.json', '')
        with open(f, 'r', encoding='utf-8') as fh:
            items = json.load(fh)
        for item in items:
            item['_slug'] = slug
        results.extend(items)
        print(f"  {os.path.basename(f)}: {len(items)} items")
    content = [r for r in results if not r.get('is_back_page', False)]
    print(f"Loaded {len(content)} content pages (filtered {len(results)-len(content)} back pages)\n")
    return content


def load_killernay():
    path = os.path.join(DATA_DIR, 'killernay_constituency.csv')
    if not os.path.exists(path):
        print("killernay CSV not found, skipping cross-validation")
        return {}
    data = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = (row['จังหวัด'], int(row['เขต']))
            if key not in data:
                data[key] = {'candidates': {}, 'total_votes': 0}
            votes = int(row['คะแนน'] or 0)
            data[key]['candidates'][row['ชื่อผู้สมัคร']] = votes
            data[key]['total_votes'] += votes
    print(f"killernay: {len(data)} constituencies\n")
    return data


# ── 1. Ballot Reconciliation ──────────────────────────────────────────

def check_ballot_reconciliation(items):
    print("=" * 70)
    print("1. Ballot Reconciliation")
    print("   บัตรที่ได้รับ = บัตรดี + บัตรเสีย + ไม่เลือกใคร + บัตรเหลือ")
    print("=" * 70)
    checked, mismatches = 0, []
    for item in items:
        r = item.get('ballots_received')
        v = item.get('valid_ballots')
        i = item.get('invalid_ballots')
        n = item.get('no_vote_ballots')
        m = item.get('remaining_ballots')
        if any(x is None for x in [r, v, i, n, m]):
            continue
        checked += 1
        expected = v + i + n + m
        if r != expected:
            mismatches.append({
                'file': item.get('file', ''), 'page': item.get('page'),
                'province': item.get('province', ''),
                'constituency': item.get('constituency', ''),
                'station': item.get('ocr_station_no', ''),
                'received': r, 'valid': v, 'invalid': i,
                'no_vote': n, 'remaining': m,
                'expected': expected, 'diff': r - expected,
            })
    print(f"  Checked: {checked} stations")
    print(f"  Mismatches: {len(mismatches)}")
    for m in sorted(mismatches, key=lambda x: abs(x['diff']), reverse=True)[:15]:
        print(f"    {m['province']} เขต{m['constituency']} หน่วย{m['station']}: "
              f"รับ={m['received']} != ดี{m['valid']}+เสีย{m['invalid']}"
              f"+ไม่เลือก{m['no_vote']}+เหลือ{m['remaining']}={m['expected']} "
              f"(diff={m['diff']:+d})")
    print()
    return mismatches


# ── 2. Turnout Anomalies ──────────────────────────────────────────────

def check_turnout(items):
    print("=" * 70)
    print("2. Turnout Anomaly Check")
    print("=" * 70)
    checked = 0
    over_100, high, low = [], [], []
    for item in items:
        voters = item.get('registered_voters')
        turnout = item.get('turnout')
        if not voters or not turnout or voters == 0:
            continue
        checked += 1
        pct = turnout / voters * 100
        rec = {
            'province': item.get('province', ''),
            'constituency': item.get('constituency', ''),
            'station': item.get('ocr_station_no', ''),
            'voters': voters, 'turnout': turnout, 'pct': pct,
            'file': item.get('file', ''),
        }
        if turnout > voters:
            over_100.append(rec)
        if pct > 95:
            high.append(rec)
        elif pct < 30:
            low.append(rec)
    print(f"  Checked: {checked} stations")
    print(f"  Turnout > 100%: {len(over_100)}")
    print(f"  Turnout > 95%: {len(high)}")
    print(f"  Turnout < 30%: {len(low)}")
    if over_100:
        print("  --- Turnout > 100% ---")
        for t in over_100[:10]:
            print(f"    {t['province']} เขต{t['constituency']} หน่วย{t['station']}: "
                  f"{t['turnout']}/{t['voters']} = {t['pct']:.1f}%")
    print()
    return {'over_100': over_100, 'high': high, 'low': low}


# ── 3. Vote Total vs Valid Ballots ────────────────────────────────────

def check_vote_totals(items):
    print("=" * 70)
    print("3. Candidate Vote Sum vs Valid Ballots")
    print("=" * 70)
    checked, issues = 0, []
    for item in items:
        cands = item.get('candidates', [])
        valid = item.get('valid_ballots')
        cand_votes = [c['votes'] for c in cands if c.get('votes') is not None]
        if not cand_votes or valid is None:
            continue
        checked += 1
        total = sum(cand_votes)
        if total > valid:
            issues.append({
                'province': item.get('province', ''),
                'constituency': item.get('constituency', ''),
                'station': item.get('ocr_station_no', ''),
                'valid': valid, 'total_cand': total, 'diff': total - valid,
                'file': item.get('file', ''),
            })
    print(f"  Checked: {checked} stations")
    print(f"  Candidate votes > valid ballots: {len(issues)}")
    for m in sorted(issues, key=lambda x: x['diff'], reverse=True)[:10]:
        print(f"    {m['province']} เขต{m['constituency']} หน่วย{m['station']}: "
              f"sum={m['total_cand']} > valid={m['valid']} (+{m['diff']})")
    print()
    return issues


# ── 4. Cross-validate with killernay ──────────────────────────────────

def cross_validate(items, killernay):
    print("=" * 70)
    print("4. Cross-Validation: Station Sum vs killernay Constituency")
    print("=" * 70)
    if not killernay:
        print("  Skipped (no killernay data)\n")
        return {}

    # Aggregate our data by constituency
    agg = {}
    for item in items:
        prov = item.get('province')
        const = item.get('constituency')
        if not prov or not const:
            continue
        key = (prov, int(const))
        if key not in agg:
            agg[key] = {'stations': 0, 'total_votes': 0, 'cand_votes': collections.Counter()}
        agg[key]['stations'] += 1
        for c in item.get('candidates', []):
            if c.get('votes') is not None and c.get('name'):
                agg[key]['cand_votes'][c['name']] += c['votes']
                agg[key]['total_votes'] += c['votes']

    matched = 0
    results = []
    for key, our in agg.items():
        kn = killernay.get(key)
        if not kn:
            continue
        matched += 1
        diff = our['total_votes'] - kn['total_votes']
        pct = diff / kn['total_votes'] * 100 if kn['total_votes'] else 0
        results.append({
            'province': key[0], 'constituency': key[1],
            'our_stations': our['stations'],
            'our_total': our['total_votes'],
            'kn_total': kn['total_votes'],
            'diff': diff, 'pct': pct,
        })

    print(f"  Our constituencies: {len(agg)}")
    print(f"  Matched with killernay: {matched}")
    if results:
        print(f"\n  {'จังหวัด':<15} {'เขต':>4} {'หน่วย':>5} {'เรา':>10} {'killernay':>10} {'diff':>8} {'%':>7}")
        print(f"  {'-'*65}")
        for r in sorted(results, key=lambda x: abs(x['diff']), reverse=True):
            flag = " !!!" if abs(r['pct']) > 5 else ""
            print(f"  {r['province']:<15} {r['constituency']:>4} {r['our_stations']:>5} "
                  f"{r['our_total']:>10,} {r['kn_total']:>10,} {r['diff']:>+8,} {r['pct']:>+6.1f}%{flag}")
    print()
    return results


# ── 5. Benford's Law ──────────────────────────────────────────────────

def benford_analysis(items):
    print("=" * 70)
    print("5. Benford's Law Analysis (first digit of vote counts)")
    print("=" * 70)
    digits = collections.Counter()
    total = 0
    for item in items:
        for c in item.get('candidates', []):
            v = c.get('votes')
            if v and v > 0:
                first = int(str(v)[0])
                digits[first] += 1
                total += 1

        for field in ['registered_voters', 'turnout', 'ballots_received',
                      'valid_ballots', 'invalid_ballots', 'remaining_ballots']:
            v = item.get(field)
            if v and v > 0:
                first = int(str(v)[0])
                digits[first] += 1
                total += 1

    if total < 50:
        print(f"  Not enough data ({total} values)\n")
        return {}

    print(f"  Total values analyzed: {total}")
    print(f"\n  {'Digit':>5} {'Observed':>10} {'Expected':>10} {'Obs%':>7} {'Exp%':>7} {'Diff':>7}")
    print(f"  {'-'*50}")
    chi2 = 0
    for d in range(1, 10):
        obs = digits.get(d, 0)
        obs_pct = obs / total * 100
        exp_pct = BENFORD_EXPECTED[d] * 100
        exp_count = total * BENFORD_EXPECTED[d]
        diff = obs_pct - exp_pct
        chi2 += (obs - exp_count) ** 2 / exp_count if exp_count > 0 else 0
        bar = "#" * int(abs(diff) * 2)
        flag = " <<<" if abs(diff) > 3 else ""
        print(f"  {d:>5} {obs:>10,} {exp_count:>10,.0f} {obs_pct:>6.1f}% {exp_pct:>6.1f}% {diff:>+6.1f}% {bar}{flag}")

    # Chi-squared critical value for df=8, alpha=0.05 is 15.507
    print(f"\n  Chi-squared: {chi2:.2f} (critical value at 5%: 15.51)")
    if chi2 > 15.51:
        print("  Result: SIGNIFICANT deviation from Benford's Law")
    else:
        print("  Result: Consistent with Benford's Law")
    print()
    return {'chi2': chi2, 'digits': dict(digits), 'total': total}


# ── 6. Summary Stats ──────────────────────────────────────────────────

def summary_stats(items):
    print("=" * 70)
    print("Summary Statistics")
    print("=" * 70)
    provs = set()
    constits = set()
    with_voters = 0
    with_ballots = 0
    with_cands = 0
    total_cands = 0
    for item in items:
        if item.get('province'):
            provs.add(item['province'])
        if item.get('province') and item.get('constituency'):
            constits.add((item['province'], item['constituency']))
        if item.get('registered_voters') is not None:
            with_voters += 1
        if item.get('ballots_received') is not None:
            with_ballots += 1
        if item.get('candidates'):
            with_cands += 1
            total_cands += len(item['candidates'])

    print(f"  Content pages: {len(items)}")
    print(f"  Provinces: {len(provs)} {sorted(provs)}")
    print(f"  Constituencies: {len(constits)}")
    print(f"  With voter data: {with_voters} ({with_voters/len(items)*100:.0f}%)")
    print(f"  With ballot data: {with_ballots} ({with_ballots/len(items)*100:.0f}%)")
    print(f"  With candidates: {with_cands} ({with_cands/len(items)*100:.0f}%)")
    print(f"  Total candidate entries: {total_cands}")
    print()


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Station-level anomaly detection")
    parser.add_argument("--province", help="Province slug (e.g. tak, chaiyaphum)")
    parser.add_argument("--output", help="Save report as JSON")
    args = parser.parse_args()

    items = load_ocr_results(args.province)
    if not items:
        sys.exit(1)

    killernay = load_killernay()

    summary_stats(items)
    ballot_issues = check_ballot_reconciliation(items)
    turnout_issues = check_turnout(items)
    vote_issues = check_vote_totals(items)
    xval = cross_validate(items, killernay)
    benford = benford_analysis(items)

    # Save report
    if args.output:
        report = {
            'total_pages': len(items),
            'ballot_mismatches': len(ballot_issues),
            'turnout_over_100': len(turnout_issues['over_100']),
            'turnout_high': len(turnout_issues['high']),
            'vote_total_issues': len(vote_issues),
            'cross_validation': xval,
            'benford_chi2': benford.get('chi2'),
            'ballot_issues': ballot_issues[:50],
            'turnout_issues_over100': turnout_issues['over_100'][:50],
            'vote_issues': vote_issues[:50],
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Report saved to {args.output}")


if __name__ == '__main__':
    main()
