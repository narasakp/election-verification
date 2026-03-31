# -*- coding: utf-8 -*-
"""Test GOOGLE_CLOUD_API_KEY with Gemini models."""
import json, os, requests, base64, struct, zlib

env = {}
with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

API_KEY = env.get('GOOGLE_CLOUD_API_KEY', '')
print(f"Key: {API_KEY[:12]}...{API_KEY[-4:]}")

# Tiny test PNG
def make_tiny_png():
    raw = b'\x00\xff\xff\xff'
    compressed = zlib.compress(raw)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', compressed) +
            chunk(b'IEND', b''))

png_b64 = base64.b64encode(make_tiny_png()).decode()

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

for model in MODELS:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [
            {"text": "Reply with just: OK"},
            {"inline_data": {"mime_type": "image/png", "data": png_b64}}
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 10}
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '?')
            print(f"  OK  {model:35s} -> {text.strip()[:30]}")
        else:
            err = resp.json().get('error', {}).get('message', resp.text[:80])
            print(f"  ERR {model:35s} -> {resp.status_code} | {err[:80]}")
    except Exception as e:
        print(f"  ERR {model:35s} -> {e}")
