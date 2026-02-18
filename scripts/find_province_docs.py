#!/usr/bin/env python3
"""
Find provincial ECT office websites and สส.5/18 document links.
Strategy:
1. Fetch the Nuxt API / builds meta to find content for election-2026 page
2. Fetch the province offices page for a list of provincial sites
3. Probe known provincial site patterns for document sections
"""
import os
import re
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# Known provincial site IDs from earlier findings
# Pattern: https://www.ect.go.th/mini//web-upload/{HASH}/...
# 11xc410600758f76a9b83604e779b2d1de5 = one province
# 63xa1d86322de1e6a3c0c425fc734b74f91 = another province

def try_fetch(url, label=""):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        print(f"  {'✅' if r.status_code == 200 else '❌'} {r.status_code} {len(r.text):>8} {label or url}")
        return r
    except Exception as e:
        print(f"  ⚠️ ERROR {label or url}: {e}")
        return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    results = {}

    # 1. Try Nuxt builds/meta JSON (referenced in the SPA HTML)
    print("=" * 60)
    print("1. Checking Nuxt meta/API endpoints...")
    meta_url = "https://www.ect.go.th/ect_th/_ect/builds/meta/0364dd06-d5c9-4903-8828-46de687baa91.json"
    r = try_fetch(meta_url, "Nuxt meta JSON")
    if r and r.status_code == 200:
        try:
            meta = r.json()
            print(f"     Keys: {list(meta.keys())[:10]}")
            # Save it
            with open(os.path.join(DATA_DIR, "ect_nuxt_meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            # Look for election-2026 related content
            text = json.dumps(meta, ensure_ascii=False)
            if "election" in text.lower():
                matches = re.findall(r'"[^"]*election[^"]*"', text, re.IGNORECASE)
                print(f"     Election refs: {matches[:10]}")
        except:
            print(f"     (not JSON, first 200 chars: {r.text[:200]})")

    # 2. Try ect_th internal API patterns
    print("\n" + "=" * 60)
    print("2. Trying internal API patterns for election-2026 content...")
    api_urls = [
        "https://www.ect.go.th/ect_th/api/content/election-2026",
        "https://www.ect.go.th/ect_th/api/pages/election-2026",
        "https://www.ect.go.th/ect_th/api/election-2026/files",
        "https://www.ect.go.th/ect_th/api/media/election-2026",
        "https://www.ect.go.th/ect_th/_payload.json",
        # Province offices
        "https://www.ect.go.th/ect_th/api/ect-province-offices",
        "https://www.ect.go.th/ect_th/api/content/ect-province-offices",
    ]
    for url in api_urls:
        r = try_fetch(url)
        if r and r.status_code == 200 and len(r.text) > 100:
            # Check if JSON
            try:
                data = r.json()
                print(f"     JSON keys: {list(data.keys())[:5] if isinstance(data, dict) else f'array[{len(data)}]'}")
                results[url] = {"type": "json", "size": len(r.text)}
            except:
                # Check for useful links in HTML
                links = re.findall(r'href=["\']([^"\']*(?:election|province|mini|web-upload)[^"\']*)["\']', r.text, re.IGNORECASE)
                if links:
                    print(f"     Links found: {len(links)}")
                    for l in links[:5]:
                        print(f"       {l}")
                results[url] = {"type": "html", "size": len(r.text)}

    # 3. Try known provincial mini sites
    print("\n" + "=" * 60)
    print("3. Probing known provincial mini site patterns...")
    # Try to get the main mini site index
    mini_urls = [
        "https://www.ect.go.th/mini/",
        "https://www.ect.go.th/mini/api/provinces",
        "https://www.ect.go.th/mini/api/sites",
    ]
    for url in mini_urls:
        r = try_fetch(url)
        if r and r.status_code == 200:
            # Look for province links or site IDs
            hashes = re.findall(r'[0-9]+x[a-f0-9]{32,40}', r.text)
            if hashes:
                unique = list(set(hashes))
                print(f"     Province hashes found: {len(unique)}")
                for h in unique[:10]:
                    print(f"       {h}")

    # 4. Try to fetch province list from ect-province-offices page
    print("\n" + "=" * 60)
    print("4. Fetching province offices page...")
    r = try_fetch("https://www.ect.go.th/ect_th/th/ect-province-offices", "Province offices page")
    if r and r.status_code == 200:
        # Save HTML
        with open(os.path.join(DATA_DIR, "ect_province_offices.html"), "w", encoding="utf-8") as f:
            f.write(r.text)
        # Extract province site links
        prov_links = re.findall(r'href=["\']([^"\']*(?:ect\.go\.th/[^"\']*province|ect\.go\.th/mini)[^"\']*)["\']', r.text, re.IGNORECASE)
        mini_links = re.findall(r'https?://www\.ect\.go\.th/[a-z]+/', r.text)
        all_links = list(set(prov_links + mini_links))
        if all_links:
            print(f"     Province/mini links: {len(all_links)}")
            for l in sorted(all_links)[:20]:
                print(f"       {l}")

        # Also look for JSON/API calls in the page
        api_calls = re.findall(r'(?:fetch|axios|api|endpoint)[^"\']*["\']([^"\']+)["\']', r.text)
        if api_calls:
            print(f"     API calls found: {api_calls[:5]}")

    # 5. Try specific provincial document patterns
    print("\n" + "=" * 60)
    print("5. Probing document download patterns for known provinces...")
    # Use known hash: 11xc410600758f76a9b83604e779b2d1de5
    base = "https://www.ect.go.th/mini//web-upload/11xc410600758f76a9b83604e779b2d1de5"
    doc_patterns = [
        f"{base}/m_document/",
        f"{base}/202602/",
        f"{base}/202602/m_document/",
        f"{base}/election-2026/",
        f"{base}/ss518/",
    ]
    for url in doc_patterns:
        r = try_fetch(url)

    # 6. Try the election-2026 page directly with different approaches
    print("\n" + "=" * 60)
    print("6. Trying election-2026 page with cookie/session...")
    session = requests.Session()
    # First get the main page to get cookies
    r1 = session.get("https://www.ect.go.th/ect_th/th/main", headers=HEADERS, timeout=20)
    print(f"  Main page: {r1.status_code}, cookies: {list(session.cookies.keys())}")
    # Then try election-2026
    r2 = session.get("https://www.ect.go.th/ect_th/th/election-2026", headers=HEADERS, timeout=20)
    print(f"  Election-2026: {r2.status_code}, size: {len(r2.text)}")
    if r2.status_code == 200:
        # Look for embedded data or API URLs
        data_matches = re.findall(r'__NUXT_DATA__\s*=\s*(\[.*?\])', r2.text[:50000], re.DOTALL)
        if data_matches:
            print(f"  Found __NUXT_DATA__ ({len(data_matches[0])} chars)")
        # Look for any file/document links
        file_links = re.findall(r'https?://[^\s"\'<>]+(?:\.pdf|\.jpg|\.jpeg|\.png|file_download)[^\s"\'<>]*', r2.text)
        if file_links:
            unique_files = list(set(file_links))
            print(f"  File links found: {len(unique_files)}")
            for fl in unique_files[:10]:
                print(f"    {fl}")
        # Check for province-specific patterns
        prov_hashes = re.findall(r'[0-9]+x[a-f0-9]{30,}', r2.text)
        if prov_hashes:
            unique_hashes = list(set(prov_hashes))
            print(f"  Province hashes: {len(unique_hashes)}")
            for h in unique_hashes[:10]:
                print(f"    {h}")
        # Save
        with open(os.path.join(DATA_DIR, "ect_election_2026_session.html"), "w", encoding="utf-8") as f:
            f.write(r2.text)

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
