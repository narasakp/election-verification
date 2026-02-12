#!/usr/bin/env python3
"""
วิเคราะห์ความผิดปกติของข้อมูลเลือกตั้งจาก กกต.
สร้าง anomaly_data.json สำหรับ visualization บนหน้าเว็บ
"""

import json
import math
import os
import statistics
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')


def quantiles_4(data):
    """Return (Q1, Q2, Q3) — works on Python 3.7+"""
    s = sorted(data)
    n = len(s)
    def percentile(p):
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return s[int(k)]
        return s[f] * (c - k) + s[c] * (k - f)
    return percentile(0.25), percentile(0.50), percentile(0.75)


def load_data():
    path = os.path.join(DATA_DIR, 'election_data.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_turnout(units):
    """วิเคราะห์อัตราการมาใช้สิทธิ"""
    turnouts = []
    for u in units:
        if u['turn_out'] > 0 and u['registered_vote'] and u['registered_vote'] > 0:
            pct = u['percent_turn_out']
            turnouts.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'turnout_pct': round(pct, 2),
                'registered': u['registered_vote'],
                'came': u['turn_out'],
            })

    pcts = [t['turnout_pct'] for t in turnouts]
    mean = statistics.mean(pcts)
    stdev = statistics.stdev(pcts)
    median = statistics.median(pcts)
    q1, _, q3 = quantiles_4(pcts)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    for t in turnouts:
        z = (t['turnout_pct'] - mean) / stdev if stdev > 0 else 0
        t['z_score'] = round(z, 2)
        t['is_outlier'] = t['turnout_pct'] < lower_fence or t['turnout_pct'] > upper_fence
        if t['turnout_pct'] < lower_fence:
            t['flag'] = 'ต่ำผิดปกติ'
        elif t['turnout_pct'] > upper_fence:
            t['flag'] = 'สูงผิดปกติ'
        else:
            t['flag'] = 'ปกติ'

    outliers = [t for t in turnouts if t['is_outlier']]
    outliers.sort(key=lambda x: x['z_score'])

    return {
        'summary': {
            'mean': round(mean, 2),
            'median': round(median, 2),
            'stdev': round(stdev, 2),
            'q1': round(q1, 2),
            'q3': round(q3, 2),
            'iqr': round(iqr, 2),
            'lower_fence': round(lower_fence, 2),
            'upper_fence': round(upper_fence, 2),
            'total': len(turnouts),
            'outlier_count': len(outliers),
        },
        'distribution': build_histogram(pcts, bins=[0, 30, 40, 50, 55, 60, 65, 70, 75, 80, 100]),
        'outliers': outliers,
        'all': sorted(turnouts, key=lambda x: x['turnout_pct']),
    }


def analyze_invalid_ballots(units):
    """วิเคราะห์อัตราบัตรเสีย"""
    items = []
    for u in units:
        if u['turn_out'] > 0:
            rate = u['invalid_votes'] / u['turn_out'] * 100
            items.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'invalid_rate': round(rate, 2),
                'invalid_votes': u['invalid_votes'],
                'turn_out': u['turn_out'],
            })

    rates = [i['invalid_rate'] for i in items]
    mean = statistics.mean(rates)
    stdev = statistics.stdev(rates)
    q1, _, q3 = quantiles_4(rates)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr

    for i in items:
        z = (i['invalid_rate'] - mean) / stdev if stdev > 0 else 0
        i['z_score'] = round(z, 2)
        i['is_outlier'] = i['invalid_rate'] > upper_fence
        i['flag'] = 'บัตรเสียสูงผิดปกติ' if i['is_outlier'] else 'ปกติ'

    outliers = [i for i in items if i['is_outlier']]
    outliers.sort(key=lambda x: x['invalid_rate'], reverse=True)

    return {
        'summary': {
            'mean': round(mean, 2),
            'stdev': round(stdev, 2),
            'q1': round(q1, 2),
            'q3': round(q3, 2),
            'upper_fence': round(upper_fence, 2),
            'total': len(items),
            'outlier_count': len(outliers),
        },
        'distribution': build_histogram(rates, bins=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15]),
        'outliers': outliers,
    }


def analyze_blank_votes(units):
    """วิเคราะห์อัตราไม่ประสงค์ลงคะแนน"""
    items = []
    for u in units:
        if u['turn_out'] > 0:
            rate = u['blank_votes'] / u['turn_out'] * 100
            items.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'blank_rate': round(rate, 2),
                'blank_votes': u['blank_votes'],
                'turn_out': u['turn_out'],
            })

    rates = [i['blank_rate'] for i in items]
    mean = statistics.mean(rates)
    stdev = statistics.stdev(rates)
    q1, _, q3 = quantiles_4(rates)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr

    for i in items:
        z = (i['blank_rate'] - mean) / stdev if stdev > 0 else 0
        i['z_score'] = round(z, 2)
        i['is_outlier'] = i['blank_rate'] > upper_fence
        i['flag'] = 'ไม่ประสงค์ฯ สูงผิดปกติ' if i['is_outlier'] else 'ปกติ'

    outliers = [i for i in items if i['is_outlier']]
    outliers.sort(key=lambda x: x['blank_rate'], reverse=True)

    return {
        'summary': {
            'mean': round(mean, 2),
            'stdev': round(stdev, 2),
            'q1': round(q1, 2),
            'q3': round(q3, 2),
            'upper_fence': round(upper_fence, 2),
            'total': len(items),
            'outlier_count': len(outliers),
        },
        'distribution': build_histogram(rates, bins=[0, 2, 3, 4, 5, 6, 7, 8, 10, 15, 25]),
        'outliers': outliers,
    }


def analyze_winner_dominance(units):
    """วิเคราะห์ผู้ชนะได้คะแนนสูงเกินไป (potential vote buying / manipulation)"""
    items = []
    for u in units:
        if u['valid_votes'] > 0 and u['winner_votes'] > 0:
            pct = u['winner_votes'] / u['valid_votes'] * 100
            cands = u.get('candidates', [])
            runner_up = cands[1] if len(cands) >= 2 else None
            margin = 0
            if runner_up:
                margin = (u['winner_votes'] - runner_up.get('ect_votes', 0)) / u['valid_votes'] * 100

            items.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'winner': u['winner'],
                'winner_color': u['winner_color'],
                'winner_pct': round(pct, 2),
                'winner_votes': u['winner_votes'],
                'valid_votes': u['valid_votes'],
                'margin': round(margin, 2),
                'runner_up': runner_up.get('party', '') if runner_up else '',
                'runner_up_votes': runner_up.get('ect_votes', 0) if runner_up else 0,
            })

    pcts = [i['winner_pct'] for i in items]
    mean = statistics.mean(pcts)
    stdev = statistics.stdev(pcts)

    for i in items:
        z = (i['winner_pct'] - mean) / stdev if stdev > 0 else 0
        i['z_score'] = round(z, 2)
        i['is_extreme'] = i['winner_pct'] > 60
        i['flag'] = 'ชนะขาดลอย (>60%)' if i['is_extreme'] else 'ปกติ'

    extreme = [i for i in items if i['is_extreme']]
    extreme.sort(key=lambda x: x['winner_pct'], reverse=True)

    return {
        'summary': {
            'mean': round(mean, 2),
            'stdev': round(stdev, 2),
            'total': len(items),
            'extreme_count': len(extreme),
        },
        'distribution': build_histogram(pcts, bins=[0, 20, 30, 35, 40, 45, 50, 55, 60, 70, 80, 100]),
        'extreme': extreme,
        'all': sorted(items, key=lambda x: x['winner_pct'], reverse=True),
    }


def analyze_close_races(units):
    """วิเคราะห์เขตที่ผลสูสี (margin <3%)"""
    items = []
    for u in units:
        cands = u.get('candidates', [])
        if len(cands) >= 2 and u['valid_votes'] > 0:
            v1 = cands[0].get('ect_votes', 0)
            v2 = cands[1].get('ect_votes', 0)
            margin = (v1 - v2) / u['valid_votes'] * 100
            items.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'margin_pct': round(margin, 2),
                'margin_votes': v1 - v2,
                'winner': cands[0].get('party', ''),
                'winner_votes': v1,
                'runner_up': cands[1].get('party', ''),
                'runner_up_votes': v2,
                'winner_name': cands[0].get('name', ''),
                'runner_up_name': cands[1].get('name', ''),
                'counted_pct': u.get('percent_count', 0),
            })

    items.sort(key=lambda x: x['margin_pct'])
    close = [i for i in items if i['margin_pct'] < 3]

    return {
        'summary': {
            'total_close': len(close),
            'total': len(items),
        },
        'close_races': close,
    }


def analyze_counting_progress(units):
    """วิเคราะห์ความคืบหน้าการนับคะแนน + ที่หยุดรายงาน"""
    items = []
    for u in units:
        total_st = u.get('total_stations', 0) or 0
        counted = u.get('counted_stations', 0) or 0
        pct = u.get('percent_count', 0)
        paused = u.get('pause_report', False)
        remaining = total_st - counted
        items.append({
            'unit_id': u['unit_id'],
            'constituency': u['constituency'],
            'province': u['province'],
            'total_stations': total_st,
            'counted_stations': counted,
            'remaining': remaining,
            'percent_count': round(pct, 2),
            'pause_report': paused,
        })

    paused = [i for i in items if i['pause_report']]
    incomplete = [i for i in items if i['percent_count'] < 100]
    incomplete.sort(key=lambda x: x['percent_count'])

    return {
        'summary': {
            'total': len(items),
            'complete': len([i for i in items if i['percent_count'] >= 100]),
            'incomplete': len(incomplete),
            'paused': len(paused),
        },
        'paused': paused,
        'most_incomplete': incomplete[:20],
    }


def analyze_math_consistency(units):
    """ตรวจสอบความสอดคล้องทางคณิตศาสตร์"""
    errors = []
    for u in units:
        if u['turn_out'] > 0:
            expected = u['valid_votes'] + u['invalid_votes'] + u['blank_votes']
            diff = abs(expected - u['turn_out'])
            if diff > 0:
                errors.append({
                    'unit_id': u['unit_id'],
                    'constituency': u['constituency'],
                    'province': u['province'],
                    'turn_out': u['turn_out'],
                    'sum_votes': expected,
                    'difference': diff,
                })

    # Check candidate votes sum vs valid_votes
    cand_errors = []
    for u in units:
        cands = u.get('candidates', [])
        if cands and u['valid_votes'] > 0:
            cand_sum = sum(c.get('ect_votes', 0) for c in cands)
            diff = abs(cand_sum - u['valid_votes'])
            if diff > 0:
                pct_diff = diff / u['valid_votes'] * 100
                cand_errors.append({
                    'unit_id': u['unit_id'],
                    'constituency': u['constituency'],
                    'province': u['province'],
                    'valid_votes': u['valid_votes'],
                    'candidate_sum': cand_sum,
                    'difference': diff,
                    'pct_diff': round(pct_diff, 2),
                })

    cand_errors.sort(key=lambda x: x['difference'], reverse=True)

    return {
        'summary': {
            'turnout_math_errors': len(errors),
            'candidate_sum_errors': len(cand_errors),
            'total_units': len(units),
        },
        'turnout_errors': errors,
        'candidate_sum_errors': cand_errors[:30],
    }


def analyze_benford(units):
    """Benford's Law analysis on candidate vote counts"""
    first_digits = Counter()
    all_votes = []

    for u in units:
        cands = u.get('candidates', [])
        for c in cands:
            v = c.get('ect_votes', 0)
            if v >= 10:  # Need at least 2 digits
                first = int(str(v)[0])
                first_digits[first] += 1
                all_votes.append(v)

    total = sum(first_digits.values())
    expected_benford = {d: math.log10(1 + 1/d) for d in range(1, 10)}

    results = []
    chi_sq = 0
    for d in range(1, 10):
        observed = first_digits.get(d, 0)
        expected_pct = expected_benford[d]
        observed_pct = observed / total if total > 0 else 0
        expected_count = expected_pct * total
        deviation = observed_pct - expected_pct
        if expected_count > 0:
            chi_sq += (observed - expected_count) ** 2 / expected_count
        results.append({
            'digit': d,
            'observed_count': observed,
            'observed_pct': round(observed_pct * 100, 2),
            'expected_pct': round(expected_pct * 100, 2),
            'deviation': round(deviation * 100, 2),
        })

    # Chi-square critical value for 8 df at 0.05 = 15.507
    return {
        'summary': {
            'total_values': total,
            'chi_square': round(chi_sq, 2),
            'chi_critical_005': 15.507,
            'passes_test': chi_sq < 15.507,
        },
        'digits': results,
    }


def analyze_province_patterns(units):
    """วิเคราะห์รูปแบบรายจังหวัด — พรรคเดียวชนะทุกเขต"""
    prov_data = defaultdict(list)
    for u in units:
        prov_data[u['province']].append(u)

    monopoly = []
    high_variation = []
    for prov, prov_units in prov_data.items():
        winners = [u['winner'] for u in prov_units if u['winner']]
        if not winners:
            continue
        unique = set(winners)
        total = len(winners)
        most_common = Counter(winners).most_common(1)[0]

        turnouts = [u['percent_turn_out'] for u in prov_units if u['percent_turn_out'] > 0]
        inv_rates = [u['invalid_votes'] / u['turn_out'] * 100 for u in prov_units if u['turn_out'] > 0]

        entry = {
            'province': prov,
            'prov_id': prov_units[0]['prov_id'],
            'total_cons': total,
            'unique_winners': len(unique),
            'dominant_party': most_common[0],
            'dominant_count': most_common[1],
            'dominant_pct': round(most_common[1] / total * 100, 1),
            'avg_turnout': round(statistics.mean(turnouts), 1) if turnouts else 0,
            'turnout_stdev': round(statistics.stdev(turnouts), 1) if len(turnouts) > 1 else 0,
            'avg_invalid_rate': round(statistics.mean(inv_rates), 2) if inv_rates else 0,
        }

        if len(unique) == 1 and total >= 3:
            entry['flag'] = 'ผูกขาด — พรรคเดียวชนะทุกเขต'
            monopoly.append(entry)
        elif entry['turnout_stdev'] > 10:
            entry['flag'] = 'Turnout ต่างกันมากในจังหวัด'
            high_variation.append(entry)

    monopoly.sort(key=lambda x: x['total_cons'], reverse=True)

    return {
        'monopoly': monopoly,
        'high_variation': high_variation,
    }


def analyze_wasted_votes(units):
    """วิเคราะห์อัตราคะแนนสูญเปล่า (invalid + blank) / turn_out"""
    items = []
    for u in units:
        if u['turn_out'] > 0:
            wasted = u['invalid_votes'] + u['blank_votes']
            rate = wasted / u['turn_out'] * 100
            items.append({
                'unit_id': u['unit_id'],
                'constituency': u['constituency'],
                'province': u['province'],
                'wasted_rate': round(rate, 2),
                'wasted_votes': wasted,
                'invalid_votes': u['invalid_votes'],
                'blank_votes': u['blank_votes'],
                'turn_out': u['turn_out'],
            })

    rates = [i['wasted_rate'] for i in items]
    mean = statistics.mean(rates)
    stdev = statistics.stdev(rates)
    q1w, _, q3 = quantiles_4(rates)
    iqr = q3 - q1w
    upper_fence = q3 + 1.5 * iqr

    for i in items:
        i['is_outlier'] = i['wasted_rate'] > upper_fence
        i['flag'] = 'คะแนนสูญเปล่าสูง' if i['is_outlier'] else 'ปกติ'

    outliers = [i for i in items if i['is_outlier']]
    outliers.sort(key=lambda x: x['wasted_rate'], reverse=True)

    return {
        'summary': {
            'mean': round(mean, 2),
            'stdev': round(stdev, 2),
            'upper_fence': round(upper_fence, 2),
            'outlier_count': len(outliers),
        },
        'distribution': build_histogram(rates, bins=[0, 3, 5, 7, 9, 11, 13, 15, 20, 35]),
        'outliers': outliers,
    }


def build_histogram(values, bins):
    """สร้าง histogram data"""
    counts = [0] * (len(bins) - 1)
    labels = []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        labels.append(f'{lo}-{hi}%')
        for v in values:
            if v >= lo and (v < hi or (i == len(bins) - 2 and v <= hi)):
                counts[i] += 1
    return {'labels': labels, 'counts': counts}


def main():
    print('=' * 60)
    print(' วิเคราะห์ความผิดปกติข้อมูลเลือกตั้ง กกต.')
    print('=' * 60)

    data = load_data()
    units = data['units']
    print(f'\nข้อมูล: {len(units)} เขตเลือกตั้ง')

    print('\n[1/8] วิเคราะห์อัตราการมาใช้สิทธิ...')
    turnout = analyze_turnout(units)
    print(f'  outliers: {turnout["summary"]["outlier_count"]} เขต')

    print('[2/8] วิเคราะห์บัตรเสีย...')
    invalid = analyze_invalid_ballots(units)
    print(f'  outliers: {invalid["summary"]["outlier_count"]} เขต')

    print('[3/8] วิเคราะห์ไม่ประสงค์ลงคะแนน...')
    blank = analyze_blank_votes(units)
    print(f'  outliers: {blank["summary"]["outlier_count"]} เขต')

    print('[4/8] วิเคราะห์ผู้ชนะได้คะแนนสูง...')
    dominance = analyze_winner_dominance(units)
    print(f'  ชนะ >60%: {dominance["summary"]["extreme_count"]} เขต')

    print('[5/8] วิเคราะห์เขตสูสี...')
    close = analyze_close_races(units)
    print(f'  margin <3%: {close["summary"]["total_close"]} เขต')

    print('[6/8] วิเคราะห์ความคืบหน้าการนับ...')
    counting = analyze_counting_progress(units)
    print(f'  ยังนับไม่ครบ: {counting["summary"]["incomplete"]} เขต, หยุดรายงาน: {counting["summary"]["paused"]}')

    print('[7/8] ตรวจสอบความสอดคล้องทางคณิตศาสตร์...')
    math_check = analyze_math_consistency(units)
    print(f'  turnout errors: {math_check["summary"]["turnout_math_errors"]}')
    print(f'  candidate sum errors: {math_check["summary"]["candidate_sum_errors"]}')

    print('[8/8] Benford\'s Law + Province patterns + Wasted votes...')
    benford = analyze_benford(units)
    print(f'  Chi-sq={benford["summary"]["chi_square"]}, pass={benford["summary"]["passes_test"]}')

    province = analyze_province_patterns(units)
    print(f'  monopoly provinces: {len(province["monopoly"])}')

    wasted = analyze_wasted_votes(units)
    print(f'  wasted vote outliers: {wasted["summary"]["outlier_count"]}')

    # Build anomaly summary
    all_flags = []

    for t in turnout['outliers']:
        all_flags.append({
            'unit_id': t['unit_id'], 'constituency': t['constituency'], 'province': t['province'],
            'category': 'turnout', 'flag': t['flag'], 'value': t['turnout_pct'],
            'detail': f'อัตรามาใช้สิทธิ {t["turnout_pct"]}% (z={t["z_score"]})',
            'severity': 'high' if abs(t['z_score']) > 3 else 'medium',
        })
    for t in invalid['outliers']:
        all_flags.append({
            'unit_id': t['unit_id'], 'constituency': t['constituency'], 'province': t['province'],
            'category': 'invalid', 'flag': t['flag'], 'value': t['invalid_rate'],
            'detail': f'บัตรเสีย {t["invalid_rate"]}% ({t["invalid_votes"]:,} ใบ)',
            'severity': 'high' if t['invalid_rate'] > 8 else 'medium',
        })
    for t in blank['outliers']:
        all_flags.append({
            'unit_id': t['unit_id'], 'constituency': t['constituency'], 'province': t['province'],
            'category': 'blank', 'flag': t['flag'], 'value': t['blank_rate'],
            'detail': f'ไม่ประสงค์ฯ {t["blank_rate"]}% ({t["blank_votes"]:,} ใบ)',
            'severity': 'high' if t['blank_rate'] > 10 else 'medium',
        })
    for t in wasted['outliers']:
        all_flags.append({
            'unit_id': t['unit_id'], 'constituency': t['constituency'], 'province': t['province'],
            'category': 'wasted', 'flag': t['flag'], 'value': t['wasted_rate'],
            'detail': f'คะแนนสูญเปล่า {t["wasted_rate"]}% ({t["wasted_votes"]:,} ใบ)',
            'severity': 'high' if t['wasted_rate'] > 20 else 'medium',
        })
    for t in dominance['extreme']:
        all_flags.append({
            'unit_id': t['unit_id'], 'constituency': t['constituency'], 'province': t['province'],
            'category': 'dominance', 'flag': t['flag'], 'value': t['winner_pct'],
            'detail': f'{t["winner"]} ชนะ {t["winner_pct"]}% (margin {t["margin"]}%)',
            'severity': 'high' if t['winner_pct'] > 70 else 'medium',
        })

    # Deduplicate by unit_id - keep highest severity per unit
    flag_by_unit = defaultdict(list)
    for f in all_flags:
        flag_by_unit[f['unit_id']].append(f)

    flagged_units = set(f['unit_id'] for f in all_flags)

    anomaly_data = {
        'metadata': {
            'total_units': len(units),
            'flagged_units': len(flagged_units),
            'analysis_categories': 8,
        },
        'turnout': turnout,
        'invalid_ballots': invalid,
        'blank_votes': blank,
        'wasted_votes': wasted,
        'winner_dominance': dominance,
        'close_races': close,
        'counting_progress': counting,
        'math_consistency': math_check,
        'benford': benford,
        'province_patterns': province,
        'all_flags': all_flags,
        'flags_by_unit': {uid: flags for uid, flags in flag_by_unit.items()},
    }

    # Save
    out_path = os.path.join(DATA_DIR, 'anomaly_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(anomaly_data, f, ensure_ascii=False, indent=2)
    print(f'\n✅ บันทึก: {out_path}')

    # Summary
    print('\n' + '=' * 60)
    print(' สรุปผลการวิเคราะห์')
    print('=' * 60)
    print(f'  เขตทั้งหมด: {len(units)}')
    print(f'  เขตที่มี flag: {len(flagged_units)} ({len(flagged_units)/len(units)*100:.1f}%)')
    print(f'\n  📊 Turnout ผิดปกติ: {turnout["summary"]["outlier_count"]} เขต')
    print(f'  📊 บัตรเสียสูง: {invalid["summary"]["outlier_count"]} เขต')
    print(f'  📊 ไม่ประสงค์ฯ สูง: {blank["summary"]["outlier_count"]} เขต')
    print(f'  📊 คะแนนสูญเปล่าสูง: {wasted["summary"]["outlier_count"]} เขต')
    print(f'  📊 ชนะขาดลอย (>60%): {dominance["summary"]["extreme_count"]} เขต')
    print(f'  📊 เขตสูสี (<3%): {close["summary"]["total_close"]} เขต')
    print(f'  📊 จังหวัดผูกขาด: {len(province["monopoly"])} จังหวัด')
    print(f'  📊 Benford\'s Law: {"ผ่าน ✅" if benford["summary"]["passes_test"] else "ไม่ผ่าน ❌"} (χ²={benford["summary"]["chi_square"]})')
    print(f'  📊 ผลรวมคะแนนไม่ตรง: {math_check["summary"]["candidate_sum_errors"]} เขต')
    print('=' * 60)


if __name__ == '__main__':
    main()
