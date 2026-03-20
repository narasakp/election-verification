#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare cross-reference JSON for the Review App.
Merges data from 4 sources:
  1. ECT official (ect_stats_cons.json + ect_provinces.json)
  2. Killernay ground truth (killernay_summary_winners.csv)
  3. Luengnat dashboard (placeholder — data not yet available)
  4. Our OCR data is loaded live in the React app

Output: review-app/public/data/cross_reference_sources.json
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "review-app" / "public" / "data" / "cross_reference_sources.json"


def load_ect_provinces():
    """Load ECT province reference → {prov_id: {province, registered, stations}}"""
    path = DATA / "ect_provinces.json"
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return {}
    raw = json.loads(path.read_text("utf-8"))
    # Structure: {"province": [...], "total_registered_vote": ..., ...}
    prov_list = raw.get("province", raw) if isinstance(raw, dict) else raw
    mapping = {}
    for p in prov_list:
        mapping[p["prov_id"]] = {
            "province": p["province"],
            "registered": p.get("total_registered_vote", 0),
            "stations": p.get("total_vote_stations", 0),
        }
    return mapping


def load_ect_stats(prov_map):
    """Load ECT constituency stats → dict keyed by 'province_zone'"""
    path = DATA / "ect_stats_cons.json"
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return {}
    raw = json.loads(path.read_text("utf-8"))
    result = {}
    for prov in raw.get("result_province", []):
        pid = prov["prov_id"]
        pinfo = prov_map.get(pid, {})
        prov_name = pinfo.get("province", pid)
        for cons in prov.get("constituencies", []):
            # cons_id like "BKK_1", "CPM_3"
            cid = cons.get("cons_id", "")
            parts = cid.rsplit("_", 1)
            zone = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
            if zone == 0:
                continue  # skip province-level aggregate (zone 0)

            # Top candidate
            candidates = cons.get("candidates", [])
            top_cand = None
            if candidates:
                ranked = sorted(candidates, key=lambda c: c.get("mp_app_rank", 999))
                top_cand = {
                    "id": ranked[0].get("mp_app_id", ""),
                    "votes": ranked[0].get("mp_app_vote", 0),
                    "party_id": ranked[0].get("party_id", 0),
                }

            key = f"{prov_name}_{zone}"
            result[key] = {
                "source": "ect",
                "province": prov_name,
                "zone": zone,
                "turnout": cons.get("turn_out", 0),
                "valid_votes": cons.get("valid_votes", 0),
                "invalid_votes": cons.get("invalid_votes", 0),
                "blank_votes": cons.get("blank_votes", 0),
                "counted_stations": cons.get("counted_vote_stations", 0),
                "percent_count": round(cons.get("percent_count", 0), 2),
                "top_candidate": top_cand,
                "candidate_count": len(candidates),
            }
    return result


def load_killernay():
    """Load Killernay summary winners CSV → dict keyed by 'province_zone'"""
    path = DATA / "killernay_summary_winners.csv"
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return {}
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prov = row.get("จังหวัด", "").strip()
            zone = row.get("เขต", "").strip()
            if not prov or not zone:
                continue
            key = f"{prov}_{zone}"
            result[key] = {
                "source": "killernay",
                "province": prov,
                "zone": int(zone) if zone.isdigit() else zone,
                "winner": row.get("ผู้ชนะ", "").strip(),
                "winner_party": row.get("พรรค", "").strip(),
                "winner_votes": _int(row.get("คะแนน", "0")),
                "valid_votes": _int(row.get("คะแนนดี", "0")),
                "registered": _int(row.get("ผู้มีสิทธิ", "0")),
                "turnout": _int(row.get("มาใช้สิทธิ", "0")),
            }
    return result


def load_killernay_candidates():
    """Load Killernay full constituency CSV → dict keyed by 'province_zone'
    with total candidate votes sum per constituency."""
    path = DATA / "killernay_constituency_full.csv"
    if not path.exists():
        return {}
    groups = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prov = row.get("จังหวัด", "").strip()
            zone = row.get("เขต", "").strip()
            if not prov or not zone:
                continue
            key = f"{prov}_{zone}"
            if key not in groups:
                groups[key] = {"candidates": 0, "total_votes": 0}
            groups[key]["candidates"] += 1
            groups[key]["total_votes"] += _int(row.get("คะแนน", "0"))
    return groups


def _int(s):
    try:
        return int(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def main():
    print("📊 Preparing cross-reference sources...")

    prov_map = load_ect_provinces()
    print(f"   ECT provinces: {len(prov_map)}")

    ect_data = load_ect_stats(prov_map)
    print(f"   ECT constituencies: {len(ect_data)}")

    killernay_data = load_killernay()
    print(f"   Killernay constituencies: {len(killernay_data)}")

    killernay_cands = load_killernay_candidates()
    print(f"   Killernay candidate groups: {len(killernay_cands)}")

    # Merge all keys
    all_keys = sorted(set(list(ect_data.keys()) + list(killernay_data.keys())))
    print(f"   Total unique constituencies: {len(all_keys)}")

    # Build merged records
    records = []
    for key in all_keys:
        ect = ect_data.get(key)
        kn = killernay_data.get(key)
        kn_cands = killernay_cands.get(key, {})

        # Determine province/zone from whichever source has it
        province = (ect or kn or {}).get("province", key.rsplit("_", 1)[0])
        zone_str = key.rsplit("_", 1)[-1]
        zone = int(zone_str) if zone_str.isdigit() else zone_str

        rec = {
            "key": key,
            "province": province,
            "zone": zone,
        }

        if ect:
            rec["ect"] = {
                "turnout": ect["turnout"],
                "valid_votes": ect["valid_votes"],
                "invalid_votes": ect["invalid_votes"],
                "blank_votes": ect["blank_votes"],
                "counted_stations": ect["counted_stations"],
                "percent_count": ect["percent_count"],
                "top_candidate": ect.get("top_candidate"),
                "candidate_count": ect["candidate_count"],
            }

        if kn:
            kn_rec = {
                "turnout": kn["turnout"],
                "valid_votes": kn["valid_votes"],
                "registered": kn["registered"],
                "winner": kn["winner"],
                "winner_party": kn["winner_party"],
                "winner_votes": kn["winner_votes"],
            }
            if kn_cands:
                kn_rec["candidate_count"] = kn_cands["candidates"]
                kn_rec["total_candidate_votes"] = kn_cands["total_votes"]
            rec["killernay"] = kn_rec

        # Luengnat placeholder
        rec["luengnat"] = None  # data not yet available

        # Compute diffs where both sources available
        if ect and kn:
            ect_turnout = ect["turnout"]
            kn_turnout = kn["turnout"]
            ect_valid = ect["valid_votes"]
            kn_valid = kn["valid_votes"]

            rec["diff_ect_kn"] = {
                "turnout": ect_turnout - kn_turnout,
                "turnout_pct": round((ect_turnout - kn_turnout) / max(kn_turnout, 1) * 100, 2),
                "valid_votes": ect_valid - kn_valid,
                "valid_pct": round((ect_valid - kn_valid) / max(kn_valid, 1) * 100, 2),
            }

        records.append(rec)

    # Province summary for ECT
    prov_summary = {}
    for pid, pinfo in prov_map.items():
        prov_summary[pinfo["province"]] = {
            "registered": pinfo["registered"],
            "stations": pinfo["stations"],
        }

    output = {
        "generated": __import__("datetime").datetime.now().isoformat(),
        "sources": {
            "ect": {"name": "กกต. (ECT Official)", "records": len(ect_data), "status": "available"},
            "killernay": {"name": "Killernay (OCR Ground Truth)", "records": len(killernay_data), "status": "available"},
            "luengnat": {"name": "Luengnat Dashboard", "records": 0, "status": "pending"},
            "ocr": {"name": "ระบบ OCR ของเรา", "records": 0, "status": "live"},
        },
        "province_summary": prov_summary,
        "constituencies": records,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"\n✅ Output: {OUT.relative_to(ROOT)} ({size_kb:.0f} KB)")
    print(f"   {len(records)} constituency records")
    print(f"   Sources: ECT={len(ect_data)}, Killernay={len(killernay_data)}, Luengnat=0 (pending)")


if __name__ == "__main__":
    main()
