# -*- coding: utf-8 -*-
"""Batch test improved parser v2 against all available OCR debug text files."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from ocr_cloud_vision import parse_ss518_text

sys.stdout.reconfigure(encoding='utf-8')

DEBUG_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'ocr_debug_vision')

# Find all vision txt files
txt_files = sorted(glob.glob(os.path.join(DEBUG_DIR, '*_vision.txt')))
print(f"Found {len(txt_files)} OCR text files\n")

stat_fields = ["registered_voters", "turnout", "ballots_received", "valid_ballots",
               "invalid_ballots", "no_vote_ballots", "remaining_ballots"]

total_fields = 0
filled_fields = 0
high_conf = 0
low_conf = 0
files_with_candidates = 0

for tf in txt_files:
    fname = os.path.basename(tf)
    with open(tf, 'r', encoding='utf-8') as f:
        raw = f.read()
    if len(raw) < 50:
        continue

    result = parse_ss518_text(raw)
    conf = result.get("_confidence", {})
    cands = result.get("candidates", [])

    n_filled = sum(1 for sf in stat_fields if result.get(sf) is not None)
    n_high = sum(1 for sf in stat_fields if conf.get(sf, "") == "high")
    n_low = sum(1 for sf in stat_fields if conf.get(sf, "").startswith("low"))

    total_fields += len(stat_fields)
    filled_fields += n_filled
    high_conf += n_high
    low_conf += n_low
    if cands:
        files_with_candidates += 1

    # Print summary per file
    vals = []
    for sf in stat_fields:
        v = result.get(sf)
        c = conf.get(sf, "?")
        tag = ""
        if c == "high":
            tag = "✅"
        elif c.startswith("low"):
            tag = "⚠️"
        elif v is not None:
            tag = "📊"
        else:
            tag = "❌"
        vals.append(f"{sf[:8]}={v}{tag}")
    print(f"--- {fname[:60]} ---")
    print(f"  type={result.get('ocr_vote_type')} prov={result.get('ocr_province')} "
          f"stn={result.get('ocr_station_no')} cands={len(cands)}")
    print(f"  {' | '.join(vals[:4])}")
    print(f"  {' | '.join(vals[4:])}")
    if n_low > 0:
        for sf in stat_fields:
            c = conf.get(sf, "")
            if c.startswith("low"):
                print(f"  ⚠️ {sf}: {c}")
    print()

print("=" * 60)
print(f"SUMMARY: {len(txt_files)} files")
print(f"  Fields filled: {filled_fields}/{total_fields} ({100*filled_fields//total_fields if total_fields else 0}%)")
print(f"  High confidence: {high_conf}")
print(f"  Low confidence (digit≠thai): {low_conf}")
print(f"  Files with candidates: {files_with_candidates}/{len(txt_files)}")
