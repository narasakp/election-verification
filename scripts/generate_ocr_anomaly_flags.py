#!/usr/bin/env python3
"""
สร้าง anomaly_flags.json จาก OCR review_data.json (station-level)
ใช้แทน ECT API-based flags เดิมที่มี encoding bug (province names garbled)

Output: review-app/public/data/anomaly_flags.json
Format เดิม: { flags_by_prov_con: { "Province_Constituency": [...flags] }, metadata: {...} }
"""
import json, math, statistics, os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, '..')
REVIEW_DATA = os.path.join(ROOT, 'review-app', 'public', 'data', 'review_data.json')
OUT_PATH = os.path.join(ROOT, 'review-app', 'public', 'data', 'anomaly_flags.json')

def load_data():
    with open(REVIEW_DATA, encoding='utf-8') as f:
        return json.load(f)

def n(v):
    return None if v is None else float(v)

def run_validation(item):
    """Replicate key validation rules from validation.js (Python port)."""
    issues = []
    reg = n(item.get('registered_voters'))
    turn = n(item.get('turnout'))
    vb = n(item.get('valid_ballots'))
    ib = n(item.get('invalid_ballots'))
    nv = n(item.get('no_vote_ballots'))
    br = n(item.get('ballots_received'))
    rem = n(item.get('remaining_ballots'))
    tv = n(item.get('total_votes'))
    cands = item.get('candidates') or []

    # V1: turnout > registered
    if reg and turn and turn > reg:
        issues.append({'rule': 'V1', 'severity': 'error', 'msg': f'มาแสดงตน ({int(turn)}) > ผู้มีสิทธิ ({int(reg)})'})

    # V2: total_votes != valid_ballots
    if tv is not None and vb and tv != vb:
        issues.append({'rule': 'V2', 'severity': 'warning', 'msg': f'รวมคะแนน ({int(tv)}) ≠ บัตรดี ({int(vb)})'})

    # V3: vb+ib+nv != turnout
    if all(v is not None for v in [vb, ib, nv, turn]) and turn > 0:
        s = vb + ib + nv
        if s != turn:
            issues.append({'rule': 'V3', 'severity': 'warning', 'msg': f'บัตรดี+เสีย+ไม่เลือก ({int(s)}) ≠ มาแสดงตน ({int(turn)})'})

    # V4: negative remaining
    if rem is not None and rem < 0:
        issues.append({'rule': 'V4', 'severity': 'error', 'msg': f'บัตรเหลือติดลบ ({int(rem)})'})

    # V6: candidate sum != total_votes
    if cands and tv and tv > 0:
        cand_sum = sum(n(c.get('votes')) or 0 for c in cands)
        if cand_sum != tv:
            issues.append({'rule': 'V6', 'severity': 'warning', 'msg': f'ผลรวมผู้สมัคร ({int(cand_sum)}) ≠ รวมคะแนน ({int(tv)})'})

    # V10: candidate votes > valid_ballots
    if cands and vb and vb > 0:
        bad = [c for c in cands if (n(c.get('votes')) or 0) > vb]
        if bad:
            issues.append({'rule': 'V10', 'severity': 'error', 'msg': f'ผู้สมัครมีคะแนนเกินบัตรดี: {len(bad)} คน'})

    return issues


def analyze_constituency(items):
    """Generate flags for one constituency (province+constituency group)."""
    flags = []

    # Filter to แบ่งเขต only for numeric analysis
    khet_items = [x for x in items if x.get('vote_type') == 'แบ่งเขต']
    all_items = items

    # Count validation errors
    error_count = warning_count = 0
    for item in all_items:
        for issue in run_validation(item):
            if issue['severity'] == 'error':
                error_count += 1
            else:
                warning_count += 1

    total = len(all_items)
    if total == 0:
        return flags

    # Flag: many errors in constituency
    if error_count >= 3:
        flags.append({
            'category': 'data_errors',
            'flag': f'ข้อผิดพลาดหลายจุด ({error_count} รายการ)',
            'value': error_count,
            'detail': f'พบ {error_count} errors และ {warning_count} warnings ใน {total} หน่วย',
            'severity': 'high' if error_count >= 5 else 'medium',
        })
    elif error_count >= 1:
        flags.append({
            'category': 'data_errors',
            'flag': f'พบข้อผิดพลาด ({error_count} รายการ)',
            'value': error_count,
            'detail': f'พบ {error_count} errors ใน {total} หน่วย',
            'severity': 'medium',
        })

    # Turnout analysis (แบ่งเขต)
    turnouts = []
    for item in khet_items:
        reg = n(item.get('registered_voters'))
        turn = n(item.get('turnout'))
        if reg and turn and reg > 0:
            pct = turn / reg * 100
            if 0 < pct <= 100:
                turnouts.append(pct)

    if len(turnouts) >= 5:
        mean_t = statistics.mean(turnouts)
        stdev_t = statistics.stdev(turnouts)

        # High turnout flag (>85%)
        high = [t for t in turnouts if t > 85]
        if len(high) >= 3:
            flags.append({
                'category': 'turnout',
                'flag': f'อัตรามาใช้สิทธิ์สูง (>85%)',
                'value': round(mean_t, 1),
                'detail': f'เฉลี่ย {mean_t:.1f}% ({len(high)}/{len(turnouts)} หน่วย > 85%)',
                'severity': 'medium',
            })

        # Low turnout flag (<50%)
        low = [t for t in turnouts if t < 50]
        if len(low) >= 3:
            flags.append({
                'category': 'turnout',
                'flag': f'อัตรามาใช้สิทธิ์ต่ำ (<50%)',
                'value': round(mean_t, 1),
                'detail': f'เฉลี่ย {mean_t:.1f}% ({len(low)}/{len(turnouts)} หน่วย < 50%)',
                'severity': 'medium',
            })

        # High variance flag
        if stdev_t > 15 and len(turnouts) >= 10:
            flags.append({
                'category': 'turnout',
                'flag': 'ความแปรปรวนสูง (turnout ต่างกันมาก)',
                'value': round(stdev_t, 1),
                'detail': f'SD={stdev_t:.1f}% ใน {len(turnouts)} หน่วย (เฉลี่ย {mean_t:.1f}%)',
                'severity': 'low',
            })

    # Missing data flag
    no_data = sum(1 for x in all_items if not any([
        x.get('registered_voters'), x.get('turnout'), x.get('valid_ballots')
    ]))
    if no_data > 0:
        pct_missing = no_data / total * 100
        if pct_missing >= 20:
            flags.append({
                'category': 'missing_data',
                'flag': f'ข้อมูลขาดหาย ({pct_missing:.0f}%)',
                'value': no_data,
                'detail': f'{no_data}/{total} หน่วยไม่มีข้อมูลสถิติ',
                'severity': 'high' if pct_missing >= 50 else 'medium',
            })

    # No PDF (vision OCR only)
    no_pdf = sum(1 for x in all_items if not x.get('pdf_url'))
    if no_pdf > 0:
        pct_no_pdf = no_pdf / total * 100
        if pct_no_pdf >= 30:
            flags.append({
                'category': 'missing_pdf',
                'flag': f'ไม่มี PDF หลายหน่วย ({pct_no_pdf:.0f}%)',
                'value': no_pdf,
                'detail': f'{no_pdf}/{total} หน่วยไม่มี PDF preview (ใช้ Vision OCR)',
                'severity': 'low',
            })

    return flags


def main():
    print("Loading review_data.json...")
    items = load_data()
    print(f"  {len(items)} items")

    # Group by province_constituency
    groups = defaultdict(list)
    for item in items:
        prov = item.get('province', '')
        con = item.get('constituency', '')
        if prov and con:
            key = f"{prov}_{con}"
            groups[key].append(item)

    print(f"  {len(groups)} province_constituency groups")

    # Analyze each group
    flags_by_prov_con = {}
    for key, group_items in sorted(groups.items()):
        flags = analyze_constituency(group_items)
        if flags:
            flags_by_prov_con[key] = flags

    print(f"  {len(flags_by_prov_con)} groups flagged")

    # Province summary
    from collections import Counter
    prov_counts = Counter('_'.join(k.split('_')[:-1]) for k in flags_by_prov_con)
    for prov, cnt in sorted(prov_counts.items()):
        print(f"    {prov}: {cnt} constituencies flagged")

    # Build output
    provinces = sorted(set(x.get('province') for x in items if x.get('province')))
    out = {
        'metadata': {
            'total_groups': len(groups),
            'flagged_groups': len(flags_by_prov_con),
            'data_source': 'OCR review_data.json (station-level)',
            'provinces': provinces,
            'generated': '2026-04-01',
            'note': 'Rebuilt from OCR data — replaces ECT API flags (encoding bug in original)',
        },
        'flags_by_prov_con': flags_by_prov_con,
    }

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"\nSaved: {OUT_PATH} ({size_kb:.1f} KB)")
    print(f"Flagged: {len(flags_by_prov_con)} / {len(groups)} groups")


if __name__ == '__main__':
    main()
