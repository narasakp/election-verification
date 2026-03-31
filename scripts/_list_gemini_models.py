# -*- coding: utf-8 -*-
"""List available Gemini models that support vision."""
import os, requests

env = {}
with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

KEY = env.get('GEMINI_API_KEY', '')
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={KEY}"
resp = requests.get(url, timeout=20)
models = resp.json().get('models', [])

print(f"Total models: {len(models)}\n")
print("Vision-capable models (generateContent + image input):")
for m in models:
    name = m.get('name', '').replace('models/', '')
    methods = m.get('supportedGenerationMethods', [])
    if 'generateContent' in methods and 'vision' in str(m).lower() or 'flash' in name or 'pro' in name:
        print(f"  {name}")
