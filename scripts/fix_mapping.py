"""Fix province mapping: restore original names, fix truncated, find missing."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ECT_URL = "https://www.ect.go.th/ect_th/th/election-2026"
DATA_DIR = Path(__file__).parent.parent / "data"

# All 77 Thai provinces
ALL_PROVINCES = [
    "กรุงเทพมหานคร", "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร",
    "ขอนแก่น", "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี", "ชัยนาท",
    "ชัยภูมิ", "ชุมพร", "เชียงราย", "เชียงใหม่", "ตรัง",
    "ตราด", "ตาก", "นครนายก", "นครปฐม", "นครพนม",
    "นครราชสีมา", "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", "นราธิวาส",
    "น่าน", "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์",
    "ปราจีนบุรี", "ปัตตานี", "พระนครศรีอยุธยา", "พะเยา", "พังงา",
    "พัทลุง", "พิจิตร", "พิษณุโลก", "เพชรบุรี", "เพชรบูรณ์",
    "แพร่", "ภูเก็ต", "มหาสารคาม", "มุกดาหาร", "แม่ฮ่องสอน",
    "ยโสธร", "ยะลา", "ร้อยเอ็ด", "ระนอง", "ระยอง",
    "ราชบุรี", "ลพบุรี", "ลำปาง", "ลำพูน", "เลย",
    "ศรีสะเกษ", "สกลนคร", "สงขลา", "สตูล", "สมุทรปราการ",
    "สมุทรสงคราม", "สมุทรสาคร", "สระแก้ว", "สระบุรี", "สิงห์บุรี",
    "สุโขทัย", "สุพรรณบุรี", "สุราษฎร์ธานี", "สุรินทร์", "หนองคาย",
    "หนองบัวลำภู", "อ่างทอง", "อำนาจเจริญ", "อุดรธานี", "อุตรดิตถ์",
    "อุทัยธานี", "อุบลราชธานี",
]


def scrape_proper_mapping():
    """Use Playwright to get proper cell-by-cell province→Drive mapping."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"🌐 Loading {ECT_URL} ...")
        page.goto(ECT_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Get each TD cell that has a Drive link, with FULL text content
        cells = page.eval_on_selector_all("td", """
            cells => cells.map((td, idx) => {
                const link = td.querySelector('a[href*="drive.google.com"]');
                if (!link) return null;
                // Get ALL text nodes in this cell (not just textContent which may truncate)
                const allText = [];
                const walker = document.createTreeWalker(td, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const t = walker.currentNode.textContent.trim();
                    if (t) allText.push(t);
                }
                // Also get the row context
                const row = td.closest('tr');
                const rowCells = row ? Array.from(row.querySelectorAll('td')) : [];
                const cellIndex = rowCells.indexOf(td);
                return {
                    cellIndex: cellIndex,
                    allText: allText,
                    fullText: td.innerText.trim(),
                    href: link.href,
                    rowText: row ? row.innerText.trim() : ''
                };
            }).filter(x => x !== null)
        """)

        print(f"📊 Cells with Drive links: {len(cells)}")

        mapping = []
        for cell in cells:
            # Province name: look for Thai text that matches a known province
            province = None
            texts = cell["allText"] + [cell["fullText"]]
            
            for text in texts:
                text = text.strip()
                # Try exact match first
                for prov in ALL_PROVINCES:
                    if prov in text:
                        province = prov
                        break
                if province:
                    break
            
            # If no exact match, try partial match
            if not province:
                for text in texts:
                    text = text.strip()
                    for prov in ALL_PROVINCES:
                        # Check if truncated version matches
                        if len(text) >= 2 and text in prov:
                            province = prov
                            break
                    if province:
                        break

            folder_match = re.search(r'folders/([a-zA-Z0-9_-]+)', cell["href"])
            if folder_match:
                mapping.append({
                    "province": province or f"UNKNOWN ({cell['fullText'][:30]})",
                    "folder_id": folder_match.group(1),
                    "drive_url": cell["href"].split("?")[0].replace("/u/1/", "/").replace("/u/2/", "/").replace("/u/3/", "/").replace("/mobile/", "/"),
                    "raw_text": cell["fullText"][:50],
                })

        browser.close()

        # Deduplicate by folder_id, keeping first occurrence
        seen = set()
        unique = []
        for m in mapping:
            if m["folder_id"] not in seen:
                seen.add(m["folder_id"])
                unique.append(m)

        # Check which provinces are found/missing
        found = {m["province"] for m in unique}
        missing = [p for p in ALL_PROVINCES if p not in found]

        print(f"\n{'='*60}")
        print(f"✅ Found: {len(found)} provinces")
        print(f"❌ Missing: {len(missing)} provinces")
        for p in missing:
            print(f"   - {p}")
        print(f"{'='*60}\n")

        for i, m in enumerate(unique, 1):
            status = "✅" if m["province"] in ALL_PROVINCES else "⚠️"
            print(f"  {i:2d}. {status} {m['province']:25s} → ...{m['folder_id'][-10:]}")

        # Save clean mapping (remove raw_text)
        clean = [{"province": m["province"], "folder_id": m["folder_id"], "drive_url": m["drive_url"]} for m in unique]
        out_path = DATA_DIR / "ect_drive_mapping.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Saved to {out_path}")

        return unique, missing


if __name__ == "__main__":
    scrape_proper_mapping()
