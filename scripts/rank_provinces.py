#!/usr/bin/env python3
"""Rank 77 provinces by anomaly score from anomaly_data.json"""
import json, os, glob, sys, io
from collections import defaultdict

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Also write to file
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "province_ranking.txt")
_out_lines = []
_orig_print = print
def print(*args, **kwargs):
    import io as _io
    buf = _io.StringIO()
    _orig_print(*args, file=buf, **kwargs)
    line = buf.getvalue()
    _out_lines.append(line)
    _orig_print(*args, **kwargs)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "..", "downloads", "ss518")

# slug -> Thai name mapping (all 77 provinces)
SLUG_TO_THAI = {
    "amnatcharoen": "อำนาจเจริญ", "angthong": "อ่างทอง",
    "phranakhonsiayutthaya": "พระนครศรีอยุธยา", "bangkok": "กรุงเทพมหานคร",
    "buengkan": "บึงกาฬ", "buriram": "บุรีรัมย์",
    "chonburi": "ชลบุรี", "chachoengsao": "ฉะเชิงเทรา",
    "chiangmai": "เชียงใหม่", "chainat": "ชัยนาท",
    "chaiyaphum": "ชัยภูมิ", "chumphon": "ชุมพร",
    "chiangrai": "เชียงราย", "chanthaburi": "จันทบุรี",
    "krabi": "กระบี่", "khonkaen": "ขอนแก่น",
    "kamphaengphet": "กำแพงเพชร", "kanchanaburi": "กาญจนบุรี",
    "kalasin": "กาฬสินธุ์", "loei": "เลย",
    "lampang": "ลำปาง", "lamphun": "ลำพูน",
    "lopburi": "ลพบุรี", "mukdahan": "มุกดาหาร",
    "mahasarakham": "มหาสารคาม", "maehongson": "แม่ฮ่องสอน",
    "nan": "น่าน", "nongbualamphu": "หนองบัวลำภู",
    "nonthaburi": "นนทบุรี", "nongkhai": "หนองคาย",
    "nakhonratchasima": "นครราชสีมา", "nakhonphanom": "นครพนม",
    "nakhonpathom": "นครปฐม", "nakhonsawan": "นครสวรรค์",
    "nakhonsithammarat": "นครศรีธรรมราช", "narathiwat": "นราธิวาส",
    "nakhonnayok": "นครนายก", "phetchaburi": "เพชรบุรี",
    "prachuapkhirikhan": "ประจวบคีรีขันธ์", "pathumthani": "ปทุมธานี",
    "phuket": "ภูเก็ต", "phatthalung": "พัทลุง",
    "phitsanulok": "พิษณุโลก", "phangnga": "พังงา",
    "phetchabun": "เพชรบูรณ์", "phrae": "แพร่",
    "prachinburi": "ปราจีนบุรี", "pattani": "ปัตตานี",
    "phichit": "พิจิตร", "phayao": "พะเยา",
    "ratchaburi": "ราชบุรี", "roiet": "ร้อยเอ็ด",
    "ranong": "ระนอง", "rayong": "ระยอง",
    "saraburi": "สระบุรี", "sakaeo": "สระแก้ว",
    "samutsongkhram": "สมุทรสงคราม", "samutsakhon": "สมุทรสาคร",
    "songkhla": "สงขลา", "singburi": "สิงห์บุรี",
    "sakonnakhon": "สกลนคร", "suphanburi": "สุพรรณบุรี",
    "samutprakan": "สมุทรปราการ", "surin": "สุรินทร์",
    "sisaket": "ศรีสะเกษ", "sukhothai": "สุโขทัย",
    "satun": "สตูล", "tak": "ตาก",
    "trang": "ตรัง", "trat": "ตราด",
    "ubonratchathani": "อุบลราชธานี", "udonthani": "อุดรธานี",
    "uthaithani": "อุทัยธานี", "uttaradit": "อุตรดิตถ์",
    "yala": "ยะลา", "yasothon": "ยโสธร",
    "surattthani": "สุราษฎร์ธานี", "suratthani": "สุราษฎร์ธานี",
}
THAI_TO_SLUG = {v: k for k, v in SLUG_TO_THAI.items()}

# prov_id -> Thai name mapping
PROV_ID_TO_THAI = {
    "ACR": "อำนาจเจริญ", "ATG": "อ่างทอง", "AYA": "พระนครศรีอยุธยา",
    "BKK": "กรุงเทพมหานคร", "BKN": "บึงกาฬ", "BRM": "บุรีรัมย์",
    "CBI": "ชลบุรี", "CCO": "ฉะเชิงเทรา", "CMI": "เชียงใหม่",
    "CNT": "ชัยนาท", "CPM": "ชัยภูมิ", "CPN": "ชุมพร",
    "CRI": "เชียงราย", "CTI": "จันทบุรี", "KBI": "กระบี่",
    "KKN": "ขอนแก่น", "KPT": "กำแพงเพชร", "KRI": "กาญจนบุรี",
    "KSN": "กาฬสินธุ์", "LEI": "เลย", "LPG": "ลำปาง",
    "LPN": "ลำพูน", "LRI": "ลพบุรี", "MDH": "มุกดาหาร",
    "MKM": "มหาสารคาม", "MSN": "แม่ฮ่องสอน", "NAN": "น่าน",
    "NBI": "หนองบัวลำภู", "NBP": "นนทบุรี", "NKI": "หนองคาย",
    "NMA": "นครราชสีมา", "NPM": "นครพนม", "NPT": "นครปฐม",
    "NSN": "นครสวรรค์", "NST": "นครศรีธรรมราช", "NWT": "นราธิวาส",
    "NYK": "นครนายก", "PBI": "เพชรบุรี", "PCT": "ประจวบคีรีขันธ์",
    "PKN": "ปทุมธานี", "PKT": "ภูเก็ต", "PLG": "พัทลุง",
    "PLK": "พิษณุโลก", "PNA": "พังงา", "PNB": "เพชรบูรณ์",
    "PRE": "แพร่", "PRI": "ปราจีนบุรี", "PTE": "ปัตตานี",
    "PTN": "พิจิตร", "PYO": "พะเยา", "RBR": "ราชบุรี",
    "RET": "ร้อยเอ็ด", "RNG": "ระนอง", "RYG": "ระยอง",
    "SBR": "สระบุรี", "SKA": "สระแก้ว", "SKM": "สมุทรสงคราม",
    "SKN": "สมุทรสาคร", "SKW": "สงขลา", "SNI": "สิงห์บุรี",
    "SNK": "สกลนคร", "SPB": "สุพรรณบุรี", "SPK": "สมุทรปราการ",
    "SRI": "สระบุรี", "SRN": "สุรินทร์", "SSK": "ศรีสะเกษ",
    "STI": "สุโขทัย", "STN": "สตูล", "TAK": "ตาก",
    "TRG": "ตรัง", "TRT": "ตราด", "UBN": "อุบลราชธานี",
    "UDN": "อุดรธานี", "UTI": "อุทัยธานี", "UTT": "อุตรดิตถ์",
    "YLA": "ยะลา", "YST": "ยโสธร",
}

# Load anomaly data
with open(os.path.join(DATA_DIR, "anomaly_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

# Load ect_raw_data for constituency counts
with open(os.path.join(DATA_DIR, "ect_raw_data.json"), "r", encoding="utf-8") as f:
    ect = json.load(f)

# Load ss518_index for download status
idx_path = os.path.join(DATA_DIR, "ss518_index.json")
idx = {}
if os.path.exists(idx_path):
    with open(idx_path, "r", encoding="utf-8") as f:
        idx = json.load(f)

# Build slug -> pdf_count from index
idx_slug_pdfs = {}
for prov in idx.get("provinces", []):
    idx_slug_pdfs[prov["slug"]] = len(prov.get("pdfs", []))

# Build province list from ect data (using prov_id)
prov_id_constituencies = defaultdict(int)
for item in ect:
    pid = item.get("prov_id", "")
    cno = item.get("cons_no", 0)
    if pid and cno > 0:  # skip cons_no=0 (party list)
        prov_id_constituencies[pid] += 1

# Aggregate flags by province (Thai name from anomaly data)
prov_flags = defaultdict(lambda: {
    "high": 0, "medium": 0, "low": 0, "total": 0,
    "categories": set(), "details": []
})

for flag in data["all_flags"]:
    prov = flag["province"]
    sev = flag.get("severity", "low")
    prov_flags[prov][sev] += 1
    prov_flags[prov]["total"] += 1
    prov_flags[prov]["categories"].add(flag["category"])
    prov_flags[prov]["details"].append(
        f"  {flag['constituency']}: {flag['detail']}"
    )

# Check download status per province
def get_download_status(thai_name):
    slug = THAI_TO_SLUG.get(thai_name, "")
    if not slug:
        return "no_slug", 0, slug
    prov_dir = os.path.join(DOWNLOAD_DIR, slug)
    if not os.path.exists(prov_dir):
        return "missing", 0, slug
    pdfs = glob.glob(os.path.join(prov_dir, "**", "*.pdf"), recursive=True)
    return ("ok" if pdfs else "empty"), len(pdfs), slug

# Build full 77-province ranking
scores = []
for pid, n_const in prov_id_constituencies.items():
    thai = PROV_ID_TO_THAI.get(pid, pid)
    f = prov_flags.get(thai, {
        "high": 0, "medium": 0, "low": 0, "total": 0,
        "categories": set(), "details": []
    })
    score = f["high"] * 3 + f["medium"] * 2 + f["low"] * 1
    dl_status, pdf_count, slug = get_download_status(thai)

    scores.append({
        "province": thai,
        "prov_id": pid,
        "slug": slug if slug else "?",
        "constituencies": n_const,
        "flags": f["total"],
        "high": f["high"],
        "medium": f["medium"],
        "low": f["low"],
        "score": score,
        "categories": len(f["categories"]),
        "cat_list": ",".join(sorted(f["categories"])) if f["categories"] else "-",
        "dl_status": dl_status,
        "pdf_count": pdf_count,
        "details": f["details"],
    })

scores.sort(key=lambda x: (-x["score"], -x["high"], -x["flags"]))

# Print ranking
hdr = f"{'#':>3} {'จังหวัด':<22} {'slug':<22} {'เขต':>3} {'flags':>5} {'H':>2} {'M':>2} {'L':>2} {'score':>5} {'PDFs':>5} {'DL':<4} ประเภทความผิดปกติ"
print(hdr)
print("=" * 140)
for i, s in enumerate(scores):
    icon = {"ok": "✅", "missing": "❌", "empty": "📂", "no_slug": "❓"}.get(s["dl_status"], "?")
    print(
        f"{i+1:>3} {s['province']:<22} {s['slug']:<22} {s['constituencies']:>3} "
        f"{s['flags']:>5} {s['high']:>2} {s['medium']:>2} {s['low']:>2} "
        f"{s['score']:>5} {s['pdf_count']:>5} {icon:<4} {s['cat_list']}"
    )

# Print details for flagged provinces
print("\n")
print("=" * 80)
print(" รายละเอียด flags แต่ละจังหวัด (เฉพาะที่มี flag)")
print("=" * 80)
for s in scores:
    if s["flags"] > 0:
        rank = scores.index(s) + 1
        print(f"\n--- #{rank} {s['province']} ({s['slug']}) score={s['score']} flags={s['flags']} (H={s['high']} M={s['medium']} L={s['low']}) PDFs={s['pdf_count']} ---")
        for d in s["details"]:
            print(d)

# Summary stats
print("\n\n" + "=" * 60)
print(" สรุป")
print("=" * 60)
total_prov = len(scores)
total_flagged = sum(1 for s in scores if s["flags"] > 0)
total_ok = sum(1 for s in scores if s["dl_status"] == "ok")
total_missing = sum(1 for s in scores if s["dl_status"] in ("missing", "no_slug"))
total_pdfs = sum(s["pdf_count"] for s in scores)
print(f"  จังหวัดทั้งหมด: {total_prov}")
print(f"  จังหวัดที่มี flags: {total_flagged}")
print(f"  จังหวัดที่มี PDF แล้ว: {total_ok} ({total_pdfs} ไฟล์)")
print(f"  จังหวัดที่ยังไม่มี PDF: {total_missing}")
print(f"\n  แนะนำดาวน์โหลดตามลำดับ: จังหวัดที่ score สูง + ยังไม่มี PDF ก่อน")

# Write to file
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("".join(_out_lines))
_orig_print(f"\nOutput written to {OUT_FILE}")
