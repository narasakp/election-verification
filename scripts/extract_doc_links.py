#!/usr/bin/env python3
"""
Extract สส.5/18 document links from provincial ECT election-2026 pages.
These are Nuxt SPA pages with embedded data — we need to find the actual
PDF/document URLs inside the full HTML (including inline scripts/data).
"""
import os
import re
import json
import time
import requests
from urllib.parse import urljoin, unquote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")

# Test provinces
TEST_SLUGS = ["bangkok", "amnatcharoen", "chiangmai", "nakhonratchasima", "songkhla"]


def fetch(url, timeout=30):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        print(f"  ⚠️ {e}")
        return None


def extract_all_urls(text, base_url="https://www.ect.go.th"):
    """Extract ALL URLs from text — including embedded JSON, scripts, etc."""
    urls = set()

    # Pattern 1: Standard href/src
    for m in re.findall(r'(?:href|src|url|link)[\s=:]*["\']([^"\']+)["\']', text, re.IGNORECASE):
        urls.add(urljoin(base_url, m))

    # Pattern 2: Direct http(s) URLs in text
    for m in re.findall(r'https?://[^\s"\'<>\]\)]+', text):
        urls.add(m)

    # Pattern 3: web-upload paths (common ECT pattern)
    for m in re.findall(r'/(?:web-upload|mini/+web-upload)/[^\s"\'<>\]\)]+', text):
        urls.add(urljoin(base_url, m))

    # Pattern 4: file_download hashes
    for m in re.findall(r'file_download/[a-f0-9]{32}(?:\.[a-z]+)?', text):
        urls.add(urljoin(base_url, m))

    return urls


def categorize_urls(urls):
    """Categorize URLs by type."""
    docs = {"pdf": [], "image": [], "other_doc": []}
    for u in urls:
        lower = u.lower()
        # Skip obvious non-documents
        if any(skip in lower for skip in ['favicon', 'logo', 'banner', 'thumbnail', '.css', '.js', 'font', 'recaptcha', 'google']):
            continue
        if lower.endswith('.pdf') or ('file_download' in lower and '.pdf' not in lower):
            docs["pdf"].append(u)
        elif any(lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            if 'web-upload' in lower or 'file_download' in lower:
                docs["image"].append(u)
        elif 'file_download' in lower:
            docs["other_doc"].append(u)
    return docs


def analyze_page_structure(html, slug):
    """Analyze the structure of a province election-2026 page."""
    results = {
        "slug": slug,
        "html_size": len(html),
        "has_nuxt_data": False,
        "embedded_json_count": 0,
        "doc_urls": {"pdf": [], "image": [], "other_doc": []},
        "election_keywords": [],
    }

    # Check for Nuxt embedded data
    nuxt_matches = re.findall(r'(?:__NUXT_DATA__|__NUXT__|nuxtData|window\.__NUXT__)\s*=\s*', html)
    results["has_nuxt_data"] = len(nuxt_matches) > 0

    # Find script tags with JSON content
    script_contents = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    results["embedded_json_count"] = len(script_contents)

    # Extract all URLs from the entire page
    all_urls = extract_all_urls(html)
    results["total_urls"] = len(all_urls)

    # Categorize
    docs = categorize_urls(all_urls)
    results["doc_urls"] = docs

    # Check for election-related keywords in the raw HTML
    keywords = ["สส.5/18", "สส.5/11", "สส.5/16", "สส.5/17", "ผลคะแนนรายหน่วย", "รายหน่วยเลือกตั้ง", "file_download"]
    for kw in keywords:
        if kw in html:
            count = html.count(kw)
            results["election_keywords"].append({"keyword": kw, "count": count})

    # Look for large embedded data blocks (could contain base64 PDFs or document lists)
    large_scripts = re.findall(r'<script[^>]*>((?:(?!</script>).){10000,})</script>', html, re.DOTALL)
    results["large_script_blocks"] = len(large_scripts)
    if large_scripts:
        # Search large scripts for doc patterns
        for i, script in enumerate(large_scripts):
            script_urls = extract_all_urls(script)
            script_docs = categorize_urls(script_urls)
            if any(script_docs.values()):
                results[f"script_block_{i}_docs"] = {k: v for k, v in script_docs.items() if v}

    return results


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print(" สกัดลิงก์เอกสาร สส.5/18 จากเว็บจังหวัด กกต.")
    print("=" * 60)

    all_results = []

    for slug in TEST_SLUGS:
        url = f"https://www.ect.go.th/{slug}/th/election-2026"
        print(f"\n{'='*40}")
        print(f"🔍 {slug}: {url}")
        print(f"{'='*40}")

        r = fetch(url)
        if not r or r.status_code != 200:
            print(f"  ❌ Failed: {r.status_code if r else 'timeout'}")
            continue

        html = r.text
        print(f"  HTML size: {len(html):,} bytes")

        # Analyze
        result = analyze_page_structure(html, slug)
        all_results.append(result)

        # Print findings
        print(f"  Nuxt data: {result['has_nuxt_data']}")
        print(f"  Embedded JSON blocks: {result['embedded_json_count']}")
        print(f"  Large script blocks: {result['large_script_blocks']}")
        print(f"  Total URLs found: {result['total_urls']}")
        print(f"  PDF docs: {len(result['doc_urls']['pdf'])}")
        print(f"  Image docs: {len(result['doc_urls']['image'])}")
        print(f"  Other docs: {len(result['doc_urls']['other_doc'])}")

        if result["election_keywords"]:
            print(f"  Keywords: {result['election_keywords']}")

        if result["doc_urls"]["pdf"]:
            print(f"  📄 PDF links:")
            for u in result["doc_urls"]["pdf"][:10]:
                print(f"    {u}")

        if result["doc_urls"]["other_doc"]:
            print(f"  📎 Other doc links:")
            for u in result["doc_urls"]["other_doc"][:10]:
                print(f"    {u}")

        # Save individual page HTML for deeper analysis
        page_dir = os.path.join(DATA_DIR, "province_pages")
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(html)

        time.sleep(1)

    # Save results
    out = os.path.join(DATA_DIR, "doc_extraction_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n\n✅ Saved: {out}")

    # Summary
    total_pdfs = sum(len(r["doc_urls"]["pdf"]) for r in all_results)
    total_docs = sum(len(r["doc_urls"]["other_doc"]) for r in all_results)
    print(f"\nSummary ({len(TEST_SLUGS)} provinces tested):")
    print(f"  Total PDFs: {total_pdfs}")
    print(f"  Total other docs: {total_docs}")
    if total_pdfs == 0 and total_docs == 0:
        print("\n⚠️ ไม่พบลิงก์เอกสารในหน้าเว็บ — เนื้อหาน่าจะโหลดด้วย JavaScript (SPA)")
        print("   ต้องใช้วิธีอื่น เช่น:")
        print("   1. ดู API ที่ SPA เรียก (ผ่าน browser DevTools)")
        print("   2. ใช้ Headless browser (Playwright/Puppeteer)")
        print("   3. วิเคราะห์ Nuxt payload/API endpoints")


if __name__ == "__main__":
    main()
