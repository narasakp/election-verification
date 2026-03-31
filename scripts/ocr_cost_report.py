#!/usr/bin/env python3
"""Generate OCR cost and performance metrics report."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
data_dir = root / 'data'

# Manual baseline values (from log)
MODEL_COST_PER_PAGE = 0.0011

provinces = [
    {'name': 'chaiyaphum', 'pages': 5595},
    {'name': 'tak', 'pages': 2335},
    {'name': 'phetchabun', 'pages': 6362},
]

report = {
    'total_pages': sum(p['pages'] for p in provinces),
    'estimated_cost': sum(p['pages'] for p in provinces) * MODEL_COST_PER_PAGE,
    'model_cost_per_page': MODEL_COST_PER_PAGE,
    'details': []
}

for p in provinces:
    p_cost = p['pages'] * MODEL_COST_PER_PAGE
    report['details'].append({
        'province': p['name'],
        'pages': p['pages'],
        'estimated_cost': round(p_cost, 4),
        'completion': round(p['pages'] / 15000 * 100, 2)  # placeholder
    })

output_file = data_dir / 'ocr_cost_report.json'
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print('Wrote', output_file)
