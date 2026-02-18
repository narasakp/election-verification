#!/usr/bin/env python3
"""
ดาวน์โหลดเอกสาร สส.5/18 (ใบสรุปผลคะแนนรายหน่วย) จากเว็บจังหวัด กกต. ทั้ง 77 จังหวัด

ขั้นตอน:
1. ดึงหน้า election-2026 ของแต่ละจังหวัด
2. สกัดลิงก์ PDF ทั้งหมด
3. ดาวน์โหลดแยกโฟลเดอร์ตามจังหวัด
4. Resume support — ข้ามไฟล์ที่ดาวน์โหลดแล้ว
5. Rate limit — หน่วงเวลาระหว่างดาวน์โหลด
6. Retry — ลองใหม่ 3 ครั้งถ้าล้มเหลว

Usage:
  python scripts/download_ss518.py                  # ดาวน์โหลดทุกจังหวัด
  python scripts/download_ss518.py --province bangkok chiangmai  # เฉพาะจังหวัด
  python scripts/download_ss518.py --index-only     # สร้าง index เท่านั้น (ไม่ดาวน์โหลด)
"""
import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse, unquote
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "..", "downloads", "ss518")

PROVINCE_SLUGS = [
    "amnatcharoen", "angthong", "bangkok", "buengkan", "buriram",
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

RATE_LIMIT_SECONDS = 0.5
MAX_RETRIES = 3


def fetch(url, timeout=30, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            return r
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    ⚠️ Failed after {retries} attempts: {e}")
                return None


def extract_pdf_links(html, base_url):
    """Extract all PDF/document download links from page HTML."""
    urls = set()

    # href/src patterns
    for m in re.findall(r'(?:href|src|url)[\s=:]*["\']([^"\']+)["\']', html, re.IGNORECASE):
        urls.add(urljoin(base_url, m))

    # Direct http URLs in text (catches embedded JSON/data)
    for m in re.findall(r'https?://[^\s"\'<>\]\)\\]+', html):
        urls.add(m)

    # web-upload paths
    for m in re.findall(r'/(?:web-upload|mini/+web-upload)/[^\s"\'<>\]\)\\]+', html):
        urls.add(urljoin(base_url, m))

    # Filter to PDFs and file_download only
    pdfs = []
    for u in urls:
        lower = u.lower()
        if any(skip in lower for skip in ['favicon', 'logo', 'banner', 'thumbnail', '.css', '.js', '.woff', 'recaptcha', 'google', 'cloudflare', 'cloudwise']):
            continue
        if lower.endswith('.pdf') or ('file_download' in lower and not lower.endswith(('.js', '.css', '.png', '.jpg'))):
            pdfs.append(u)

    return sorted(set(pdfs))


def safe_filename(url):
    """Create a safe filename from a URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    # Use the hash + .pdf
    match = re.search(r'file_download/([a-f0-9]+)', path)
    if match:
        return match.group(1) + ".pdf"
    # Use last path segment
    name = path.split("/")[-1]
    if not name or name == "":
        name = re.sub(r'[^\w.-]', '_', path[-40:]) + ".pdf"
    return name


def download_file(url, dest_path, retries=MAX_RETRIES):
    """Download a file with resume support."""
    # Check if already downloaded
    if os.path.exists(dest_path):
        existing_size = os.path.getsize(dest_path)
        if existing_size > 0:
            return "skipped"

    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return "downloaded"
            elif r.status_code == 404:
                return "not_found"
            else:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return f"error: {e}"

    return "failed"


def crawl_province(slug, download=True):
    """Crawl one province's election-2026 page and extract/download PDFs."""
    url = f"https://www.ect.go.th/{slug}/th/election-2026"
    print(f"\n{'='*50}")
    print(f"📍 {slug}: {url}")

    r = fetch(url)
    if not r or r.status_code != 200:
        print(f"  ❌ Page failed: {r.status_code if r else 'timeout'}")
        return {"slug": slug, "status": "page_failed", "pdfs": []}

    html = r.text
    pdfs = extract_pdf_links(html, url)
    print(f"  📄 Found {len(pdfs)} PDF links (page size: {len(html):,} bytes)")

    result = {
        "slug": slug,
        "status": "ok",
        "page_size": len(html),
        "pdf_count": len(pdfs),
        "pdfs": pdfs,
    }

    if not download:
        return result

    if not pdfs:
        print(f"  ⚠️ No PDFs found")
        return result

    # Create province download directory
    prov_dir = os.path.join(DOWNLOAD_DIR, slug)
    os.makedirs(prov_dir, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for i, pdf_url in enumerate(pdfs):
        fname = safe_filename(pdf_url)
        dest = os.path.join(prov_dir, fname)

        status = download_file(pdf_url, dest)

        if status == "downloaded":
            downloaded += 1
            size = os.path.getsize(dest)
            print(f"  ✅ [{i+1}/{len(pdfs)}] {fname} ({size:,} bytes)")
        elif status == "skipped":
            skipped += 1
        elif status == "not_found":
            failed += 1
            print(f"  ❌ [{i+1}/{len(pdfs)}] 404 {fname}")
        else:
            failed += 1
            print(f"  ⚠️ [{i+1}/{len(pdfs)}] {status}")

        time.sleep(RATE_LIMIT_SECONDS)

    result["downloaded"] = downloaded
    result["skipped"] = skipped
    result["failed"] = failed
    print(f"  📊 Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")

    return result


def main():
    parser = argparse.ArgumentParser(description="ดาวน์โหลดเอกสาร สส.5/18 จากเว็บจังหวัด กกต.")
    parser.add_argument("--province", nargs="+", help="ระบุจังหวัด (slug) เฉพาะ")
    parser.add_argument("--index-only", action="store_true", help="สร้าง index เท่านั้น ไม่ดาวน์โหลด")
    parser.add_argument("--rate-limit", type=float, default=0.5, help="หน่วงเวลา (วินาที) ระหว่างดาวน์โหลด")
    args = parser.parse_args()

    global RATE_LIMIT_SECONDS
    RATE_LIMIT_SECONDS = args.rate_limit

    slugs = args.province if args.province else PROVINCE_SLUGS
    download = not args.index_only

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print("=" * 60)
    print(f" ดาวน์โหลดเอกสาร สส.5/18 จากเว็บจังหวัด กกต.")
    print(f" จำนวนจังหวัด: {len(slugs)}")
    print(f" โหมด: {'สร้าง index เท่านั้น' if not download else 'ดาวน์โหลด'}")
    print(f" Rate limit: {RATE_LIMIT_SECONDS}s")
    print(f" Download dir: {DOWNLOAD_DIR}")
    print("=" * 60)

    all_results = []
    total_pdfs = 0
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    for i, slug in enumerate(slugs):
        print(f"\n[{i+1}/{len(slugs)}]", end="")
        result = crawl_province(slug, download=download)
        all_results.append(result)
        total_pdfs += result.get("pdf_count", 0)
        total_downloaded += result.get("downloaded", 0)
        total_skipped += result.get("skipped", 0)
        total_failed += result.get("failed", 0)

        # Save progress index after each province
        index_path = os.path.join(DATA_DIR, "ss518_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_provinces": len(slugs),
                "completed": i + 1,
                "total_pdfs": total_pdfs,
                "total_downloaded": total_downloaded,
                "total_skipped": total_skipped,
                "total_failed": total_failed,
                "provinces": all_results,
            }, f, ensure_ascii=False, indent=2)

        time.sleep(1)  # Rate limit between provinces

    # Final summary
    print("\n" + "=" * 60)
    print(" สรุปผลการดาวน์โหลด")
    print("=" * 60)
    print(f"  จังหวัดทั้งหมด: {len(slugs)}")
    print(f"  PDF ทั้งหมด: {total_pdfs}")
    if download:
        print(f"  ดาวน์โหลดใหม่: {total_downloaded}")
        print(f"  ข้ามไฟล์ซ้ำ: {total_skipped}")
        print(f"  ล้มเหลว: {total_failed}")
    print(f"\n  📁 Index: {index_path}")
    if download:
        print(f"  📁 Downloads: {DOWNLOAD_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
