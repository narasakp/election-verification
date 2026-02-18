#!/usr/bin/env python3
"""
Crawl provincial ECT office websites to find สส.5/18 document links.
1. Build list of 77 provincial slugs
2. For each province, find the election results / document section
3. Extract document download links (PDF/JPG)
4. Save a master index as JSON
"""
import os
import re
import json
import time
import requests
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# All 77 provincial slugs (standard romanization used by ECT)
PROVINCE_SLUGS = [
    "bangkok", "amnatcharoen", "angthong", "buengkan", "buriram",
    "chachoengsao", "chainat", "chaiyaphum", "chanthaburi", "chiangmai",
    "chiangrai", "chonburi", "chumphon", "kalasin", "kamphaengphet",
    "kanchanaburi", "khonkaen", "krabi", "lampang", "lamphun",
    "loei", "lopburi", "maehongson", "mahasarakham", "mukdahan",
    "nakhonnayok", "nakhonpathom", "nakhonphanom", "nakhonratchasima",
    "nakhonsawan", "nakhonsithammarat", "nan", "narathiwat", "nongbualamphu",
    "nongkhai", "nonthaburi", "pathumthani", "pattani", "phangnga",
    "phatthalung", "phayao", "phetchabun", "phetchaburi", "phichit",
    "phitsanulok", "phranakhonsiayutthaya", "phrae", "phuket",
    "prachinburi", "prachuapkhirikhan", "ranong", "ratchaburi", "rayong",
    "roiet", "sakaeo", "sakonnakhon", "samutprakan", "samutsakhon",
    "samutsongkhram", "saraburi", "satun", "singburi", "sisaket",
    "songkhla", "sukhothai", "suphanburi", "suratthani", "surin",
    "tak", "trang", "trat", "ubonratchathani", "udonthani",
    "uthaithani", "uttaradit", "yala", "yasothon",
]


def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        return None


def find_doc_links(html, base_url):
    """Find document download links in HTML (PDF/JPG/file_download)."""
    links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    docs = []
    for u in links:
        abs_url = urljoin(base_url, u)
        lower = abs_url.lower()
        if any(kw in lower for kw in ['.pdf', '.jpg', '.jpeg', '.png', 'file_download']):
            if 'favicon' not in lower and 'logo' not in lower:
                docs.append(abs_url)
    return list(set(docs))


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print(" สำรวจเว็บจังหวัด กกต. — หาเอกสาร สส.5/18")
    print("=" * 60)

    # Phase 1: Check which province slugs actually work
    print(f"\n[Phase 1] ตรวจสอบ {len(PROVINCE_SLUGS)} จังหวัด...")
    valid = []
    invalid = []
    for i, slug in enumerate(PROVINCE_SLUGS):
        url = f"https://www.ect.go.th/{slug}/"
        r = fetch(url, timeout=15)
        if r and r.status_code == 200 and len(r.text) > 500:
            valid.append(slug)
            mark = "✅"
        else:
            invalid.append(slug)
            mark = "❌"
            # Try alternate spellings
            alts = [slug.replace("ph", "p"), slug + "i"]
            for alt in alts:
                r2 = fetch(f"https://www.ect.go.th/{alt}/", timeout=10)
                if r2 and r2.status_code == 200 and len(r2.text) > 500:
                    valid.append(alt)
                    mark = f"✅ (→{alt})"
                    invalid.remove(slug)
                    break
        if (i + 1) % 10 == 0:
            print(f"  {mark} {i+1}/{len(PROVINCE_SLUGS)} checked, valid: {len(valid)}")
        time.sleep(0.3)

    print(f"\n  Valid: {len(valid)}, Invalid: {len(invalid)}")
    if invalid:
        print(f"  Invalid slugs: {invalid[:20]}")

    # Phase 2: For each valid province, find election results / document pages
    print(f"\n[Phase 2] หาหน้าเอกสาร สส.5/18 ใน {len(valid)} จังหวัด...")

    # Try first 5 provinces to find the pattern
    test_provinces = valid[:5]
    found_pattern = None

    for slug in test_provinces:
        base = f"https://www.ect.go.th/{slug}/"
        print(f"\n  🔍 {slug}:")

        # Try common election result page patterns
        page_patterns = [
            f"{base}th/election-2026",
            f"{base}th/election-result",
            f"{base}th/election-result-2026",
            f"{base}th/db_119",
            f"{base}th/election",
            f"{base}election-2026",
        ]

        for page_url in page_patterns:
            r = fetch(page_url, timeout=15)
            if r and r.status_code == 200 and len(r.text) > 1000:
                docs = find_doc_links(r.text, page_url)
                # Check for election-related keywords
                has_election = any(kw in r.text for kw in ['สส.5/18', '5/18', 'ผลคะแนน', 'รายหน่วย', 'election'])
                print(f"    {'✅' if has_election else '⚪'} {r.status_code} {page_url}")
                print(f"       size={len(r.text)}, docs={len(docs)}, election_kw={has_election}")
                if docs:
                    print(f"       Sample docs: {docs[:3]}")
                if has_election and docs:
                    found_pattern = page_url.replace(slug, "{slug}")
                    break
            time.sleep(0.3)

        # Also search the main page for links containing "election" or "ผลคะแนน"
        r_main = fetch(base, timeout=15)
        if r_main and r_main.status_code == 200:
            election_links = re.findall(
                r'href=["\']([^"\']*(?:election|ผลคะแนน|5-18|518|result)[^"\']*)["\']',
                r_main.text, re.IGNORECASE
            )
            if election_links:
                print(f"    📎 Election links on main page: {election_links[:5]}")
            # Also look for API/content patterns
            api_patterns = re.findall(r'api/[^\s"\'<>]+', r_main.text)
            if api_patterns:
                unique_apis = list(set(api_patterns))[:5]
                print(f"    📡 API patterns: {unique_apis}")

        time.sleep(0.5)

    # Save results
    results = {
        "valid_provinces": valid,
        "invalid_slugs": invalid,
        "found_pattern": found_pattern,
        "total_valid": len(valid),
    }
    out = os.path.join(DATA_DIR, "province_crawl_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n\n✅ Saved: {out}")
    print(f"Valid provinces: {len(valid)}")
    print(f"Pattern found: {found_pattern}")


if __name__ == "__main__":
    main()
