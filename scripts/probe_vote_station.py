"""Probe ECT API for per-polling-station (vote station) data."""
import requests
import json

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Known endpoints from JS bundle analysis
ENDPOINTS = [
    # Stats endpoints - try station-level
    "https://stats-ectreport69.ect.go.th/data/records/stats_cons.json",
    "https://stats-ectreport69.ect.go.th/data/records/stats_station.json",
    "https://stats-ectreport69.ect.go.th/data/records/stats_vote_station.json",
    # Per-constituency station data patterns
    "https://stats-ectreport69.ect.go.th/data/records/cons/BKK_1.json",
    "https://stats-ectreport69.ect.go.th/data/cons/BKK_1.json",
    "https://stats-ectreport69.ect.go.th/data/records/station/BKK_1.json",
    "https://stats-ectreport69.ect.go.th/data/station/BKK_1.json",
    # Static data endpoints
    "https://static-ectreport69.ect.go.th/data/data/records/stats_cons.json",
    "https://static-ectreport69.ect.go.th/data/data/records/stats_station.json",
    "https://static-ectreport69.ect.go.th/data/data/cons/BKK_1.json",
    "https://static-ectreport69.ect.go.th/data/data/station/BKK_1.json",
    "https://static-ectreport69.ect.go.th/data/data/refs/info_vote_station.json",
    # Referendum station data
    "https://stats-ectreport69.ect.go.th/data/records/stats_referendum.json",
]

print("=== Probing ECT endpoints for station-level data ===\n")
for url in ENDPOINTS:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        short = url.replace("https://stats-ectreport69.ect.go.th", "STATS")
        short = short.replace("https://static-ectreport69.ect.go.th", "STATIC")
        if r.status_code == 200:
            data = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text[:200]
            if isinstance(data, dict):
                keys = list(data.keys())[:10]
                print(f"OK  {short}")
                print(f"    Keys: {keys}")
                # Check for station/vote_station data
                for k in ["vote_stations", "stations", "result_station", "station"]:
                    if k in data:
                        val = data[k]
                        if isinstance(val, list):
                            print(f"    >>> Found '{k}' with {len(val)} items!")
                            if len(val) > 0:
                                print(f"    Sample: {json.dumps(val[0], ensure_ascii=False)[:300]}")
                        elif isinstance(val, dict):
                            print(f"    >>> Found '{k}' dict keys: {list(val.keys())[:5]}")
                # Check nested province data for station info
                if "result_province" in data:
                    prov = data["result_province"]
                    if isinstance(prov, list) and len(prov) > 0:
                        p0 = prov[0]
                        print(f"    Province[0] keys: {list(p0.keys())[:10]}")
                        if "result_cons" in p0:
                            cons = p0["result_cons"]
                            if isinstance(cons, list) and len(cons) > 0:
                                c0 = cons[0]
                                print(f"    Cons[0] keys: {list(c0.keys())[:15]}")
                                for sk in ["vote_stations","stations","result_station","station_results"]:
                                    if sk in c0:
                                        print(f"    >>> Cons has '{sk}'!")
            elif isinstance(data, list):
                print(f"OK  {short} - List with {len(data)} items")
                if len(data) > 0:
                    print(f"    Sample keys: {list(data[0].keys())[:10] if isinstance(data[0],dict) else str(data[0])[:200]}")
            else:
                print(f"OK  {short} - {str(data)[:200]}")
        else:
            print(f"{r.status_code} {short}")
    except Exception as e:
        print(f"ERR {url[:60]}... - {e}")

# Now check the JS bundle for station-related endpoints
print("\n=== Checking JS bundle for station endpoints ===\n")
try:
    r = requests.get("https://ectreport69.ect.go.th/", headers=HEADERS, timeout=10)
    import re
    js_files = re.findall(r'src="(/assets/[^"]+\.js)"', r.text)
    print(f"Found JS files: {js_files}")
    for js in js_files:
        jr = requests.get(f"https://ectreport69.ect.go.th{js}", headers=HEADERS, timeout=15)
        # Search for station-related patterns
        patterns = re.findall(r'["\']([^"\']*(?:station|vote_station|หน่วย)[^"\']*)["\']', jr.text, re.IGNORECASE)
        if patterns:
            print(f"\nStation patterns in {js}:")
            for p in set(patterns):
                if len(p) < 150:
                    print(f"  {p}")
        # Search for data URL patterns
        url_patterns = re.findall(r'["\']([^"\']*(?:/data/|/records/|/refs/)[^"\']*)["\']', jr.text)
        if url_patterns:
            print(f"\nData URLs in {js}:")
            for p in sorted(set(url_patterns)):
                if len(p) < 150:
                    print(f"  {p}")
except Exception as e:
    print(f"JS bundle check error: {e}")
