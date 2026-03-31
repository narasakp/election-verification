# -*- coding: utf-8 -*-
"""Quick test: which Gemini models are currently available?"""
import json, os, requests, base64

# Load API key
env = {}
with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

API_KEY = env.get('GEMINI_API_KEY', '')
if not API_KEY:
    print("ERROR: No GEMINI_API_KEY in .env")
    exit(1)

# Test models
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.5-pro-preview-05-06",
]

# Create a tiny test image (1x1 white PNG)
import struct, zlib
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

print(f"Testing {len(MODELS)} Gemini models...\n")

for model in MODELS:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [
            {"text": "Reply with just the word: OK"},
            {"inline_data": {"mime_type": "image/png", "data": png_b64}}
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 10}
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '?')
            print(f"  ✅ {model:40s} → {resp.status_code} | {text.strip()[:30]}")
        else:
            err = resp.text[:100]
            print(f"  ❌ {model:40s} → {resp.status_code} | {err}")
    except Exception as e:
        print(f"  ❌ {model:40s} → ERROR: {e}")

print("\nDone.")
