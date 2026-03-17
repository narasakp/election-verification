"""Extract dashboard data into a static JSON for the React Review App."""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

# Load dashboard cache
cache = json.load(open('data/dashboard_cache.json', 'r', encoding='utf-8'))
provs_cache = cache.get('provinces', {})

# Load backup progress for more detail
prog = json.load(open('data/backup_progress.json', 'r', encoding='utf-8'))
prog_by_prov = {}
for r in prog.get('results', []):
    prov = r.get('province')
    if prov:
        prog_by_prov[prov] = r

# RANKING_ORDER from dashboard.py
RANKING_ORDER = [
    "บุรีรัมย์", "ตาก", "ชัยภูมิ", "เพชรบูรณ์", "เพชรบุรี",
    "นครราชสีมา", "อุบลราชธานี", "ศรีสะเกษ", "สุรินทร์", "ร้อยเอ็ด",
    "ขอนแก่น", "อุดรธานี", "เชียงใหม่", "นครศรีธรรมราช", "สงขลา",
    "กรุงเทพมหานคร", "เชียงราย", "สกลนคร", "กาฬสินธุ์", "มหาสารคาม",
    "นครพนม", "อำนาจเจริญ", "ยโสธร", "มุกดาหาร", "หนองคาย",
    "หนองบัวลำภู", "บึงกาฬ", "เลย", "ชัยนาท", "สระบุรี",
    "ลพบุรี", "อ่างทอง", "นครนายก", "ปราจีนบุรี", "สระแก้ว",
    "จันทบุรี", "ระยอง", "ชลบุรี", "ฉะเชิงเทรา", "ตราด",
    "สมุทรปราการ", "นนทบุรี", "พระนครศรีอยุธยา", "สุพรรณบุรี",
    "กาญจนบุรี", "ราชบุรี", "นครสวรรค์", "พิจิตร", "พิษณุโลก",
    "อุตรดิตถ์", "สุโขทัย", "กำแพงเพชร", "แพร่", "น่าน",
    "ลำปาง", "ลำพูน", "แม่ฮ่องสอน", "ประจวบคีรีขันธ์",
    "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "ปทุมธานี", "กระบี่",
    "พังงา", "ภูเก็ต", "สิงห์บุรี", "ชุมพร", "ตรัง",
    "พัทลุง", "ยะลา", "สุราษฎร์ธานี",
    # remaining from cache
    "ปัตตานี", "นราธิวาส", "พะเยา", "ระนอง", "สตูล",
]

# Merge data
provinces = []
for prov in RANKING_ORDER:
    c = provs_cache.get(prov, {})
    p = prog_by_prov.get(prov, {})
    
    actual = c.get('actual', 0) or p.get('uploaded', 0) + p.get('skipped', 0)
    expected = c.get('expected', 0) or p.get('pdf_count', 0)
    pct = round(actual / expected * 100, 1) if expected > 0 else 0
    complete = c.get('complete', False)
    
    provinces.append({
        'name': prov,
        'actual': actual,
        'expected': expected,
        'pct': pct,
        'complete': complete,
        'uploaded': p.get('uploaded', 0),
        'skipped': p.get('skipped', 0),
        'failed': p.get('failed', 0),
        'status': c.get('status', p.get('status', '')),
    })

# Also check for any provinces in cache not in RANKING_ORDER
for prov in provs_cache:
    if prov not in RANKING_ORDER:
        c = provs_cache[prov]
        provinces.append({
            'name': prov,
            'actual': c.get('actual', 0),
            'expected': c.get('expected', 0),
            'pct': c.get('pct', 0),
            'complete': c.get('complete', False),
            'uploaded': 0, 'skipped': 0, 'failed': 0,
            'status': c.get('status', ''),
        })

# Summary
has_data = sum(1 for p in provinces if p['actual'] > 0)
complete_count = sum(1 for p in provinces if p['complete'])
total_actual = sum(p['actual'] for p in provinces)
total_expected = sum(p['expected'] for p in provinces)
total_pct = round(total_actual / total_expected * 100, 1) if total_expected > 0 else 0

out = {
    'summary': {
        'has_data': has_data,
        'complete': complete_count,
        'total': len(provinces),
        'total_actual': total_actual,
        'total_expected': total_expected,
        'pct': total_pct,
        'last_scan_ts': cache.get('last_scan_ts'),
    },
    'provinces': provinces,
}

outpath = 'review-app/public/data/backup_status.json'
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)

print(f"Output: {os.path.getsize(outpath) / 1024:.1f} KB")
print(f"Provinces: {len(provinces)}")
print(f"Has data: {has_data}, Complete: {complete_count}")
print(f"Total PDFs: {total_actual:,} / {total_expected:,} ({total_pct}%)")
print()
# Show top 5
for p in provinces[:5]:
    print(f"  {p['name']:15s} {p['actual']:>7,} / {p['expected']:>7,} ({p['pct']}%) {'✅' if p['complete'] else '❌'}")
