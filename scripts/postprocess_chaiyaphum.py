# -*- coding: utf-8 -*-
"""
Post-process Chaiyaphum OCR data: fix what can be fixed, flag what can't.

Fixes applied:
  R0. Override constituency/province/vote_type from file path metadata (ground truth)
  R1. total_votes = sum(candidate_votes) when they disagree
  R2. remaining_ballots = ballots_received - valid - invalid - novote (if >= 0)
  R3. Negative values -> None
  R4. Outlier values -> None (e.g. valid_ballots > 10000 for a single station)
  R5. Flag: turnout > registered_voters
  R6. Cross-validate constituency totals with killernay ground truth
  R7. Normalize candidates against ECT reference (remove extras from adjacent stations)

Usage:
  python scripts/postprocess_chaiyaphum.py
  python scripts/postprocess_chaiyaphum.py --dry-run   # preview only
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

BALLOT_FIELDS = [
    'registered_voters', 'turnout', 'ballots_received',
    'valid_ballots', 'invalid_ballots', 'no_vote_ballots',
    'remaining_ballots', 'total_votes',
]

# Reasonable upper bound per station (largest stations have ~3000 voters)
MAX_STATION_VALUE = 10000


def fix_metadata_from_filepath(records, stats):
    """R0: Override constituency/province/vote_type from file path.

    The file path (e.g. จังหวัดชัยภูมิ/เขตเลือกตั้งที่ 7/...-แบ่งเขต-...)
    is ground truth. OCR often misreads constituency numbers.
    """
    fixed_cons = 0
    fixed_prov = 0
    fixed_vt = 0

    for r in records:
        fl = r.get('file', '')
        if not fl:
            continue

        # Extract constituency from file path
        m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', fl)
        if m:
            file_cons = int(m.group(1))
            if r.get('constituency') != file_cons:
                r['_original_constituency'] = r.get('constituency')
                r['constituency'] = file_cons
                fixed_cons += 1

        # Extract province from file path
        m = re.search(r'จังหวัด([^/\\]+)', fl)
        if m:
            file_prov = m.group(1).strip()
            if r.get('province') != file_prov:
                r['province'] = file_prov
                fixed_prov += 1

        # Extract vote_type from filepath
        # Strategy: use basename first, but handle combined files
        # Combined file pattern: 'ต.XXX-แบ่งเขต/บัญชีรายชื่อ.pdf'
        #   → folder says แบ่งเขต, basename says บัญชีรายชื่อ
        #   → content is 99.8% แบ่งเขต, so folder is correct
        norm_path = fl.replace('\\', '/') if fl else ''
        fn = norm_path.split('/')[-1]
        parent = '/'.join(norm_path.split('/')[:-1])

        # Detect combined file: both keywords in path
        has_bk_in_path = 'แบ่งเขต' in norm_path
        has_bn_in_path = 'บัญชีรายชื่อ' in norm_path
        is_combined = has_bk_in_path and has_bn_in_path

        if is_combined:
            # Combined file: use candidate count to distinguish pages
            # แบ่งเขต typically has ≤10 candidates, บัญชีรายชื่อ has many more
            cands = r.get('candidates', [])
            n_cands = len(cands)
            if n_cands > 10:
                file_vt = 'บัญชีรายชื่อ'
            elif 'แบ่งเขต' in parent:
                file_vt = 'แบ่งเขต'
            else:
                file_vt = 'บัญชีรายชื่อ'
        elif 'บัญชีรายชื่อ' in fn:
            file_vt = 'บัญชีรายชื่อ'
        elif 'แบ่งเขต' in fn:
            file_vt = 'แบ่งเขต'
        else:
            # Fallback: check full path if filename has no indicator
            if 'แบ่งเขต' in fl and 'บัญชีรายชื่อ' not in fl:
                file_vt = 'แบ่งเขต'
            elif 'บัญชีรายชื่อ' in fl:
                file_vt = 'บัญชีรายชื่อ'
            else:
                file_vt = None
        if file_vt and r.get('vote_type') != file_vt:
            r['vote_type'] = file_vt
            fixed_vt += 1

    stats['R0_constituency_fixed'] = fixed_cons
    stats['R0_province_fixed'] = fixed_prov
    stats['R0_vote_type_fixed'] = fixed_vt
    print("  R0 metadata from filepath: cons=%d prov=%d vtype=%d fixed" % (
        fixed_cons, fixed_prov, fixed_vt))


def dedup_interleaved(records, stats):
    """R0d: Fix interleaved pages in multi-station PDFs.
    Combined files (แบ่งเขต/บัญชีรายชื่อ) often have alternating pages for the same
    station: one แบ่งเขต page (high votes) and one บัญชีรายชื่อ page (low votes).
    Both get classified as แบ่งเขต. This rule detects same-(file, station_no, vote_type)
    duplicates and reclassifies the lower-vote record as บัญชีรายชื่อ.
    """
    from collections import defaultdict
    by_key = defaultdict(list)
    for i, r in enumerate(records):
        if r.get('is_back_page') or not r.get('candidates'):
            continue
        fl = r.get('file', '')
        # Only apply to combined files — in non-combined multi-station PDFs,
        # same station_no from different tambons are different physical stations
        if 'แบ่งเขต' not in fl or 'บัญชีรายชื่อ' not in fl:
            continue
        stn = r.get('station_no')
        vt = r.get('vote_type', '')
        if fl and stn and vt:
            by_key[(fl, stn, vt)].append(i)

    reclassified = 0
    for key, indices in by_key.items():
        if len(indices) <= 1:
            continue
        # Sort by total_votes descending — keep highest, reclassify rest
        idx_tv = [(i, records[i].get('total_votes') or 0) for i in indices]
        idx_tv.sort(key=lambda x: -x[1])
        for i, tv in idx_tv[1:]:  # skip the best one
            if key[2] == 'แบ่งเขต':
                records[i]['vote_type'] = 'บัญชีรายชื่อ'
                records[i]['_interleaved_reclassified'] = True
                reclassified += 1

    stats['R0d_interleaved_reclassified'] = reclassified
    if reclassified:
        print("  R0d interleaved dedup: %d records reclassified แบ่งเขต→บัญชีรายชื่อ" % reclassified)


def dedup_records(records, stats):
    """R0c: Remove duplicate records with same (file, page).
    Some files were OCR'd multiple times, creating exact duplicates.
    Keeps the first occurrence (which typically has better quality).
    """
    seen = set()
    to_remove = []
    for i, r in enumerate(records):
        key = (r.get('file', ''), r.get('page'))
        if key in seen:
            to_remove.append(i)
        else:
            seen.add(key)

    # Remove in reverse order to preserve indices
    for i in reversed(to_remove):
        records.pop(i)

    stats['R0c_duplicates_removed'] = len(to_remove)
    print("  R0c dedup (file+page): %d duplicates removed, %d remaining" % (
        len(to_remove), len(records)))


def fix_station_no_from_filepath(records, stats):
    """R0b: Derive station_no from filename 'หน่วยที่ X-Y' + page position.

    Pattern: each station occupies a fixed number of pages:
      - แบ่งเขต: 2 pages/station (front + back)
      - บัญชีรายชื่อ: 4 pages/station
    Formula: station_no = (page - 1) // pages_per_station + start

    For files without 'หน่วยที่ X-Y', assume start=1 if total_pages
    is consistent with pages_per_station.
    """
    fixed_from_range = 0
    fixed_from_infer = 0
    already_set = 0
    skipped = 0

    for r in records:
        page = r.get('page')
        if not page or not isinstance(page, (int, float)):
            skipped += 1
            continue
        page = int(page)

        # Determine pages per station from vote_type
        vt = r.get('vote_type', '')
        if 'แบ่งเขต' in vt:
            pps = 2
        elif 'บัญชีรายชื่อ' in vt:
            pps = 4
        else:
            skipped += 1
            continue

        fl = r.get('file', '')

        # Try to extract range from filename
        m = re.search(r'หน่วยที่\s*(\d+)\s*-\s*(\d+)', fl)
        if m:
            sta_start = int(m.group(1))
            sta_end = int(m.group(2))
        else:
            # Infer: assume start=1, derive end from total_pages
            total = r.get('total_pages')
            if total and isinstance(total, (int, float)) and int(total) >= pps:
                sta_start = 1
                sta_end = int(total) // pps
            else:
                skipped += 1
                continue

        # Calculate station_no
        calc_sn = (page - 1) // pps + sta_start
        # Clamp to valid range
        calc_sn = max(sta_start, min(calc_sn, sta_end))

        existing = r.get('station_no')
        if existing and isinstance(existing, (int, float)) and int(existing) > 0:
            # Already has a value — only override if it's out of range
            if sta_start <= int(existing) <= sta_end:
                already_set += 1
                continue

        r['station_no'] = calc_sn
        if m:
            fixed_from_range += 1
        else:
            fixed_from_infer += 1

    stats['R0b_station_from_range'] = fixed_from_range
    stats['R0b_station_from_infer'] = fixed_from_infer
    stats['R0b_station_already_set'] = already_set
    stats['R0b_station_skipped'] = skipped
    print("  R0b station_no from filepath: range=%d infer=%d (already=%d skip=%d)" % (
        fixed_from_range, fixed_from_infer, already_set, skipped))


def load_killernay():
    """Load killernay constituency-level ground truth for Chaiyaphum."""
    path = os.path.join(DATA_DIR, 'killernay_constituency_full.csv')
    if not os.path.exists(path):
        return {}
    result = defaultdict(dict)  # {zone: {candidate_no: votes}}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            prov = r.get('\u0e08\u0e31\u0e07\u0e2b\u0e27\u0e31\u0e14', '')
            if prov != '\u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34':
                continue
            zone = r.get('\u0e40\u0e02\u0e15', '')
            no = int(r.get('\u0e2b\u0e21\u0e32\u0e22\u0e40\u0e25\u0e02', 0))
            votes = int(r.get('\u0e04\u0e30\u0e41\u0e19\u0e19', 0))
            name = r.get('\u0e0a\u0e37\u0e48\u0e2d\u0e1c\u0e39\u0e49\u0e2a\u0e21\u0e31\u0e04\u0e23', '')
            party = r.get('\u0e1e\u0e23\u0e23\u0e04', '')
            result[zone][no] = {'votes': votes, 'name': name, 'party': party}
    return dict(result)


def fix_total_votes(records, stats):
    """R1: Replace total_votes with sum(candidate votes) when they disagree."""
    fixed = 0
    for r in records:
        if r.get('is_back_page'):
            continue
        tv = r.get('total_votes')
        cands = r.get('candidates', [])
        if not cands:
            continue
        cv = [c.get('votes') for c in cands if c.get('votes') is not None]
        if not cv:
            continue
        s = sum(cv)
        if tv is None:
            r['total_votes'] = s
            r['_fix_total_votes'] = 'set_from_sum'
            fixed += 1
        elif s != tv:
            r['_original_total_votes'] = tv
            r['total_votes'] = s
            r['_fix_total_votes'] = 'replaced_with_sum'
            fixed += 1
    stats['R1_total_votes_fixed'] = fixed
    print("  R1 total_votes = sum(cands): %d fixed" % fixed)


def fix_remaining_ballots(records, stats):
    """R2: Recalculate remaining_ballots = br - vb - ib - nv when equation fails."""
    fixed = 0
    skipped = 0
    for r in records:
        if r.get('is_back_page'):
            continue
        br = r.get('ballots_received')
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        if not all(x is not None for x in [br, vb, ib, nv, rb]):
            continue
        calc = vb + ib + nv + rb
        if calc == br:
            continue
        new_rb = br - vb - ib - nv
        if new_rb >= 0:
            r['_original_remaining_ballots'] = rb
            r['remaining_ballots'] = new_rb
            r['_fix_remaining'] = 'recalculated'
            fixed += 1
        else:
            r['_flag_ballot_equation'] = True
            r['_ballot_eq_detail'] = 'br=%s vb=%s ib=%s nv=%s rb=%s calc_rb=%s' % (
                br, vb, ib, nv, rb, new_rb)
            skipped += 1
    stats['R2_remaining_fixed'] = fixed
    stats['R2_remaining_skipped'] = skipped
    print("  R2 remaining_ballots recalc: %d fixed, %d flagged (negative)" % (fixed, skipped))


def fix_negative_values(records, stats):
    """R3: Set negative values to None."""
    fixed = 0
    for r in records:
        for f in BALLOT_FIELDS:
            val = r.get(f)
            if val is not None and isinstance(val, (int, float)) and val < 0:
                r['_original_%s' % f] = val
                r[f] = None
                r['_fix_negative'] = True
                fixed += 1
    stats['R3_negatives_removed'] = fixed
    print("  R3 negative values -> None: %d fixed" % fixed)


def fix_outliers(records, stats):
    """R4: Set impossibly large values to None (OCR misread digits)."""
    fixed = 0
    for r in records:
        if r.get('is_back_page'):
            continue
        for f in BALLOT_FIELDS:
            val = r.get(f)
            if val is not None and isinstance(val, (int, float)) and val > MAX_STATION_VALUE:
                r['_original_%s' % f] = val
                r[f] = None
                r.setdefault('_fix_outlier_fields', []).append(f)
                fixed += 1
    stats['R4_outliers_removed'] = fixed
    print("  R4 outliers (>%d) -> None: %d fixed" % (MAX_STATION_VALUE, fixed))


def load_ect_reference():
    """Load ECT candidate reference for all provinces."""
    path = os.path.join(DATA_DIR, 'ect_candidates_reference.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_candidates(records, ect_ref, stats):
    """R7: Normalize candidates against ECT reference.

    For \u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15 records:
    - Keep only candidates whose number exists in ECT for that zone
    - Remove extras (from adjacent stations in multi-station PDFs)
    - Flag records where candidates were modified
    """
    prov_ref = ect_ref.get('\u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34', {})
    if not prov_ref:
        print("  R7 candidate normalization: SKIPPED (no ECT ref for \u0e0a\u0e31\u0e22\u0e20\u0e39\u0e21\u0e34)")
        return

    fixed = 0
    removed_total = 0
    filled_total = 0
    name_remapped = 0

    for r in records:
        if r.get('is_back_page'):
            continue
        if r.get('vote_type') != '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15':
            continue

        cons = str(r.get('constituency', ''))
        if cons not in prov_ref:
            continue

        ect_cands = prov_ref[cons]
        ect_by_no = {c['no']: c for c in ect_cands}
        ect_nos = set(ect_by_no.keys())

        ocr_cands = r.get('candidates', [])
        if not ocr_cands:
            continue

        # Phase 1: Keep only candidates whose number is in ECT
        kept = []
        removed = []
        for c in ocr_cands:
            num = c.get('number')
            if num in ect_nos:
                # Override name/party with ECT ground truth
                ect = ect_by_no[num]
                c['name'] = ect['name']
                c['party'] = ect['party']
                c['_ect_matched'] = True
                kept.append(c)
            else:
                removed.append(c)

        # Phase 1.5: Name-matching fallback for unmatched OCR candidates
        # e.g. OCR reads #7 นายถวัลย์ but ECT has #8 นายถวัลย์ (no #7 exists)
        matched_nos = set(c.get('number') for c in kept)
        unmatched_ect = {no: e for no, e in ect_by_no.items() if no not in matched_nos}
        still_removed = []
        for c in removed:
            ocr_name = (c.get('name') or '').strip()
            if not ocr_name or len(ocr_name) < 4:
                still_removed.append(c)
                continue
            best_match = None
            best_overlap = 0
            for no, e in unmatched_ect.items():
                ect_name = e['name']
                # Character overlap ratio
                common = sum(1 for ch in ocr_name if ch in ect_name)
                ratio = common / max(len(ocr_name), len(ect_name), 1)
                if ratio > best_overlap:
                    best_overlap = ratio
                    best_match = no
            if best_match and best_overlap >= 0.5:
                ect = ect_by_no[best_match]
                c['_original_number'] = c.get('number')
                c['number'] = best_match
                c['name'] = ect['name']
                c['party'] = ect['party']
                c['_ect_matched'] = True
                c['_ect_name_matched'] = True
                kept.append(c)
                matched_nos.add(best_match)
                del unmatched_ect[best_match]
                name_remapped += 1
            else:
                still_removed.append(c)
        removed = still_removed

        # Phase 2: Fill missing ECT candidates with votes=None
        matched_nos = set(c.get('number') for c in kept)
        filled = 0
        for no, ect in sorted(ect_by_no.items()):
            if no not in matched_nos:
                kept.append({
                    'number': no,
                    'name': ect['name'],
                    'party': ect['party'],
                    'votes': None,
                    '_ect_matched': True,
                    '_ect_filled': True,
                })
                filled += 1

        # Phase 3: Sort by candidate number
        kept.sort(key=lambda c: (c.get('number') or 9999, str(c.get('name', ''))))

        if removed or filled:
            r['_original_candidates'] = ocr_cands
            r['candidates'] = kept
            if removed:
                r['_candidates_removed'] = len(removed)
                removed_total += len(removed)
            if filled:
                r['_candidates_filled'] = filled
                filled_total += filled
            fixed += 1

    stats['R7_records_fixed'] = fixed
    stats['R7_candidates_removed'] = removed_total
    stats['R7_candidates_filled'] = filled_total
    stats['R7_name_remapped'] = name_remapped
    print("  R7 candidate normalization: %d records fixed (%d removed, %d filled, %d name-remapped)" % (
        fixed, removed_total, filled_total, name_remapped))


def flag_turnout(records, stats):
    """R5: Flag turnout > registered_voters."""
    flagged = 0
    for r in records:
        if r.get('is_back_page'):
            continue
        rv = r.get('registered_voters')
        to = r.get('turnout')
        if rv is not None and to is not None and to > rv and rv > 0:
            r['_flag_turnout_over_registered'] = True
            r['_turnout_detail'] = 'turnout=%s > registered=%s' % (to, rv)
            flagged += 1
    stats['R5_turnout_flagged'] = flagged
    print("  R5 turnout > registered: %d flagged" % flagged)


def cross_validate_killernay(records, killernay, stats):
    """R6: Aggregate station-level votes per constituency, compare with killernay."""
    if not killernay:
        print("  R6 killernay cross-check: SKIPPED (no data)")
        return

    print("\n  R6 KILLERNAY CROSS-VALIDATION (constituency \u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15 only)")
    print("  " + "-" * 56)

    # Aggregate station votes by constituency + candidate number
    agg = defaultdict(lambda: defaultdict(int))  # {zone: {cand_no: total_votes}}
    station_count = defaultdict(int)
    for r in records:
        if r.get('is_back_page'):
            continue
        if r.get('vote_type') != '\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e02\u0e15':
            continue
        cons = r.get('constituency')
        if cons is None:
            continue
        zone = str(cons)
        cands = r.get('candidates', [])
        if not cands:
            continue
        station_count[zone] += 1
        for c in cands:
            no = c.get('number')
            v = c.get('votes')
            if no is not None and v is not None:
                agg[zone][no] += v

    total_cands_checked = 0
    total_pct_error = 0
    worst = []

    for zone in sorted(killernay.keys(), key=int):
        kn = killernay[zone]
        our = agg.get(zone, {})
        n_stations = station_count.get(zone, 0)

        print("\n  Zone %s (%d stations):" % (zone, n_stations))
        zone_errors = []
        for no in sorted(kn.keys()):
            k = kn[no]
            kv = k['votes']
            ov = our.get(no, 0)
            diff = ov - kv
            pct = 100 * diff / kv if kv > 0 else 0
            total_cands_checked += 1
            total_pct_error += abs(pct)
            marker = ''
            if abs(pct) > 20:
                marker = ' *** HIGH'
            elif abs(pct) > 5:
                marker = ' * WARN'
            name_short = k['name'][:18]
            print("    #%2d %-18s  killernay=%6d  ours=%6d  diff=%+6d (%+.1f%%)%s" % (
                no, name_short, kv, ov, diff, pct, marker))
            zone_errors.append(abs(pct))
            if abs(pct) > 20:
                worst.append((zone, no, k['name'], kv, ov, pct))

    avg_pct = total_pct_error / total_cands_checked if total_cands_checked else 0
    print("\n  Overall: %d candidates checked, avg |error| = %.1f%%" % (
        total_cands_checked, avg_pct))

    if worst:
        print("  HIGH errors (>20%%):")
        for z, no, name, kv, ov, pct in worst:
            print("    Zone %s #%d %s: killernay=%d ours=%d (%+.0f%%)" % (
                z, no, name[:20], kv, ov, pct))

    stats['R6_candidates_checked'] = total_cands_checked
    stats['R6_avg_pct_error'] = round(avg_pct, 1)
    stats['R6_high_errors'] = len(worst)


def fix_candidate_vote_outliers(records, stats):
    """R8: Detect and cap per-candidate vote outliers at station level.

    For minor candidates, OCR sometimes reads wrong fields (e.g. total_votes)
    and attributes 100-300+ votes to a candidate who should get 0-5.

    Algorithm:
      1. Group front-page แบ่งเขต records by constituency
      2. For each candidate, collect per-station votes
      3. Calculate median; if station_vote > 10*median AND > 30, cap to median
      4. Recalculate total_votes for affected records
    """
    from statistics import median as stat_median

    cons_records = defaultdict(list)
    for r in records:
        if r.get('vote_type') != 'แบ่งเขต':
            continue
        if r.get('is_back_page'):
            continue
        if not r.get('candidates'):
            continue
        cons_records[r.get('constituency', 0)].append(r)

    total_capped = 0
    total_flagged = 0

    for zone in sorted(cons_records.keys()):
        zone_recs = cons_records[zone]

        # Collect all candidate numbers in this zone
        cand_nums = set()
        for r in zone_recs:
            for c in r.get('candidates', []):
                if c.get('number'):
                    cand_nums.add(c['number'])

        for cn in sorted(cand_nums):
            # Gather per-station votes for this candidate
            station_data = []  # (record_ref, candidate_ref, votes)
            for r in zone_recs:
                for c in r.get('candidates', []):
                    if c.get('number') == cn:
                        v = c.get('votes', 0) or 0
                        station_data.append((r, c, v))
                        break

            if len(station_data) < 10:
                continue

            votes = [sd[2] for sd in station_data]
            med = stat_median(votes)
            avg = sum(votes) / len(votes)

            # Threshold: must be > 10x median AND > 30 absolute
            # Only apply to minor candidates (median < 10)
            if med >= 10:
                continue
            threshold = max(med * 10, 30)

            for rec, cand, v in station_data:
                if v > threshold:
                    cand['_original_votes'] = v
                    cand['_flag_vote_outlier'] = True
                    cand['votes'] = int(med)
                    total_capped += 1

                    # Recalculate total_votes for this record
                    cv = [c.get('votes', 0) or 0 for c in rec.get('candidates', [])
                          if c.get('votes') is not None]
                    if cv:
                        rec['total_votes'] = sum(cv)

                    total_flagged += 1

    stats['R8_vote_outliers_capped'] = total_capped
    print("  R8 candidate vote outliers: %d capped (>10x median & >30)" % total_capped)


def revalidate(records):
    """Run validation checks after fixes."""
    front = [r for r in records if not r.get('is_back_page')]
    with_data = [r for r in front if r.get('valid_ballots') is not None]

    print("\n" + "=" * 60)
    print("POST-FIX VALIDATION")
    print("=" * 60)

    # Ballot equation
    eq_fail = 0
    for r in with_data:
        br = r.get('ballots_received')
        vb = r.get('valid_ballots')
        ib = r.get('invalid_ballots')
        nv = r.get('no_vote_ballots')
        rb = r.get('remaining_ballots')
        if all(x is not None for x in [br, vb, ib, nv, rb]):
            if vb + ib + nv + rb != br:
                eq_fail += 1

    # total_votes vs sum(cands)
    tv_fail = 0
    for r in with_data:
        tv = r.get('total_votes')
        cands = r.get('candidates', [])
        if tv is None or not cands:
            continue
        cv = [c.get('votes') for c in cands if c.get('votes') is not None]
        if cv and sum(cv) != tv:
            tv_fail += 1

    # Negative values
    neg = 0
    for r in front:
        for f in BALLOT_FIELDS:
            val = r.get(f)
            if val is not None and isinstance(val, (int, float)) and val < 0:
                neg += 1

    # Turnout > registered
    to_fail = 0
    for r in with_data:
        rv = r.get('registered_voters')
        to = r.get('turnout')
        if rv is not None and to is not None and to > rv:
            to_fail += 1

    # Outliers
    outliers = 0
    for r in front:
        for f in BALLOT_FIELDS:
            val = r.get(f)
            if val is not None and isinstance(val, (int, float)) and val > MAX_STATION_VALUE:
                outliers += 1

    print("  Ballot equation failures:  %d" % eq_fail)
    print("  total_votes mismatches:    %d" % tv_fail)
    print("  Negative values:           %d" % neg)
    print("  Outliers (>%d):          %d" % (MAX_STATION_VALUE, outliers))
    print("  Turnout > registered:      %d" % to_fail)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not save')
    args = parser.parse_args()

    src = os.path.join(DATA_DIR, 'ocr_multimodel_chaiyaphum.json')
    with open(src, 'r', encoding='utf-8') as f:
        records = json.load(f)
    print("Loaded %d records from %s\n" % (len(records), os.path.basename(src)))

    killernay = load_killernay()
    print("Killernay zones: %s\n" % sorted(killernay.keys(), key=int))

    stats = {}

    print("=" * 60)
    print("APPLYING FIXES")
    print("=" * 60)

    ect_ref = load_ect_reference()
    print("ECT reference: %s\n" % ('loaded' if ect_ref else 'NOT FOUND'))

    # Order matters: metadata first, then outliers, then candidates, then equations
    fix_metadata_from_filepath(records, stats)  # R0 first - correct constituency before R7
    dedup_records(records, stats)  # R0c - remove exact duplicates (same file+page)
    fix_station_no_from_filepath(records, stats)  # R0b - derive station_no from filename+page
    # dedup_interleaved(records, stats)  # R0d - disabled: removes party-list noise but worsens Zone 2 (253/345 coverage)
    fix_outliers(records, stats)       # R4 - remove garbage before math
    fix_negative_values(records, stats) # R3
    normalize_candidates(records, ect_ref, stats)  # R7 before R1 (need correct cands first)
    fix_candidate_vote_outliers(records, stats)  # R8 - cap per-candidate outlier votes
    fix_remaining_ballots(records, stats)  # R2
    fix_total_votes(records, stats)    # R1 (recalcs total_votes from normalized cands)
    flag_turnout(records, stats)       # R5
    cross_validate_killernay(records, killernay, stats)  # R6

    revalidate(records)

    # Save
    if args.dry_run:
        print("\n[DRY RUN] No files saved.")
    else:
        # Backup original
        backup = src.replace('.json', '_backup.json')
        if not os.path.exists(backup):
            import shutil
            shutil.copy2(src, backup)
            print("\n  Backed up original to %s" % os.path.basename(backup))

        with open(src, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print("  Saved fixed data to %s" % os.path.basename(src))

        # Save stats
        stats_path = os.path.join(DATA_DIR, 'postprocess_stats_chaiyaphum.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print("  Saved stats to %s" % os.path.basename(stats_path))

    print("\n[DONE]")


if __name__ == '__main__':
    main()
