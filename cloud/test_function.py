# -*- coding: utf-8 -*-
"""Quick test for the deployed Cloud Function."""
import json
import os
import sys
import requests

FUNCTION_URL = "https://asia-southeast1-election-ocr.cloudfunctions.net/ocr-worker"
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Load first file from tak drive index
idx_path = os.path.join(DATA_DIR, 'drive_index_tak.json')
with open(idx_path, 'r', encoding='utf-8') as f:
    drive_index = json.load(f)

entry = drive_index[0]
file_id = entry['file_id']
path = entry.get('path', '')
name = entry.get('name', '')
label = f"{path}/{name}" if path else name

print(f"Testing with: {label}")
print(f"File ID: {file_id}")
print(f"URL: {FUNCTION_URL}")
print()

resp = requests.post(FUNCTION_URL, json={
    "file_id": file_id,
    "file_label": label,
    "province": "tak",
    "max_pages": 2,
}, timeout=120)

print(f"Status: {resp.status_code}")
print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
