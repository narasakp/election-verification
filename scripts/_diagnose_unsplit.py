#!/usr/bin/env python3
"""Diagnose why 351 items didn't get split PDF URLs."""
import json, sys
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))
progress = json.load(open('_split_progress.json', encoding='utf-8'))

# Build lookup from progress
fid_page_to_new = {}
for key, val in progress.items():
    parts = key.rsplit('_', 1)
    if len(parts) == 2:
        orig_fid, page_str = parts
        try:
            fid_page_to_new[(orig_fid, int(page_str))] = val['new_fid']
        except (ValueError, KeyError):
            pass

def get_fid(url):
    if not url or '/d/' not in url:
        return None
    return url.split('/d/')[1].split('/')[0]

# Check unsplit items
unsplit = [r for r in d if (r.get('total_pages') or 1) > 2]
reasons = Counter()

for item in unsplit:
    fid = get_fid(item.get('pdf_url', ''))
    pg = item.get('page', 1)
    merged = item.get('_merged_pages', [])
    
    if not fid:
        reasons['no_fid'] += 1
        continue
    
    # Check if any page in progress
    all_pages = [pg] + [p for p in merged if p != pg]
    has_any = any((fid, p) in fid_page_to_new for p in all_pages)
    
    if has_any:
        reasons['has_match_but_missed'] += 1
    else:
        # Check if fid exists at all in progress
        fid_in_progress = any(k[0] == fid for k in fid_page_to_new)
        if fid_in_progress:
            # fid exists but not for these pages
            available = sorted([k[1] for k in fid_page_to_new if k[0] == fid])
            reasons['fid_ok_page_mismatch'] += 1
        else:
            reasons['fid_not_in_progress'] += 1

print(f"Unsplit items: {len(unsplit)}")
print(f"Reasons:")
for r, c in reasons.most_common():
    print(f"  {r}: {c}")

# Show samples for each reason
print("\n--- Samples: fid_not_in_progress ---")
cnt = 0
for item in unsplit:
    fid = get_fid(item.get('pdf_url', ''))
    if not fid:
        continue
    if not any(k[0] == fid for k in fid_page_to_new):
        if cnt < 3:
            print(f"  fid={fid[:20]}... pg={item.get('page')} tp={item.get('total_pages')} file=...{item.get('file','')[-50:]}")
            cnt += 1

print("\n--- Samples: fid_ok_page_mismatch ---")
cnt = 0
for item in unsplit:
    fid = get_fid(item.get('pdf_url', ''))
    if not fid:
        continue
    fid_in = any(k[0] == fid for k in fid_page_to_new)
    if not fid_in:
        continue
    pg = item.get('page', 1)
    merged = item.get('_merged_pages', [])
    all_pages = [pg] + [p for p in merged if p != pg]
    if not any((fid, p) in fid_page_to_new for p in all_pages):
        available = sorted([k[1] for k in fid_page_to_new if k[0] == fid])
        if cnt < 5:
            print(f"  fid=...{fid[-15:]} pg={pg} merged={merged[:5]} available={available[:10]}... tp={item.get('total_pages')}")
            cnt += 1
