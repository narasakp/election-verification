# -*- coding: utf-8 -*-
"""
Check sample PDFs to determine:
1. Whether they have embedded text (text layer) or are scanned images
2. Page count, dimensions, image count
3. If text exists, extract sample text
"""
import os
import sys
import json
import fitz  # PyMuPDF

BASE = r'D:\Code\Election69\election-verification\downloads\ss518'
DATA_DIR = r'D:\Code\Election69\election-verification\data'

def find_chaiyaphum():
    for d in os.listdir(BASE):
        if 'ชัยภูมิ' in d:
            return os.path.join(BASE, d)
    return None

def analyze_pdf(filepath):
    """Analyze a single PDF file."""
    result = {
        "file": os.path.basename(filepath),
        "size_bytes": os.path.getsize(filepath),
        "pages": 0,
        "has_text": False,
        "has_images": False,
        "text_sample": "",
        "image_count": 0,
        "page_dimensions": [],
    }
    try:
        doc = fitz.open(filepath)
        result["pages"] = len(doc)
        
        all_text = ""
        total_images = 0
        
        for i, page in enumerate(doc):
            # Get dimensions
            rect = page.rect
            result["page_dimensions"].append({
                "page": i+1,
                "width": round(rect.width, 1),
                "height": round(rect.height, 1),
            })
            
            # Extract text
            text = page.get_text("text")
            if text.strip():
                all_text += f"\n--- PAGE {i+1} ---\n{text}"
            
            # Count images
            images = page.get_images(full=True)
            total_images += len(images)
            
            # Only analyze first 3 pages for speed
            if i >= 2:
                break
        
        result["has_text"] = len(all_text.strip()) > 10
        result["has_images"] = total_images > 0
        result["image_count"] = total_images
        result["text_sample"] = all_text[:2000] if all_text else "(no text found)"
        
        doc.close()
    except Exception as e:
        result["error"] = str(e)
    
    return result

def main():
    prov_dir = find_chaiyaphum()
    if not prov_dir:
        print("Chaiyaphum folder not found!")
        return
    
    print(f"Province dir: {prov_dir}")
    
    # Collect all PDF files
    pdfs = []
    for dp, dn, fn in os.walk(prov_dir):
        for f in fn:
            if f.lower().endswith('.pdf'):
                pdfs.append(os.path.join(dp, f))
    
    print(f"Total PDFs: {len(pdfs)}")
    
    # Sort by size and pick samples: smallest, medium, largest
    pdfs_sorted = sorted(pdfs, key=os.path.getsize)
    
    # Pick diverse samples
    samples = []
    if pdfs_sorted:
        samples.append(pdfs_sorted[0])  # smallest
        samples.append(pdfs_sorted[len(pdfs_sorted)//4])  # 25th percentile
        samples.append(pdfs_sorted[len(pdfs_sorted)//2])  # median
        samples.append(pdfs_sorted[-1])  # largest
    
    # Also pick one "แบ่งเขต" file specifically
    for p in pdfs:
        bname = os.path.basename(p)
        if 'แบ่งเขต' in bname and 'บัญชีรายชื่อ' not in bname and p not in samples:
            samples.append(p)
            break
    
    # And one "บัญชีรายชื่อ" file
    for p in pdfs:
        bname = os.path.basename(p)
        if 'บัญชีรายชื่อ' in bname and 'แบ่งเขต' not in bname and p not in samples:
            samples.append(p)
            break
    
    print(f"\nAnalyzing {len(samples)} sample PDFs...\n")
    
    results = []
    for fp in samples:
        rel = os.path.relpath(fp, prov_dir)
        print(f"{'='*60}")
        print(f"📄 {rel}")
        print(f"   Size: {os.path.getsize(fp):,} bytes")
        
        r = analyze_pdf(fp)
        r["relative_path"] = rel
        results.append(r)
        
        print(f"   Pages: {r['pages']}")
        print(f"   Has text layer: {'✅ YES' if r['has_text'] else '❌ NO (scanned image)'}")
        print(f"   Has images: {r['has_images']} ({r['image_count']} images)")
        if r['page_dimensions']:
            d = r['page_dimensions'][0]
            print(f"   Page size: {d['width']} x {d['height']} pts")
        
        if r['has_text']:
            print(f"\n   📝 Text sample (first 500 chars):")
            for line in r['text_sample'][:500].split('\n'):
                print(f"   | {line}")
        
        print()
    
    # Summary
    has_text_count = sum(1 for r in results if r['has_text'])
    print(f"\n{'='*60}")
    print(f"SUMMARY: {has_text_count}/{len(results)} samples have text layer")
    if has_text_count == 0:
        print("→ All PDFs are scanned images → OCR (Tesseract) required")
    elif has_text_count == len(results):
        print("→ All PDFs have text layer → PyMuPDF text extraction sufficient (no OCR needed!)")
    else:
        print("→ Mixed: some have text, some don't → may need both approaches")
    
    # Save results
    out = os.path.join(DATA_DIR, 'pdf_analysis_samples.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to: {out}")

if __name__ == "__main__":
    main()
