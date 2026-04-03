#!/usr/bin/env python3
"""Check if the remaining unsplit file IDs are still accessible on Google Drive."""
import json, sys, os
from collections import Counter
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load API key
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
api_key = None
if os.path.exists(env_path):
    for line in open(env_path):
        if line.strip().startswith('GOOGLE_CLOUD_API_KEY='):
            api_key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))

def get_fid(url):
    if not url or '/d/' not in url:
        return None
    return url.split('/d/')[1].split('/')[0]

unsplit = [r for r in d if (r.get('total_pages') or 1) > 2]
print(f"Unsplit items: {len(unsplit)}")

# Get unique fids
fids = set()
for item in unsplit:
    fid = get_fid(item.get('pdf_url', ''))
    if fid:
        fids.add(fid)

print(f"Unique file IDs: {len(fids)}")

for fid in sorted(fids):
    # Try metadata endpoint
    url = f"https://www.googleapis.com/drive/v3/files/{fid}?fields=id,name,size,trashed&key={api_key}"
    resp = requests.get(url, timeout=30)
    
    # Find matching items
    items = [r for r in unsplit if get_fid(r.get('pdf_url', '')) == fid]
    files = set(r.get('file', '?')[-60:] for r in items)
    
    if resp.status_code == 200:
        meta = resp.json()
        print(f"  OK fid=...{fid[-12:]} name={meta.get('name','?')} size={meta.get('size','?')} trashed={meta.get('trashed',False)}")
    else:
        print(f"  FAIL fid=...{fid[-12:]} HTTP {resp.status_code}: {resp.text[:100]}")
    
    for f in files:
        print(f"    -> ...{f}")
