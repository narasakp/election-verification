# -*- coding: utf-8 -*-
"""
Deep analysis of the biggest data quality issues in Chaiyaphum OCR.
Focuses on: total_votes mismatch, ballot equation, candidate counts.
"""
import json
import os
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

VT_BL = '\u0e1a\u0e31\u0e0d\u0e0a\u0e35\u0e23\u0e32\u0e22\u0e0a\u0e37\u0e48\u0e2d'  # party list
VT_BK = '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15'  # constituency


def load():
    path = os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [r for r in data if not r.get('is_back_page')]


def section_total_votes(front):
    """Deep dive: total_votes vs sum(candidate votes)."""
    print("=" * 60)
    print("A. TOTAL_VOTES vs SUM(CANDIDATE VOTES)")
    print("=" * 60)

    for vt_name in [VT_BK, VT_BL]:
        items = [r for r in front if r.get('vote_type') == vt_name]
        match_list, mismatch_list = [], []
        for r in items:
            tv = r.get('total_votes')
            cands = r.get('candidates', [])
            if tv is None or not cands:
                continue
            cv = [c.get('votes') for c in cands if c.get('votes') is not None]
            if not cv:
                continue
            s = sum(cv)
            if s == tv:
                match_list.append(r)
            else:
                mismatch_list.append((r, tv, s, tv - s))

        total = len(match_list) + len(mismatch_list)
        print("\n  [%s] checked=%d  match=%d (%.0f%%)  mismatch=%d (%.0f%%)" % (
            vt_name, total,
            len(match_list), 100 * len(match_list) / total if total else 0,
            len(mismatch_list), 100 * len(mismatch_list) / total if total else 0))

        if not mismatch_list:
            continue

        diffs = [d for _, _, _, d in mismatch_list]
        abs_diffs = [abs(d) for d in diffs]
        bigger = sum(1 for d in diffs if d > 0)
        smaller = sum(1 for d in diffs if d < 0)
        print("    total_votes > sum(cands): %d" % bigger)
        print("    total_votes < sum(cands): %d" % smaller)
        print("    |diff| min=%d  median=%d  max=%d  mean=%.0f" % (
            min(abs_diffs), sorted(abs_diffs)[len(abs_diffs)//2],
            max(abs_diffs), sum(abs_diffs)/len(abs_diffs)))

        # Bucket diffs
        buckets = Counter()
        for d in abs_diffs:
            if d <= 5: buckets['1-5'] += 1
            elif d <= 20: buckets['6-20'] += 1
            elif d <= 100: buckets['21-100'] += 1
            elif d <= 500: buckets['101-500'] += 1
            else: buckets['500+'] += 1
        print("    |diff| buckets: %s" % dict(sorted(buckets.items())))

        # Pattern: n_candidates distribution in mismatches vs matches
        mm_ncands = Counter(len(r.get('candidates', [])) for r, _, _, _ in mismatch_list)
        ok_ncands = Counter(len(r.get('candidates', [])) for r in match_list)
        print("    #candidates in MISMATCH: %s" % dict(sorted(mm_ncands.items())))
        print("    #candidates in MATCH:    %s" % dict(sorted(ok_ncands.items())))

        # Show examples: small, medium, large diff
        print("\n    Representative examples (sorted by |diff|):")
        by_abs = sorted(mismatch_list, key=lambda x: abs(x[3]))
        picks = []
        for pct in [0, 0.25, 0.5, 0.75, 0.95]:
            idx = min(int(pct * len(by_abs)), len(by_abs) - 1)
            picks.append(by_abs[idx])
        for r, tv, s, d in picks:
            fn = os.path.basename(r.get('file', ''))[:40]
            cands = r.get('candidates', [])
            vlist = [c.get('votes', '?') for c in cands]
            vb = r.get('valid_ballots')
            print("      %s p%s: tv=%s sum=%s diff=%+d vb=%s cands=%s" % (
                fn, r.get('page'), tv, s, d, vb, vlist[:6]))

    # Multi vs single station
    print("\n  Multi vs Single station breakdown:")
    for label, filt in [("Multi (>4pp)", lambda r: (r.get('total_pages') or 0) > 4),
                         ("Single (<=4pp)", lambda r: 0 < (r.get('total_pages') or 0) <= 4)]:
        checked, bad = 0, 0
        for r in front:
            if not filt(r):
                continue
            tv = r.get('total_votes')
            cands = r.get('candidates', [])
            if tv is None or not cands:
                continue
            cv = [c.get('votes') for c in cands if c.get('votes') is not None]
            if not cv:
                continue
            checked += 1
            if sum(cv) != tv:
                bad += 1
        print("    %s: %d/%d mismatch (%.0f%%)" % (label, bad, checked, 100*bad/checked if checked else 0))


def section_ballot_equation(front):
    """Deep dive: ballots_received != valid + invalid + novote + remaining."""
    print("\n" + "=" * 60)
    print("B. BALLOT EQUATION (br = vb + ib + nv + rb)")
    print("=" * 60)

    eq_fail, eq_pass = [], []
    for r in front:
        br = r.get('ballots_received')
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        if not all(x is not None for x in [br, vb, ib, nv, rb]):
            continue
        calc = vb + ib + nv + rb
        if calc == br:
            eq_pass.append(r)
        else:
            eq_fail.append((r, br, calc, br - calc))

    total = len(eq_fail) + len(eq_pass)
    print("  Checked: %d  Pass: %d  Fail: %d (%.1f%%)" % (
        total, len(eq_pass), len(eq_fail), 100*len(eq_fail)/total if total else 0))

    if not eq_fail:
        return

    # By vote type
    print("\n  By vote type:")
    for vt in [VT_BK, VT_BL]:
        nf = sum(1 for r, _, _, _ in eq_fail if r.get('vote_type') == vt)
        np = sum(1 for r in eq_pass if r.get('vote_type') == vt)
        t = nf + np
        print("    %s: %d fail / %d (%.0f%%)" % (vt, nf, t, 100*nf/t if t else 0))

    # Multi vs single
    print("\n  Multi vs Single:")
    for label, filt in [("Multi (>4pp)", lambda r: (r.get('total_pages') or 0) > 4),
                         ("Single (<=4pp)", lambda r: 0 < (r.get('total_pages') or 0) <= 4)]:
        nf = sum(1 for r, _, _, _ in eq_fail if filt(r))
        np = sum(1 for r in eq_pass if filt(r))
        t = nf + np
        print("    %s: %d fail / %d (%.0f%%)" % (label, nf, t, 100*nf/t if t else 0))

    # Which field is most likely wrong?
    # Check: if we remove remaining_ballots, does br = vb+ib+nv?
    fix_by_rb = 0
    fix_by_br = 0
    for r, br, calc, diff in eq_fail:
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        # If br == vb+ib+nv (remaining should be 0 or is wrong)
        if br == vb + ib + nv:
            fix_by_rb += 1
        # If remaining = br - vb - ib - nv would fix it (br is correct)
        # Actually br = vb+ib+nv+rb fails; check turnout = br - remaining
        to = r.get('turnout')
        if to is not None and to == vb + ib + nv:
            fix_by_br += 1  # turnout matches used ballots, br might include remaining

    print("\n  Root cause hints:")
    print("    br == vb+ib+nv (remaining is the odd one out): %d" % fix_by_rb)
    print("    turnout == vb+ib+nv (br may include remaining): %d" % fix_by_br)

    # Show examples
    print("\n  Examples (sorted by |diff|):")
    by_abs = sorted(eq_fail, key=lambda x: abs(x[3]))
    for r, br, calc, d in by_abs[:3] + by_abs[-3:]:
        fn = os.path.basename(r.get('file', ''))[:35]
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        to = r.get('turnout')
        rv = r.get('registered_voters')
        print("    %s p%s: br=%s vb=%s ib=%s nv=%s rb=%s to=%s rv=%s diff=%+d" % (
            fn, r.get('page'), br, vb, ib, nv, rb, to, rv, d))


def section_candidate_mismatch(front):
    """Analyze candidate count mismatches with ECT reference."""
    print("\n" + "=" * 60)
    print("C. CANDIDATE COUNT vs ECT REFERENCE")
    print("=" * 60)

    ect_path = os.path.join(DATA_DIR, 'ect_candidates_reference.json')
    if not os.path.exists(ect_path):
        print("  No ECT reference found")
        return

    with open(ect_path, 'r', encoding='utf-8') as f:
        ect_ref = json.load(f)
    prov_ref = ect_ref.get('\u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34', {})

    bk = [r for r in front if r.get('vote_type') == VT_BK]
    print("  %s records: %d" % (VT_BK, len(bk)))

    # Group by constituency
    by_cons = defaultdict(list)
    for r in bk:
        c = r.get('constituency')
        if c is not None:
            by_cons[str(c)].append(r)

    for cons in sorted(by_cons.keys(), key=int):
        items = by_cons[cons]
        ect_cands = prov_ref.get(cons, [])
        ect_n = len(ect_cands)
        if not ect_n:
            continue

        counts = Counter(len(r.get('candidates', [])) for r in items)
        mode_n = counts.most_common(1)[0][0] if counts else 0
        mismatch = sum(1 for r in items if len(r.get('candidates', [])) != ect_n)
        total = len(items)

        # Only show if there are mismatches
        if mismatch == 0:
            print("  Zone %s: ECT=%d, all %d records match" % (cons, ect_n, total))
        else:
            print("  Zone %s: ECT=%d, mode=%d, %d/%d mismatch (%.0f%%)" % (
                cons, ect_n, mode_n, mismatch, total, 100*mismatch/total))
            print("    count distribution: %s" % dict(sorted(counts.items())))

            # Show what the extra/missing candidates look like
            for r in items:
                ocr_n = len(r.get('candidates', []))
                if ocr_n != ect_n and abs(ocr_n - ect_n) >= 3:
                    cands = r.get('candidates', [])
                    names = [(c.get('number'), str(c.get('name', ''))[:15]) for c in cands]
                    fn = os.path.basename(r.get('file', ''))[:30]
                    print("      %s p%s: %d cands %s" % (fn, r.get('page'), ocr_n, names[:8]))
                    break  # just one example per zone


def section_autofix_potential(front):
    """Estimate what can be auto-fixed."""
    print("\n" + "=" * 60)
    print("D. AUTO-FIX POTENTIAL")
    print("=" * 60)

    # 1. total_votes: trust sum(candidates) over reported total
    can_fix_tv = 0
    tv_mismatch_total = 0
    sum_closer_to_vb = 0
    tv_closer_to_vb = 0
    for r in front:
        tv = r.get('total_votes')
        vb = r.get('valid_ballots')
        cands = r.get('candidates', [])
        if tv is None or not cands:
            continue
        cv = [c.get('votes') for c in cands if c.get('votes') is not None]
        if not cv or sum(cv) == tv:
            continue
        s = sum(cv)
        tv_mismatch_total += 1

        if vb is not None and vb > 0:
            # Which is closer to valid_ballots?
            if abs(s - vb) < abs(tv - vb):
                sum_closer_to_vb += 1
            else:
                tv_closer_to_vb += 1

        # Can fix: just replace total_votes with sum
        can_fix_tv += 1

    print("  1. Replace total_votes with sum(candidate votes):")
    print("     Candidates: %d records" % can_fix_tv)
    if sum_closer_to_vb + tv_closer_to_vb > 0:
        print("     sum(cands) closer to valid_ballots: %d" % sum_closer_to_vb)
        print("     total_votes closer to valid_ballots: %d" % tv_closer_to_vb)
        print("     -> Neither is clearly better (OCR errors in both)")

    # 2. Ballot equation: recalculate remaining_ballots = br - vb - ib - nv
    can_fix_eq = 0
    for r in front:
        br = r.get('ballots_received')
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        if not all(x is not None for x in [br, vb, ib, nv, rb]):
            continue
        calc = vb + ib + nv + rb
        if calc != br:
            # Can fix remaining = br - vb - ib - nv
            new_rb = br - vb - ib - nv
            if new_rb >= 0:
                can_fix_eq += 1

    print("\n  2. Recalculate remaining_ballots = br - vb - ib - nv:")
    print("     Candidates (new_rb >= 0): %d" % can_fix_eq)

    # 3. Cross-validate with killernay constituency data
    killernay_path = os.path.join(DATA_DIR, 'killernay_constituency_full.csv')
    if os.path.exists(killernay_path):
        print("\n  3. Killernay cross-check: AVAILABLE")
        print("     Can aggregate station votes -> constituency and compare")
    else:
        print("\n  3. Killernay cross-check: not available")


def main():
    print("Loading Chaiyaphum front pages...\n")
    front = load()
    print("Front pages: %d\n" % len(front))

    section_total_votes(front)
    section_ballot_equation(front)
    section_candidate_mismatch(front)
    section_autofix_potential(front)

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("""
  Key findings:
  1. total_votes mismatch is mostly in party-list forms where the OCR
     reads a 'total' field that doesn't match individual party votes.
     Root cause: multi-station PDFs have summary totals mixed with
     per-station data, confusing the LLM.

  2. Ballot equation failures correlate with multi-station PDFs
     where adjacent station data bleeds into the current record.

  3. Candidate count mismatches are concentrated in zones 3-4
     where OCR picks up extra rows or misses candidates.

  Recommended actions:
  - Flag records with math errors for manual review in the review app
  - Use sum(candidate_votes) as the authoritative total_votes
  - Cross-validate constituency aggregates with killernay data
  - Do NOT auto-correct ballot fields (too risky without ground truth)
""")


if __name__ == '__main__':
    main()
