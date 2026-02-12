#!/usr/bin/env python3
"""
วิเคราะห์ข้อมูล กกต. จาก ECT API จริง และสร้าง JSON สำหรับ Dashboard
ดึงข้อมูลจาก:
  - https://stats-ectreport69.ect.go.th/data/records/stats_cons.json (ผลคะแนน)
  - https://static-ectreport69.ect.go.th/data/data/refs/info_province.json (ข้อมูลจังหวัด)
  - https://static-ectreport69.ect.go.th/data/data/refs/info_party_overview.json (ข้อมูลพรรค)
"""

import json
import requests
from datetime import datetime
import os

# --- API Endpoints ---
STATS_URL = "https://stats-ectreport69.ect.go.th/data/records/stats_cons.json"
PROVINCE_URL = "https://static-ectreport69.ect.go.th/data/data/refs/info_province.json"
PARTY_URL = "https://static-ectreport69.ect.go.th/data/data/refs/info_party_overview.json"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')


def fetch_json(url, label):
    """ดึง JSON จาก URL"""
    print(f"  ดึงข้อมูล {label}...")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"  ✅ {label} สำเร็จ")
        return data
    except Exception as e:
        print(f"  ❌ {label} ล้มเหลว: {e}")
        return None


def build_party_map(party_data):
    """สร้าง dict party_id -> {name, color, abbr}"""
    m = {}
    for p in party_data:
        pid = int(p["id"])
        m[pid] = {
            "name": p["name"],
            "color": p.get("color", "#999"),
            "abbr": p.get("abbr") or p["name"],
        }
    return m


def build_province_map(province_data):
    """สร้าง dict prov_id -> province name (Thai)"""
    m = {}
    # province_data is a dict with key "province" containing the list
    prov_list = province_data if isinstance(province_data, list) else province_data.get("province", [])
    for p in prov_list:
        m[p["prov_id"]] = p["province"]
    return m


def create_dashboard_data(stats, province_map, party_map):
    """สร้างข้อมูล Dashboard จาก stats_cons.json"""

    last_update = stats.get("last_update", datetime.now().isoformat())
    national_turnout = stats.get("turn_out", 0)
    national_valid = stats.get("valid_votes", 0)
    national_invalid = stats.get("invalid_votes", 0)
    national_blank = stats.get("blank_votes", 0)
    percent_count = stats.get("percent_count", 0)

    provinces_result = stats.get("result_province", [])

    all_units = []
    province_summary = {}
    total_constituencies = 0

    for prov in provinces_result:
        prov_id = prov["prov_id"]
        prov_name = province_map.get(prov_id, prov_id)
        prov_turnout = prov.get("turn_out", 0)
        prov_valid = prov.get("valid_votes", 0)
        prov_counted = prov.get("counted_vote_stations", 0)
        prov_total_stations = prov.get("total_vote_stations", 0)
        prov_percent = prov.get("percent_count", 0)

        # Top parties at province level
        prov_parties = prov.get("result_party", [])
        top_prov_parties = sorted(prov_parties, key=lambda x: x.get("party_cons_votes", 0), reverse=True)[:5]
        prov_top = []
        for pp in top_prov_parties:
            pid = pp["party_id"]
            pinfo = party_map.get(pid, {"name": f"party_{pid}", "color": "#999"})
            prov_top.append({
                "name": pinfo["name"],
                "color": pinfo["color"],
                "cons_votes": pp.get("party_cons_votes", 0),
                "party_list_votes": pp.get("party_list_vote", 0),
            })

        constituencies = prov.get("constituencies", [])
        prov_unit_count = 0

        for cons in constituencies:
            cons_id = cons["cons_id"]
            # Skip BKK_0 or similar aggregate entries with no real votes
            if cons.get("turn_out", 0) == 0 and cons.get("valid_votes", 0) == 0:
                continue

            total_constituencies += 1
            prov_unit_count += 1

            # Candidate results (sorted by rank)
            candidates = cons.get("candidates", [])
            candidates_sorted = sorted(candidates, key=lambda x: x.get("mp_app_rank", 999))

            parties_list = []
            for cand in candidates_sorted:
                pid = cand["party_id"]
                pinfo = party_map.get(pid, {"name": f"party_{pid}", "color": "#999"})
                parties_list.append({
                    "name": pinfo["name"],
                    "color": pinfo["color"],
                    "candidate_id": cand.get("mp_app_id", ""),
                    "ect": cand.get("mp_app_vote", 0),
                    "vote62": 0,
                    "percent": cand.get("mp_app_vote_percent", 0),
                    "rank": cand.get("mp_app_rank", 0),
                })

            ect_total = cons.get("valid_votes", 0)

            unit_data = {
                "unit_id": cons_id,
                "constituency": f"{prov_name} เขต {cons_id.split('_')[1]}",
                "province": prov_name,
                "prov_id": prov_id,
                "ect_total": ect_total,
                "vote62_total": 0,
                "difference": 0,
                "level": "pending",
                "turn_out": cons.get("turn_out", 0),
                "percent_turn_out": cons.get("percent_turn_out", 0),
                "valid_votes": ect_total,
                "invalid_votes": cons.get("invalid_votes", 0),
                "blank_votes": cons.get("blank_votes", 0),
                "counted_stations": cons.get("counted_vote_stations", 0),
                "percent_count": cons.get("percent_count", 0),
                "pause_report": cons.get("pause_report", False),
                "winner": parties_list[0]["name"] if parties_list else "",
                "winner_votes": parties_list[0]["ect"] if parties_list else 0,
                "winner_color": parties_list[0]["color"] if parties_list else "#999",
                "has_discrepancy": False,
                "note": "รอข้อมูล Vote62",
                "parties": parties_list,
            }
            all_units.append(unit_data)

        province_summary[prov_id] = {
            "name": prov_name,
            "prov_id": prov_id,
            "units": prov_unit_count,
            "compared": 0,
            "critical": 0,
            "turn_out": prov_turnout,
            "valid_votes": prov_valid,
            "counted_stations": prov_counted,
            "total_stations": prov_total_stations,
            "percent_count": prov_percent,
            "top_parties": prov_top,
        }

    # National party summary (top 10)
    national_parties = stats.get("result_province", [])
    party_totals = {}
    for prov in provinces_result:
        for pp in prov.get("result_party", []):
            pid = pp["party_id"]
            if pid not in party_totals:
                party_totals[pid] = {"cons_votes": 0, "party_list_votes": 0, "first_mp": 0}
            party_totals[pid]["cons_votes"] += pp.get("party_cons_votes", 0)
            party_totals[pid]["party_list_votes"] += pp.get("party_list_vote", 0)
            party_totals[pid]["first_mp"] += pp.get("first_mp_app_count", 0)

    top_parties_national = sorted(party_totals.items(), key=lambda x: x[1]["cons_votes"], reverse=True)[:10]
    national_top = []
    for pid, totals in top_parties_national:
        pinfo = party_map.get(pid, {"name": f"party_{pid}", "color": "#999"})
        national_top.append({
            "party_id": pid,
            "name": pinfo["name"],
            "color": pinfo["color"],
            "cons_votes": totals["cons_votes"],
            "party_list_votes": totals["party_list_votes"],
            "first_mp_count": totals["first_mp"],
        })

    dashboard_data = {
        "metadata": {
            "last_update": last_update,
            "total_units": total_constituencies,
            "compared_units": 0,
            "version": "2.0-ect-real",
            "data_source": {
                "ect": "https://ectreport69.ect.go.th",
                "vote62": "Waiting for data"
            },
            "national_stats": {
                "turn_out": national_turnout,
                "valid_votes": national_valid,
                "invalid_votes": national_invalid,
                "blank_votes": national_blank,
                "percent_count": percent_count,
            },
            "note": "ข้อมูลจาก กกต. แบบ real-time | ยังไม่มีการเปรียบเทียบกับ Vote62"
        },
        "statistics": {
            "identical": 0,
            "minor": 0,
            "significant": 0,
            "critical": 0,
            "percentage": {
                "identical": 0,
                "minor": 0,
                "significant": 0,
                "critical": 0
            },
            "note": "รอข้อมูล Vote62 เพื่อเปรียบเทียบ"
        },
        "national_parties": national_top,
        "provinces": province_summary,
        "units": all_units,
        "timeline": [
            {
                "timestamp": last_update,
                "units_compared": 0,
                "total_units": total_constituencies,
                "percent_count": percent_count,
                "note": "ECT real data loaded"
            }
        ],
    }

    return dashboard_data


def save_json(data, filename):
    """บันทึก JSON"""
    filepath = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ บันทึก: {filepath}")
    return filepath


def main():
    """ฟังก์ชันหลัก"""
    print("=" * 60)
    print(" สร้างข้อมูล Dashboard จาก ECT API (ข้อมูลจริง)")
    print("=" * 60)

    # 1. ดึงข้อมูลจาก API
    print("\n[1/4] ดึงข้อมูลจาก ECT API...")
    stats = fetch_json(STATS_URL, "ผลคะแนน (stats_cons)")
    provinces = fetch_json(PROVINCE_URL, "ข้อมูลจังหวัด")
    parties = fetch_json(PARTY_URL, "ข้อมูลพรรค")

    if not stats or not provinces or not parties:
        print("\n❌ ไม่สามารถดึงข้อมูลได้ครบ กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต")
        return

    # 2. สร้าง lookup maps
    print("\n[2/4] สร้าง lookup maps...")
    province_map = build_province_map(provinces)
    party_map = build_party_map(parties)
    print(f"  จังหวัด: {len(province_map)} รายการ")
    print(f"  พรรค: {len(party_map)} รายการ")

    # 3. สร้าง dashboard data
    print("\n[3/4] สร้างข้อมูล Dashboard...")
    dashboard_data = create_dashboard_data(stats, province_map, party_map)

    total_units = dashboard_data["metadata"]["total_units"]
    total_provs = len(dashboard_data["provinces"])
    print(f"  เขตเลือกตั้ง: {total_units}")
    print(f"  จังหวัด: {total_provs}")

    # 4. บันทึก
    print("\n[4/4] บันทึกไฟล์...")
    save_json(dashboard_data, "election_data.json")
    save_json(stats, "ect_stats_raw.json")

    # สรุป
    print("\n" + "=" * 60)
    print(" ✅ เสร็จสมบูรณ์!")
    print("=" * 60)
    print(f"\n📊 สรุป:")
    print(f"  - เขตเลือกตั้ง: {total_units} เขต")
    print(f"  - จังหวัด: {total_provs} จังหวัด")
    print(f"  - นับคะแนนแล้ว: {dashboard_data['metadata']['national_stats']['percent_count']:.2f}%")
    print(f"  - ผู้มาใช้สิทธิ: {dashboard_data['metadata']['national_stats']['turn_out']:,} คน")
    print(f"  - คะแนนที่ถูกต้อง: {dashboard_data['metadata']['national_stats']['valid_votes']:,}")

    if dashboard_data.get("national_parties"):
        print(f"\n🏆 พรรคที่ได้คะแนนสูงสุด (เขต):")
        for i, p in enumerate(dashboard_data["national_parties"][:5], 1):
            print(f"  {i}. {p['name']}: {p['cons_votes']:,} คะแนน ({p['first_mp_count']} เขต อันดับ 1)")

    print(f"\n📁 ไฟล์ที่สร้าง:")
    print(f"  - data/election_data.json")
    print(f"  - data/ect_stats_raw.json")
    print(f"\nขั้นตอนต่อไป:")
    print(f"  git add -A")
    print(f'  git commit -m "Update: Real ECT vote results"')
    print(f"  git push origin main")
    print("=" * 60)


if __name__ == "__main__":
    main()
