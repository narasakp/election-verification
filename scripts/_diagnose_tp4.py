#!/usr/bin/env python3
"""Diagnose the 3 remaining tp=4 items."""
import json, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('review-app/public/data/review_data.json', encoding='utf-8'))
progress = json.load(open('_split_progress.json', encoding='utf-8'))

def get_fid(url):
    if not url or '/d/' not in url:
        return None
    return url.split('/d/')[1].split('/')[0]

# Build lookup
fid_page_to_new = {}
for key, val in progress.items():
    parts = key.rsplit('_', 1)
    if len(parts) == 2:
        try:
            fid_page_to_new[(parts[0], int(parts[1]))] = val['new_fid']
        except (ValueError, KeyError):
            pass

unsplit = [r for r in d if (r.get('total_pages') or 1) > 2]
for item in unsplit:
    fid = get_fid(item.get('pdf_url', ''))
    pg = item.get('page', 1)
    merged = item.get('_merged_pages', [])
    stn = item.get('station_no', '?')
    tp = item.get('total_pages')
    
    # Check what's available in progress for this fid
    avail = sorted([k[1] for k in fid_page_to_new if k[0] == fid]) if fid else []
    
    print(f"stn={stn} pg={pg} tp={tp} merged={merged}")
    print(f"  fid=...{fid[-15:] if fid else 'None'}")
    print(f"  file=...{item.get('file','')[-80:]}")
    print(f"  avail_in_progress={avail}")
    print()
