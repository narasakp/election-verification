"""
Extract province → Google Drive folder mapping from ECT central page.
Each table cell contains one province name + one Drive link.
"""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ECT_URL = "https://www.ect.go.th/ect_th/th/election-2026"
DATA_DIR = Path(__file__).parent.parent / "data"


def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"🌐 Loading {ECT_URL} ...")
        page.goto(ECT_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        print(f"✅ Page loaded")

        # Each <td> cell contains one province name + one Drive link
        cells = page.eval_on_selector_all("td", """
            cells => cells.filter(td => {
                return td.querySelector('a[href*="drive.google.com"]');
            }).map(td => {
                const link = td.querySelector('a[href*="drive.google.com"]');
                const text = td.textContent.trim();
                return {
                    text: text,
                    href: link.href
                };
            })
        """)

        print(f"📊 Cells with Drive links: {len(cells)}")

        mapping = []
        for cell in cells:
            # Extract province name (Thai text before the link)
            text = cell["text"].strip()
            # Province name is usually the first line
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            province_name = lines[0] if lines else text[:30]
            
            # Extract folder ID
            folder_match = re.search(r'folders/([a-zA-Z0-9_-]+)', cell["href"])
            if folder_match:
                mapping.append({
                    "province": province_name,
                    "folder_id": folder_match.group(1),
                    "drive_url": cell["href"].split("?")[0],
                })

        # Deduplicate by folder_id
        seen = set()
        unique = []
        for m in mapping:
            if m["folder_id"] not in seen:
                seen.add(m["folder_id"])
                unique.append(m)

        print(f"\n{'='*60}")
        print(f"📋 จังหวัด → Google Drive: {len(unique)} รายการ")
        print(f"{'='*60}")
        for i, m in enumerate(unique, 1):
            print(f"  {i:2d}. {m['province']:25s} → {m['drive_url']}")

        # Save
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DATA_DIR / "ect_drive_mapping.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to {out_path}")

        browser.close()
        return unique


if __name__ == "__main__":
    scrape()
