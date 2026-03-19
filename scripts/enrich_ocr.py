# -*- coding: utf-8 -*-
"""Enrich multi-model OCR results with official candidate/party data.

Uses ECT Reporter DB + killernay as reference to:
1. Map candidate numbers → official names/parties (แบ่งเขต)
2. Map party numbers → official party names (บัญชีรายชื่อ)
3. Cross-validate vote totals against killernay constituency sums
4. Flag anomalies and mismatches
5. Output enriched JSON ready for analysis/dashboard

Usage:
  python scripts/enrich_ocr.py --province tak
  python scripts/enrich_ocr.py --province tak --output data/enriched_tak.json
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── Data Loaders ───────────────────────────────────────────────────

def load_ect_candidates():
    """Load ECT MP candidates. Returns dict: (prov_prefix, constituency, number) -> info"""
    path = os.path.join(PROJECT_ROOT, 'data', 'ect_mp_candidates.json')
    if not os.path.exists(path):
        print(f"WARNING: {path} not found")
        return {}
    cands = json.load(open(path, 'r', encoding='utf-8'))
    db = {}
    for c in cands:
        # mp_app_id format: "TAK_1_1" = PROV_CONSTITUENCY_NUMBER
        parts = c['mp_app_id'].split('_')
        if len(parts) == 3:
            prov = parts[0]
            const = int(parts[1])
            num = int(parts[2])
            db[(prov, const, num)] = {
                'ect_id': c['mp_app_id'],
                'official_name': c['mp_app_name'],
                'party_id': c.get('mp_app_party_id'),
                'image_url': c.get('image_url'),
            }
    return db


def load_ect_parties():
    """Load ECT parties. Returns dict: party_id -> party_name"""
    path = os.path.join(PROJECT_ROOT, 'data', 'ect_parties.json')
    if not os.path.exists(path):
        return {}
    parties = json.load(open(path, 'r', encoding='utf-8'))
    by_id = {}
    by_no = {}
    for p in parties:
        pid = p.get('id')
        pno = p.get('party_no')
        name = p.get('name', '')
        if pid:
            by_id[str(pid)] = name
        if pno:
            by_no[int(pno)] = name
    return by_id, by_no


def load_killernay_constituency(province_name):
    """Load killernay constituency data for a province.
    Returns dict: (constituency, number) -> {name, party, votes}
    """
    path = os.path.join(PROJECT_ROOT, 'data', 'killernay_constituency_full.csv')
    if not os.path.exists(path):
        path = os.path.join(PROJECT_ROOT, 'data', 'killernay_constituency.csv')
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('จังหวัด', '').strip() != province_name:
                continue
            try:
                const = int(row['เขต'])
                num = int(row['หมายเลข'])
                votes = int(row['คะแนน'])
            except (ValueError, KeyError):
                continue
            result[(const, num)] = {
                'name': row.get('ชื่อผู้สมัคร', '').strip(),
                'party': row.get('พรรค', '').strip(),
                'votes': votes,
            }
    return result


def load_killernay_party_list(province_name):
    """Load killernay party list data for a province.
    Returns dict: (constituency, party_number) -> {party, votes}
    """
    path = os.path.join(PROJECT_ROOT, 'data', 'killernay_party_list.csv')
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('จังหวัด', '').strip() != province_name:
                continue
            try:
                const = int(row['เขต'])
                num = int(row['หมายเลข'])
                votes = int(row['คะแนน'])
            except (ValueError, KeyError):
                continue
            result[(const, num)] = {
                'party': row.get('ชื่อพรรค', row.get('พรรค', '')).strip(),
                'votes': votes,
            }
    return result


def load_ect_stats(prov_code):
    """Load ECT stats for a province."""
    path = os.path.join(PROJECT_ROOT, 'data', 'ect_stats_cons.json')
    if not os.path.exists(path):
        return None
    stats = json.load(open(path, 'r', encoding='utf-8'))
    for p in stats.get('result_province', []):
        if p.get('prov_id') == prov_code:
            return p
    return None


# ─── Province Config ────────────────────────────────────────────────

PROVINCE_CONFIG = {
    'tak': {'name': 'ตาก', 'ect_prefix': 'TAK', 'ect_prov_id': 'TAK'},
    'chaiyaphum': {'name': 'ชัยภูมิ', 'ect_prefix': 'CPM', 'ect_prov_id': 'CPM'},
    'phetchabun': {'name': 'เพชรบูรณ์', 'ect_prefix': 'PNB', 'ect_prov_id': 'PNB'},
}


def build_party_id_map(ect_cands, killernay_const, prov_prefix):
    """Build party_id → party_name mapping by cross-referencing ECT candidates with killernay."""
    party_map = {}
    for (prov, const, num), info in ect_cands.items():
        if prov != prov_prefix:
            continue
        pid = info.get('party_id')
        if pid is None:
            continue
        kn = killernay_const.get((const, num))
        if kn and kn.get('party'):
            party_map[pid] = kn['party']
    return party_map


# ─── Enrichment ─────────────────────────────────────────────────────

def enrich_results(ocr_results, ect_cands, killernay_const, killernay_party,
                   party_id_map, ect_party_by_no, prov_prefix, province_name):
    """Enrich OCR results with official data."""
    enriched = []
    stats = {
        'total_items': len(ocr_results),
        'content_pages': 0,
        'back_pages': 0,
        'candidates_enriched': 0,
        'candidates_total': 0,
        'parties_enriched': 0,
        'parties_total': 0,
        'anomalies': [],
    }

    for item in ocr_results:
        enriched_item = dict(item)  # shallow copy

        if item.get('is_back_page'):
            stats['back_pages'] += 1
            enriched.append(enriched_item)
            continue

        stats['content_pages'] += 1
        const = item.get('constituency')
        vote_type = item.get('vote_type', '')
        is_party_list = 'บัญชี' in str(vote_type)

        enriched_candidates = []
        for cand in item.get('candidates', []):
            ec = dict(cand)  # shallow copy
            num = cand.get('number')

            if num is not None and const is not None:
                if is_party_list:
                    # บัญชีรายชื่อ: number = party number
                    stats['parties_total'] += 1
                    kn_party = killernay_party.get((const, num))
                    ect_party_name = ect_party_by_no.get(num)
                    
                    if kn_party:
                        ec['official_party'] = kn_party['party']
                        ec['killernay_votes'] = kn_party['votes']
                        stats['parties_enriched'] += 1
                    elif ect_party_name:
                        ec['official_party'] = ect_party_name
                        stats['parties_enriched'] += 1
                else:
                    # แบ่งเขต: number = candidate number
                    stats['candidates_total'] += 1
                    ect = ect_cands.get((prov_prefix, const, num))
                    kn = killernay_const.get((const, num))

                    if ect:
                        ec['official_name'] = ect['official_name']
                        ec['ect_id'] = ect['ect_id']
                        pid = ect.get('party_id')
                        ec['official_party'] = party_id_map.get(pid, f'party_id={pid}')
                        stats['candidates_enriched'] += 1

                    if kn:
                        ec['killernay_name'] = kn['name']
                        ec['killernay_party'] = kn['party']
                        ec['killernay_votes'] = kn['votes']

            enriched_candidates.append(ec)

        enriched_item['candidates'] = enriched_candidates

        # ─── Anomaly checks ───
        # 1. Ballot reconciliation
        r = item.get('ballots_received')
        v = item.get('valid_ballots')
        inv = item.get('invalid_ballots')
        nv = item.get('no_vote_ballots')
        rem = item.get('remaining_ballots')
        if all(x is not None for x in [r, v, inv, nv, rem]):
            expected = v + inv + nv + rem
            if r != expected:
                enriched_item['_anomaly_ballot_recon'] = {
                    'received': r, 'expected': expected, 'diff': r - expected
                }
                stats['anomalies'].append(f"ballot_recon: p{item.get('page')} diff={r-expected:+d}")

        # 2. Turnout check
        voters = item.get('registered_voters')
        turnout = item.get('turnout')
        if voters and turnout and turnout > voters:
            enriched_item['_anomaly_turnout'] = {
                'turnout': turnout, 'voters': voters
            }
            stats['anomalies'].append(f"turnout: p{item.get('page')} {turnout}>{voters}")

        # 3. Vote sum check (แบ่งเขต only)
        if not is_party_list and v is not None:
            cand_votes = [c.get('votes') for c in enriched_candidates if c.get('votes') is not None]
            if cand_votes:
                total = sum(cand_votes)
                if total > v:
                    enriched_item['_anomaly_vote_sum'] = {
                        'sum_candidates': total, 'valid_ballots': v, 'diff': total - v
                    }
                    stats['anomalies'].append(f"vote_sum: p{item.get('page')} sum={total}>valid={v}")

        enriched.append(enriched_item)

    return enriched, stats


# ─── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Enrich OCR results with official data')
    parser.add_argument('--province', required=True, help='Province slug (tak, chaiyaphum, phetchabun)')
    parser.add_argument('--output', help='Output file path (default: data/enriched_{province}.json)')
    args = parser.parse_args()

    slug = args.province.lower()
    config = PROVINCE_CONFIG.get(slug)
    if not config:
        print(f"Unknown province: {slug}. Available: {list(PROVINCE_CONFIG.keys())}")
        sys.exit(1)

    province_name = config['name']
    prov_prefix = config['ect_prefix']
    prov_id = config['ect_prov_id']

    print(f"{'='*70}")
    print(f"ENRICHING OCR RESULTS: {province_name} ({slug})")
    print(f"{'='*70}")

    # Load OCR results
    ocr_path = os.path.join(PROJECT_ROOT, 'data', f'ocr_multimodel_{slug}.json')
    if not os.path.exists(ocr_path):
        print(f"ERROR: {ocr_path} not found")
        sys.exit(1)
    ocr_results = json.load(open(ocr_path, 'r', encoding='utf-8'))
    print(f"OCR results: {len(ocr_results)} items")

    # Load reference data
    ect_cands = load_ect_candidates()
    _ect_party_by_id, ect_party_by_no = load_ect_parties()
    killernay_const = load_killernay_constituency(province_name)
    killernay_party = load_killernay_party_list(province_name)
    ect_stats = load_ect_stats(prov_id)

    print(f"ECT candidates: {len(ect_cands)} total")
    print(f"ECT parties by number: {len(ect_party_by_no)}")
    print(f"killernay constituency: {len(killernay_const)} entries for {province_name}")
    print(f"killernay party list: {len(killernay_party)} entries for {province_name}")
    print(f"ECT stats: {'found' if ect_stats else 'not found'} for {prov_id}")

    # Build party_id → name mapping
    party_id_map = build_party_id_map(ect_cands, killernay_const, prov_prefix)
    print(f"Party ID mapping: {len(party_id_map)} resolved")

    # Enrich
    enriched, stats = enrich_results(
        ocr_results, ect_cands, killernay_const, killernay_party,
        party_id_map, ect_party_by_no, prov_prefix, province_name
    )

    # Output
    output_path = args.output or os.path.join(PROJECT_ROOT, 'data', f'enriched_{slug}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'='*70}")
    print(f"ENRICHMENT SUMMARY")
    print(f"{'='*70}")
    print(f"  Total items: {stats['total_items']}")
    print(f"  Content pages: {stats['content_pages']}")
    print(f"  Back pages: {stats['back_pages']}")
    print(f"  Candidates enriched: {stats['candidates_enriched']}/{stats['candidates_total']}"
          f" ({stats['candidates_enriched']/max(stats['candidates_total'],1)*100:.0f}%)")
    print(f"  Parties enriched: {stats['parties_enriched']}/{stats['parties_total']}"
          f" ({stats['parties_enriched']/max(stats['parties_total'],1)*100:.0f}%)")
    print(f"  Anomalies: {len(stats['anomalies'])}")
    for a in stats['anomalies']:
        print(f"    - {a}")
    print(f"\n  Output: {output_path}")


if __name__ == '__main__':
    main()
