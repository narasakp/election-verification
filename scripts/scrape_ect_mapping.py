"""
Extract province → Google Drive folder mapping from ECT central page.
Uses Playwright to render the SPA and extract the table data.
"""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ECT_URL = "https://www.ect.go.th/ect_th/th/election-2026"
DATA_DIR = Path(__file__).parent.parent / "data"


def scrape_province_mapping():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"🌐 Loading {ECT_URL} ...")
        page.goto(ECT_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        print(f"✅ Page loaded")

        # Find all table rows that contain Drive links
        # The table has class 'table-download'
        rows = page.eval_on_selector_all("table.table-download tr, table tr", """
            rows => rows.map(row => {
                const cells = Array.from(row.querySelectorAll('td, th'));
                const links = Array.from(row.querySelectorAll('a[href*="drive.google.com"]'));
                return {
                    cells: cells.map(c => c.textContent.trim().substring(0, 100)),
                    driveLinks: links.map(a => ({
                        href: a.href,
                        text: a.textContent.trim(),
                        parentText: a.closest('td') ? a.closest('td').textContent.trim().substring(0, 100) : ''
                    }))
                };
            })
        """)

        print(f"\n📊 Table rows found: {len(rows)}")

        # Show first few rows to understand structure
        for i, row in enumerate(rows[:5]):
            print(f"\nRow {i}: cells={len(row['cells'])}")
            for j, cell in enumerate(row['cells']):
                print(f"  Cell {j}: {cell[:80]}")
            if row['driveLinks']:
                for dl in row['driveLinks']:
                    print(f"  Drive: {dl['href'][:80]}")

        # Now extract the mapping: find rows with province names and Drive links
        mapping = []
        for row in rows:
            if not row['driveLinks']:
                continue
            # Province name is usually in the first or second cell
            province_name = ""
            for cell in row['cells']:
                # Look for Thai text that could be a province name
                if re.search(r'[\u0e01-\u0e4f]{2,}', cell) and len(cell) < 50:
                    province_name = cell.strip()
                    break

            for dl in row['driveLinks']:
                folder_match = re.search(r'folders/([a-zA-Z0-9_-]+)', dl['href'])
                if folder_match:
                    mapping.append({
                        "province": province_name or dl.get('parentText', ''),
                        "folder_id": folder_match.group(1),
                        "drive_url": dl['href'].split('?')[0],
                        "link_text": dl['text']
                    })

        print(f"\n\n{'='*60}")
        print(f"📋 Province → Drive mapping: {len(mapping)} entries")
        print(f"{'='*60}")
        for m in mapping:
            print(f"  {m['province']:30s} → {m['folder_id'][:20]}...")

        # Also try a broader approach: get ALL elements near Drive links
        near_drive = page.eval_on_selector_all("a[href*='drive.google.com']", """
            links => links.map(a => {
                // Walk up to find the nearest row or container
                let row = a.closest('tr');
                let rowText = row ? row.textContent.trim() : '';
                // Get sibling/parent text
                let parent = a.parentElement;
                let parentText = parent ? parent.textContent.trim() : '';
                // Get previous sibling text
                let prev = a.closest('td');
                let prevSibling = prev ? prev.previousElementSibling : null;
                let prevText = prevSibling ? prevSibling.textContent.trim() : '';
                // Two cells before
                let prev2 = prevSibling ? prevSibling.previousElementSibling : null;
                let prev2Text = prev2 ? prev2.textContent.trim() : '';
                return {
                    href: a.href,
                    rowText: rowText.substring(0, 200),
                    parentText: parentText.substring(0, 100),
                    prevCellText: prevText.substring(0, 100),
                    prev2CellText: prev2Text.substring(0, 100)
                };
            })
        """)

        print(f"\n\n{'='*60}")
        print(f"📋 Context around Drive links: {len(near_drive)}")
        print(f"{'='*60}")
        for nd in near_drive[:10]:
            print(f"\n  Drive: {nd['href'][:60]}")
            print(f"  Row: {nd['rowText'][:150]}")
            print(f"  Prev cell: {nd['prevCellText'][:80]}")
            print(f"  Prev2 cell: {nd['prev2CellText'][:80]}")

        # Save mapping
        out = {
            "mapping": mapping,
            "context": near_drive,
        }
        out_path = DATA_DIR / "ect_province_drive_mapping.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to {out_path}")

        browser.close()
        return out


if __name__ == "__main__":
    scrape_province_mapping()
