"""
Scrape the central ECT election-2026 page using Playwright (headless browser)
to extract province links and Google Drive folder URLs.
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ECT_URL = "https://www.ect.go.th/ect_th/th/election-2026"
DATA_DIR = Path(__file__).parent.parent / "data"


def scrape_ect_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"🌐 Loading {ECT_URL} ...")
        page.goto(ECT_URL, wait_until="networkidle", timeout=60000)
        print(f"✅ Page loaded, title: {page.title()}")

        # Wait for content to render
        page.wait_for_timeout(3000)

        # Get all links on the page
        links = page.eval_on_selector_all("a[href]", """
            elements => elements.map(el => ({
                href: el.href,
                text: (el.textContent || '').trim().substring(0, 100),
                title: el.title || ''
            }))
        """)
        print(f"\n📎 Total links found: {len(links)}")

        # Categorize links
        drive_links = []
        province_links = []
        pdf_links = []
        file_download_links = []

        for link in links:
            href = link["href"]
            text = link["text"]

            if "drive.google.com" in href:
                drive_links.append(link)
            elif "file_download" in href:
                file_download_links.append(link)
            elif href.lower().endswith(".pdf"):
                pdf_links.append(link)
            elif re.search(r'/election-2026', href) and href != ECT_URL:
                province_links.append(link)

        print(f"\n🔗 Google Drive links: {len(drive_links)}")
        for d in drive_links:
            print(f"  {d['text'][:50]} → {d['href']}")

        print(f"\n📄 PDF links: {len(pdf_links)}")
        for p_link in pdf_links[:10]:
            print(f"  {p_link['text'][:50]} → {p_link['href'][:100]}")

        print(f"\n📥 file_download links: {len(file_download_links)}")
        for f in file_download_links[:10]:
            print(f"  {f['text'][:50]} → {f['href'][:100]}")

        print(f"\n🏛️ Province/election links: {len(province_links)}")
        for pl in province_links[:20]:
            print(f"  {pl['text'][:50]} → {pl['href'][:100]}")

        # Also get the full rendered HTML and search for Drive folder IDs
        html = page.content()
        print(f"\n📝 Rendered HTML size: {len(html):,} bytes")

        folder_ids = re.findall(r'folders/([a-zA-Z0-9_-]{20,})', html)
        if folder_ids:
            print(f"\n📁 Drive folder IDs in HTML: {len(set(folder_ids))}")
            for fid in set(folder_ids):
                print(f"  https://drive.google.com/drive/folders/{fid}")

        # Try clicking on province sections or document categories
        # Look for clickable elements that might expand content
        buttons = page.query_selector_all("button, [role='button'], .accordion, .collapse-trigger, [data-toggle]")
        print(f"\n🔘 Clickable elements: {len(buttons)}")

        # Try to find document/media sections
        sections = page.eval_on_selector_all("[class*='document'], [class*='media'], [class*='file'], [class*='download']", """
            elements => elements.map(el => ({
                tag: el.tagName,
                class: el.className,
                text: (el.textContent || '').trim().substring(0, 200)
            }))
        """)
        print(f"\n📦 Document/media sections: {len(sections)}")
        for s in sections[:5]:
            print(f"  <{s['tag']} class='{s['class'][:60]}'> {s['text'][:100]}")

        # Save all data
        result = {
            "url": ECT_URL,
            "html_size": len(html),
            "total_links": len(links),
            "drive_links": drive_links,
            "pdf_links": pdf_links,
            "file_download_links": file_download_links,
            "province_links": province_links,
            "folder_ids": list(set(folder_ids)),
            "all_links": links,
        }

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DATA_DIR / "ect_central_links.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to {out_path}")

        # Also save rendered HTML for manual inspection
        html_path = DATA_DIR / "ect_central_rendered.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 Rendered HTML saved to {html_path}")

        browser.close()
        return result


if __name__ == "__main__":
    scrape_ect_page()
