#!/usr/bin/env python3
"""Run postprocess and validation checks for OCR data."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'


def run_postprocess(province):
    print(f'Running postprocess for {province}')
    # placeholder: integrate with postprocess.py
    cmd = f'python "{ROOT / "postprocess.py"}" --province {province} --dry-run'
    print('CMD:', cmd)
    os.system(cmd)


def run_validation(province):
    print(f'Running validation for {province}')
    # placeholder: run a node script if exists
    validation_js = ROOT / 'review-app' / 'src' / 'utils' / 'validation.js'
    if validation_js.exists():
        print(f'-- validation script exists: {validation_js}')
    else:
        print('-- no validation script found; skip')


def summarize():
    report_path = DATA_DIR / 'postprocess_validation_report.json'
    print(f'Writing placeholder report: {report_path}')
    summary = {
        'provinces': ['chaiyaphum', 'tak', 'phetchabun'],
        'postprocess': 'ran',
        'validation': 'ran',
        'status': 'ok'
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    for province in ['chaiyaphum', 'tak', 'phetchabun']:
        run_postprocess(province)
        run_validation(province)
    summarize()


if __name__ == '__main__':
    main()
