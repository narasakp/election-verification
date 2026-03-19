"""Extract Nuxt payload and find actual document links from central ECT page."""
import re
import json
import requests

URL = "https://www.ect.go.th/ect_th/th/election-2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = requests.get(URL, headers=HEADERS, timeout=30)
html = r.text

# Extract __NUXT__ payload
m = re.search(r'window\.__NUXT__\s*=\s*(.+?);\s*</script>', html, re.DOTALL)
if m:
    print("Found Nuxt payload, length:", len(m.group(1)))
    # Save raw payload for inspection
    with open("data/nuxt_payload_raw.txt", "w", encoding="utf-8") as f:
        f.write(m.group(1)[:50000])
    print("Saved first 50K chars to data/nuxt_payload_raw.txt")
else:
    print("No Nuxt payload found")

# Also try the redirect URL pattern
# The page has a link: https://www.ect.go.th/th/election-2026
URL2 = "https://www.ect.go.th/th/election-2026"
r2 = requests.get(URL2, headers=HEADERS, timeout=30)
print(f"\n/th/election-2026 - Size: {len(r2.text):,}, Status: {r2.status_code}")
print(f"Final URL: {r2.url}")

# Search for drive links in this page too
drives2 = re.findall(r'drive\.google\.com/[^\s"\'<>\\]+', r2.text)
print(f"Drive links: {len(drives2)}")
for d in drives2[:5]:
    print(f"  {d}")

# Search for file_download/PDF links
pdfs2 = re.findall(r'file_download/[a-f0-9]+', r2.text)
print(f"file_download refs: {len(pdfs2)}")

# Look for province data in Nuxt payload
m2 = re.search(r'window\.__NUXT__\s*=\s*(.+?);\s*</script>', r2.text, re.DOTALL)
if m2:
    payload = m2.group(1)
    print(f"\nNuxt payload length: {len(payload):,}")
    # Search for province names
    provinces = re.findall(r'[\u0e01-\u0e4f]{3,20}', payload)
    # Search for URLs in payload
    urls = re.findall(r'https?://[^\s"\'\\,\]]+', payload)
    print(f"Thai words in payload: {len(provinces)}")
    print(f"URLs in payload: {len(urls)}")
    
    # Filter for interesting URLs
    for u in urls:
        if any(x in u.lower() for x in ['drive', 'pdf', 'download', 'file_download', 'web-upload/1x']):
            print(f"  Interesting: {u}")
    
    with open("data/nuxt_payload2_raw.txt", "w", encoding="utf-8") as f:
        f.write(payload[:100000])
    print("Saved payload to data/nuxt_payload2_raw.txt")
