#!/usr/bin/env python3
"""Probe ECT API endpoints to find vote result data"""
import requests

BASE = "https://static-ectreport69.ect.go.th/data/data"
CONS = "BKK_1"
PROV = "BKK"

patterns = [
    # Score patterns
    f"{BASE}/score_cons/{CONS}.json",
    f"{BASE}/score_prov/{PROV}.json",
    f"{BASE}/score/{CONS}.json",
    f"{BASE}/score/{PROV}.json",
    f"{BASE}/scores/{CONS}.json",
    f"{BASE}/scores/{PROV}.json",
    # Result patterns
    f"{BASE}/result/{CONS}.json",
    f"{BASE}/result/{PROV}.json",
    f"{BASE}/results/{CONS}.json",
    f"{BASE}/results/{PROV}.json",
    # Constituency patterns
    f"{BASE}/cons/{CONS}.json",
    f"{BASE}/cons/{PROV}.json",
    f"{BASE}/constituency/{CONS}.json",
    # Province patterns
    f"{BASE}/prov/{PROV}.json",
    f"{BASE}/province/{PROV}.json",
    # Direct patterns
    f"{BASE}/{CONS}.json",
    f"{BASE}/{PROV}.json",
    f"{BASE}/{PROV}/{CONS}.json",
    f"{BASE}/{PROV}/1.json",
    # Summary patterns
    f"{BASE}/summary.json",
    f"{BASE}/overall.json",
    f"{BASE}/total.json",
    f"{BASE}/dashboard.json",
    f"{BASE}/national.json",
    # Refs patterns
    f"{BASE}/refs/info_party.json",
    f"{BASE}/refs/info_candidate.json",
    f"{BASE}/refs/info_candidates.json",
    f"{BASE}/refs/parties.json",
    f"{BASE}/refs/candidates.json",
    f"{BASE}/refs/summary.json",
    # Report patterns
    f"{BASE}/report/{CONS}.json",
    f"{BASE}/report/{PROV}.json",
    # Vote patterns
    f"{BASE}/vote/{CONS}.json",
    f"{BASE}/votes/{CONS}.json",
    # Data patterns  
    f"{BASE}/data/{CONS}.json",
    f"{BASE}/data/{PROV}.json",
    # Different base
    "https://static-ectreport69.ect.go.th/data/{}.json".format(CONS),
    "https://static-ectreport69.ect.go.th/data/score/{}.json".format(CONS),
    "https://static-ectreport69.ect.go.th/data/result/{}.json".format(CONS),
    "https://static-ectreport69.ect.go.th/data/summary.json",
    "https://static-ectreport69.ect.go.th/data/refs/info_party.json",
    # API base
    "https://ectreport69.ect.go.th/api/score/{}.json".format(CONS),
    "https://ectreport69.ect.go.th/api/result/{}.json".format(CONS),
    "https://ectreport69.ect.go.th/api/cons/{}.json".format(CONS),
    "https://ectreport69.ect.go.th/api/summary",
    "https://ectreport69.ect.go.th/api/score/prov/{}".format(PROV),
    "https://ectreport69.ect.go.th/api/score/cons/{}".format(CONS),
]

print(f"Probing {len(patterns)} URLs...")
print("=" * 70)

found = []
for url in patterns:
    try:
        r = requests.get(url, timeout=10)
        status = r.status_code
        if status == 200:
            preview = r.text[:200]
            print(f"\n✅ {status} {url}")
            print(f"   Preview: {preview}")
            found.append(url)
        elif status != 404:
            print(f"⚠️  {status} {url}")
    except Exception as e:
        print(f"❌ ERR {url}: {e}")

print("\n" + "=" * 70)
print(f"\n✅ Found {len(found)} working endpoints:")
for url in found:
    print(f"  - {url}")
