"""Extract lightweight anomaly flags JSON for the Review App.

IMPORTANT: ECT data was captured mid-count (national 94.3%, some as low as 21%).
Flags are adjusted to account for incomplete counting:
- Turnout flags from <90% counted constituencies are excluded (unreliable)
- Remaining flags include percent_count for transparency
"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('data/anomaly_data.json', 'r', encoding='utf-8'))
ed = json.load(open('data/election_data.json', 'r', encoding='utf-8'))

# Build unit_id -> percent_count lookup from election_data
pct_count_map = {}
for u in ed['units']:
    pct_count_map[u['unit_id']] = {
        'percent_count': u.get('percent_count', 0),
        'counted_stations': u.get('counted_stations', 0),
        'total_stations': u.get('total_stations', 0),
    }

# Build province+constituency keyed flags for easy lookup
flags_by_prov_con = {}
excluded_turnout = 0

for unit_id, flags in d['flags_by_unit'].items():
    if not flags:
        continue
    f0 = flags[0]
    prov = f0['province']
    con_str = f0['constituency']
    con_num = con_str.split(' เขต ')[-1] if ' เขต ' in con_str else con_str
    key = f"{prov}_{con_num}"

    counting = pct_count_map.get(unit_id, {})
    pct = counting.get('percent_count', 100)

    filtered_flags = []
    for f in flags:
        # EXCLUDE turnout flags from constituencies with <90% counted
        # (turnout % is meaningless when denominator is full constituency but numerator is partial)
        if f['category'] == 'turnout' and pct < 90:
            excluded_turnout += 1
            continue

        entry = {
            'category': f['category'],
            'flag': f['flag'],
            'value': f['value'],
            'detail': f['detail'],
            'severity': f['severity'],
            'percent_count': round(pct, 1),
        }
        # Add counting disclaimer for any flag from incomplete data
        if pct < 100:
            entry['incomplete'] = True
            cs = counting.get('counted_stations', '?')
            ts = counting.get('total_stations', '?')
            entry['detail'] += f' [นับแล้ว {cs}/{ts} หน่วย ({pct:.0f}%)]'
        filtered_flags.append(entry)

    if filtered_flags:
        flags_by_prov_con[key] = filtered_flags

# Summary
meta = d['metadata']
benford = d['benford']['summary']

out = {
    'metadata': {
        'total_units': meta['total_units'],
        'flagged_units': len(flags_by_prov_con),
        'data_source': 'ECT API (stats_cons.json)',
        'data_snapshot': 'Feb 10, 2026 — นับ 94.3% ระดับประเทศ',
        'disclaimer': 'ข้อมูลจาก กกต. ณ ขณะนับคะแนน ยังไม่ใช่ผลสุดท้าย บางเขตนับไม่ถึง 100%',
    },
    'benford': {
        'passes_test': benford['passes_test'],
        'chi_square': benford['chi_square'],
    },
    'flags_by_prov_con': flags_by_prov_con,
}

outpath = 'review-app/public/data/anomaly_flags.json'
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)

print(f"Output: {os.path.getsize(outpath) / 1024:.1f} KB")
print(f"Flagged constituencies: {len(flags_by_prov_con)}")
print(f"Excluded turnout flags (<90% counted): {excluded_turnout}")
print()
for key, flags in sorted(flags_by_prov_con.items())[:5]:
    print(f"  {key}: {[f['category'] for f in flags]}")
