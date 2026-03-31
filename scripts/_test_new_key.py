# -*- coding: utf-8 -*-
"""Test the NEW Gemini API key from .env (GEMINI_API_KEY)."""
import os, requests

env = {}
with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

KEY = env.get('GEMINI_API_KEY', '')
print(f"GEMINI_API_KEY: {KEY[:12]}...{KEY[-4:]}")

for model in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite']:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Reply with just: OK"}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 5}
    }
    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            text = resp.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '?')
            print(f"  OK  {model:30s} -> {text.strip()}")
        else:
            msg = resp.json().get('error', {}).get('message', '')[:80]
            print(f"  ERR {model:30s} -> {resp.status_code} | {msg}")
    except Exception as e:
        print(f"  ERR {model:30s} -> {e}")
