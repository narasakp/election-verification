# -*- coding: utf-8 -*-
"""Test if OAuth2 token bypasses per-file download quota."""
import subprocess
import json
import requests

token = subprocess.run(
    ['gcloud', 'auth', 'print-access-token'],
    capture_output=True, text=True, shell=True
).stdout.strip()

idx = json.load(open('data/drive_index_chaiyaphum.json', 'r', encoding='utf-8'))

# Test file[50] which was quota-blocked with API key
fid = idx[50]['file_id']
name = idx[50].get('name', '')
print(f"File: {name}")
print(f"ID:   {fid}")

# Download with OAuth2 token (not API key)
url = f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media"
headers = {'Authorization': f'Bearer {token}'}
r = requests.get(url, headers=headers, timeout=60)
print(f"Status: {r.status_code}")
print(f"Size:   {len(r.content)}")
is_pdf = r.content[:4] == b'%PDF'
print(f"Is PDF: {is_pdf}")

if r.status_code != 200:
    print(f"Error:  {r.text[:200]}")
