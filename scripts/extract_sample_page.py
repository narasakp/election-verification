# -*- coding: utf-8 -*-
"""
Extract sample pages from PDF as images for visual inspection.
Uses PyMuPDF to render PDF pages to PNG.
"""
import os
import fitz  # PyMuPDF

BASE = r'D:\Code\Election69\election-verification\downloads\ss518'
OUT_DIR = r'D:\Code\Election69\election-verification\data\sample_pages'

def find_chaiyaphum():
    for d in os.listdir(BASE):
        if 'ชัยภูมิ' in d:
            return os.path.join(BASE, d)
    return None

def extract_page_as_image(pdf_path, page_num=0, dpi=200):
    """Extract a single page from PDF as PNG image."""
    # Read as bytes first to avoid Unicode path issues on Windows
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    if page_num >= total:
        page_num = 0
    page = doc[page_num]
    # Render at specified DPI
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes, total

def main():
    prov_dir = find_chaiyaphum()
    if not prov_dir:
        print("Chaiyaphum not found!")
        return
    
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Find specific file types to sample
    targets = {}
    for dp, dn, fn in os.walk(prov_dir):
        for f in fn:
            if not f.lower().endswith('.pdf'):
                continue
            fp = os.path.join(dp, f)
            size = os.path.getsize(fp)
            rel = os.path.relpath(fp, prov_dir)
            
            # Categorize
            fname = f.lower()
            if 'แบ่งเขต' in f and 'บัญชีรายชื่อ' not in f and 'นอกเขต' not in f:
                key = "แบ่งเขต_รายหน่วย"
            elif 'บัญชีรายชื่อ' in f and 'แบ่งเขต' not in f and 'นอกเขต' not in f:
                key = "บัญชีรายชื่อ_รายหน่วย"
            elif '5_16' in f or '5/16' in f:
                key = "สส5_16"
            elif '5_17' in f or '5/17' in f:
                key = "สส5_17"
            elif 'นอกเขต' in f:
                key = "นอกเขต"
            else:
                key = "อื่นๆ"
            
            # Pick smallest file per category (faster to process)
            if key not in targets or size < targets[key][1]:
                targets[key] = (fp, size, rel)
    
    print(f"Found {len(targets)} categories of PDFs:\n")
    
    for category, (fp, size, rel) in sorted(targets.items()):
        print(f"{'='*60}")
        print(f"📄 [{category}] {rel}")
        print(f"   Size: {size:,} bytes")
        
        try:
            # Extract first 2 pages
            for pg in range(2):
                img_bytes, total_pages = extract_page_as_image(fp, page_num=pg, dpi=150)
                if pg == 0:
                    print(f"   Total pages: {total_pages}")
                
                safe_name = category.replace('/', '_') + f"_page{pg+1}.png"
                out_path = os.path.join(OUT_DIR, safe_name)
                with open(out_path, 'wb') as f:
                    f.write(img_bytes)
                print(f"   ✅ Saved: {safe_name} ({len(img_bytes):,} bytes)")
                
                if pg + 1 >= total_pages:
                    break
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print(f"\n📁 Sample images saved to: {OUT_DIR}")
    print(f"   Total files: {len(os.listdir(OUT_DIR))}")

if __name__ == "__main__":
    main()
