#!/usr/bin/env python3
"""Fetch and parse the ECT election-2026 page to find document download links."""
import os
import re
import json
from urllib.parse import urljoin
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

URLS_TO_TRY = [
    "https://www.ect.go.th/ect_th/api/election-2026",
    "https://www.ect.go.th/ect_th/th/election-2026",
    "https://www.ect.go.th/th/election-2026",
]


def extract_links(html, base_url):
    """Extract all href links from HTML."""
    raw = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    links = []
    seen = set()
    for u in raw:
        u = u.strip()
        if u.startswith("javascript:") or u.startswith("#") or u.startswith("mailto:"):
            continue
        abs_url = urljoin(base_url, u)
        if abs_url not in seen:
            seen.add(abs_url)
            links.append(abs_url)
    return links


def categorize_link(url):
    """Categorize a link by type."""
    lower = url.lower()
    if any(ext in lower for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.zip']):
        return 'document'
    if 'file_download' in lower or 'web-upload' in lower:
        return 'document'
    if 'ect.go.th' in lower and ('election' in lower or 'province' in lower):
        return 'ect_page'
    return 'other'


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    for page_url in URLS_TO_TRY:
        print(f"\nTrying: {page_url}")
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=30, allow_redirects=True)
            print(f"  Status: {r.status_code}, Size: {len(r.text)}, Final: {r.url}")
            if r.status_code == 200 and len(r.text) > 1000:
                html = r.text

                # Save raw HTML
                fname = page_url.split("/")[-1] or "election-2026"
                html_path = os.path.join(DATA_DIR, f"ect_page_{fname}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"  Saved: {html_path}")

                links = extract_links(html, r.url)
                print(f"  Total links: {len(links)}")

                # Categorize
                docs = [u for u in links if categorize_link(u) == 'document']
                ect_pages = [u for u in links if categorize_link(u) == 'ect_page']

                print(f"  Document links: {len(docs)}")
                print(f"  ECT page links: {len(ect_pages)}")

                # Show samples
                if docs:
                    print("\n  📄 Document links (first 20):")
                    for u in docs[:20]:
                        print(f"    {u}")

                if ect_pages:
                    print("\n  🔗 ECT page links (first 20):")
                    for u in ect_pages[:20]:
                        print(f"    {u}")

                # Look for province-specific patterns
                prov_pattern = re.findall(r'https?://[^\s"\'<>]*(?:province|จังหวัด|ect_th|mini)[^\s"\'<>]*', html)
                if prov_pattern:
                    prov_unique = list(set(prov_pattern))[:20]
                    print(f"\n  🗺️ Province-related URLs ({len(prov_unique)}):")
                    for u in prov_unique:
                        print(f"    {u}")

                # Look for iframe src (sometimes content is embedded)
                iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if iframes:
                    print(f"\n  📋 Iframes found ({len(iframes)}):")
                    for u in iframes:
                        print(f"    {urljoin(r.url, u)}")

                # Save link analysis
                analysis = {
                    "url": page_url,
                    "final_url": r.url,
                    "status": r.status_code,
                    "total_links": len(links),
                    "document_links": docs,
                    "ect_page_links": ect_pages,
                    "iframes": [urljoin(r.url, u) for u in iframes] if iframes else [],
                }
                json_path = os.path.join(DATA_DIR, f"ect_page_{fname}_links.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                print(f"\n  Saved analysis: {json_path}")

                # If we got good data, no need to try more URLs
                if docs or ect_pages or iframes:
                    break
        except Exception as e:
            print(f"  Error: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
