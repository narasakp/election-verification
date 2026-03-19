# -*- coding: utf-8 -*-
import os, fitz

base = os.path.join(os.path.dirname(__file__), '..', 'downloads', 'ss518')
prov = [d for d in os.listdir(base) if 'ชัยภูมิ' in d][0]
root = os.path.join(base, prov)

pdfs = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.lower().endswith('.pdf'):
            pdfs.append(os.path.join(dp, f))

ss518 = [f for f in pdfs if '5_16' not in os.path.basename(f) and '5_17' not in os.path.basename(f)]

print(f"Total PDF files: {len(pdfs)}")
print(f"สส.5/18 files: {len(ss518)}")

# Sample page counts
total_pages = 0
for f in ss518[:20]:
    with open(f, "rb") as fh:
        doc = fitz.open(stream=fh.read(), filetype="pdf")
        total_pages += len(doc)
        doc.close()

avg = total_pages / min(20, len(ss518))
est = int(len(ss518) * avg)
print(f"Avg pages/file (sample 20): {avg:.1f}")
print(f"Est total pages: {est}")
print(f"Est API calls (max 2 pages/file): ~{len(ss518) * 2}")
print(f"Free tier: 1000/month, cost after: $1.50/1000")
print(f"Est cost: ~${max(0, len(ss518)*2 - 1000) * 0.0015:.2f}")
