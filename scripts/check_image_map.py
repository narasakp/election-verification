# Quick check: does the server image mapping work?
import re, os, json

DEBUG = 'data/ocr_debug_vision'
pngs = set(f for f in os.listdir(DEBUG) if f.endswith('.png'))
data = json.load(open('data/ocr_vision_chaiyaphum.json', 'r', encoding='utf-8'))

matched = 0
missed = []
for i in data:
    base = os.path.basename(i['file'])
    sanitized = re.sub(r'[^\w.-]', '_', base)
    target = f"{sanitized}_p{i['page']}.png"
    if target in pngs:
        matched += 1
    else:
        missed.append((base, target))

print(f"Matched: {matched}/{len(data)}")
print(f"Missed: {len(missed)}")
for b, t in missed[:5]:
    print(f"  orig: {b}")
    print(f"  target: {t}")
    # Show closest PNG
    for p in sorted(pngs):
        if b[:5] in p or t[:10] in p:
            print(f"  close: {p}")
            break
print()
print("Sample PNGs:", sorted(pngs)[:3])
