"""Analyze central ECT page to find correct PDF/Drive sources."""
import re
import requests

URL = "https://www.ect.go.th/ect_th/th/election-2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = requests.get(URL, headers=HEADERS, timeout=30)
html = r.text
print(f"Page size: {len(html):,} bytes")
print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")

# Search for Google Drive links
drives = re.findall(r'https?://drive\.google\.com/[^\s"\'<>]+', html)
print(f"\nGoogle Drive links: {len(drives)}")
for d in drives[:20]:
    print(f"  {d}")

# Search for PDF links
pdfs = re.findall(r'https?://[^\s"\'<>]*\.pdf[^\s"\'<>]*', html, re.IGNORECASE)
print(f"\nDirect PDF links: {len(pdfs)}")
for p in pdfs[:10]:
    print(f"  {p}")

# Search for file_download links
downloads = re.findall(r'https?://[^\s"\'<>]*file_download[^\s"\'<>]*', html, re.IGNORECASE)
print(f"\nfile_download links: {len(downloads)}")
for d in downloads[:10]:
    print(f"  {d}")

# Search for web-upload links
uploads = re.findall(r'/web-upload/[^\s"\'<>]+', html)
print(f"\nweb-upload paths: {len(uploads)}")
for u in uploads[:10]:
    print(f"  {u}")

# Search for any JSON data embedded (Nuxt SPA)
json_matches = re.findall(r'window\.__NUXT__\s*=\s*', html)
print(f"\nNuxt data blocks: {len(json_matches)}")

# Search for API endpoints
apis = re.findall(r'https?://[^\s"\'<>]*api[^\s"\'<>]*', html, re.IGNORECASE)
print(f"\nAPI endpoints: {len(apis)}")
for a in set(apis)[:10]:
    print(f"  {a}")

# Look for folder IDs in Drive links or any data
folder_ids = re.findall(r'folders/([a-zA-Z0-9_-]{20,})', html)
print(f"\nDrive folder IDs: {len(folder_ids)}")
for fid in set(folder_ids)[:10]:
    print(f"  {fid}")

# Look for any province-related data
# Search for Thai province keywords
provinces_found = []
for prov in ["กรุงเทพ", "เชียงใหม่", "ขอนแก่น", "นครราชสีมา", "แม่ฮ่องสอน", "บุรีรัมย์"]:
    if prov in html:
        provinces_found.append(prov)
print(f"\nProvince names found in HTML: {provinces_found}")

# Check for Nuxt payload / script data
scripts = re.findall(r'<script[^>]*src="([^"]*)"', html)
print(f"\nScript sources: {len(scripts)}")
for s in scripts[:5]:
    print(f"  {s}")
