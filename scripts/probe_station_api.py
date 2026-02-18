#!/usr/bin/env python3
"""Probe ECT API for station-level (per-polling-unit) data endpoints."""
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
}

ENDPOINTS = [
    # Stats endpoints
    "https://stats-ectreport69.ect.go.th/data/records/stats_station.json",
    "https://stats-ectreport69.ect.go.th/data/records/stats_vote_station.json",
    "https://stats-ectreport69.ect.go.th/data/records/stats_unit.json",
    "https://stats-ectreport69.ect.go.th/data/records/stats_polling.json",
    # Per-constituency station data
    "https://stats-ectreport69.ect.go.th/data/records/station/1.json",
    "https://stats-ectreport69.ect.go.th/data/records/station/BKK_1.json",
    "https://stats-ectreport69.ect.go.th/data/records/cons/1.json",
    "https://stats-ectreport69.ect.go.th/data/records/cons/BKK_1.json",
    # Static ref endpoints
    "https://static-ectreport69.ect.go.th/data/data/refs/info_vote_station.json",
    "https://static-ectreport69.ect.go.th/data/data/refs/info_station.json",
    "https://static-ectreport69.ect.go.th/data/data/refs/info_polling_station.json",
    # Document / image endpoints
    "https://static-ectreport69.ect.go.th/data/data/docs/index.json",
    "https://static-ectreport69.ect.go.th/data/data/docs/ss518/index.json",
    "https://static-ectreport69.ect.go.th/data/docs/index.json",
    # ect.go.th main site - election-2026 API
    "https://www.ect.go.th/th/api/election-2026",
    "https://www.ect.go.th/th/api/election-2026/results",
    "https://www.ect.go.th/ect_th/api/election-2026",
    # Try the mini site pattern (found in earlier search)
    "https://www.ect.go.th/mini/api/election-2026",
    # ectreport69 new patterns
    "https://ectreport69.ect.go.th/api/station",
    "https://ectreport69.ect.go.th/api/results",
    "https://stats-ectreport69.ect.go.th/data/station/1/1.json",
    "https://stats-ectreport69.ect.go.th/data/station/10/1.json",
    # Try with province ID (10=BKK) and cons_no
    "https://stats-ectreport69.ect.go.th/data/records/station_10_1.json",
    "https://stats-ectreport69.ect.go.th/data/records/10/1.json",
]

def main():
    print("Probing ECT station-level endpoints...")
    print("=" * 60)
    found = []
    for url in ENDPOINTS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            status = r.status_code
            size = len(r.content)
            ct = r.headers.get("Content-Type", "")[:40]
            marker = "✅" if status == 200 else "❌"
            print(f"  {marker} {status} {size:>8} bytes  {ct:30s}  {url}")
            if status == 200 and size > 50:
                found.append(url)
                # Show first 200 chars for small responses
                if size < 2000:
                    print(f"     BODY: {r.text[:200]}")
        except Exception as e:
            print(f"  ⚠️  ERROR  {str(e)[:50]:50s}  {url}")

    print("\n" + "=" * 60)
    if found:
        print(f"🎉 Found {len(found)} working endpoint(s):")
        for u in found:
            print(f"  → {u}")
    else:
        print("❌ No station-level endpoints found yet.")

if __name__ == "__main__":
    main()
