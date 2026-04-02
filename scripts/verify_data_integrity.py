#!/usr/bin/env python3
"""Verify data integrity between drive index and OCR output files."""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_records(prefix):
    data_path = DATA_DIR / prefix
    if not data_path.exists():
        print(f"[WARN] {data_path} not found")
        return {}
    records = {}
    for j in data_path.glob('*.json'):
        obj = load_json(j)
        if isinstance(obj, list):
            for item in obj:
                key = item.get('station_id') or item.get('file_id') or item.get('id')
                if key:
                    records[key] = item
        elif isinstance(obj, dict):
            for key, item in obj.items():
                records[key] = item
    return records


def main():
    print('=== Data integrity check ===')
    # Load all drive index files
    drive_index = {}
    for p in DATA_DIR.glob('drive_index_*.json'):
        data = load_json(p)
        if isinstance(data, list):
            # Convert list to dict using file_id as key
            for item in data:
                key = item.get('file_id')
                if key:
                    drive_index[key] = item
        elif isinstance(data, dict):
            drive_index.update(data)
    ocr_files = list(DATA_DIR.glob('ocr_multimodel_*.json'))
    if not ocr_files:
        print('[ERROR] No OCR files found in data/')
        return

    for ocr_file in ocr_files:
        print(f'-- checking {ocr_file.name}')
        ocr_records = load_json(ocr_file)
        ocr_keys = set()
        if isinstance(ocr_records, list):
            for item in ocr_records:
                if isinstance(item, dict):
                    # Use drive_file_id as the key to match with drive index
                    key = item.get('drive_file_id') or item.get('file_id') or item.get('station_id')
                    if key:
                        ocr_keys.add(key)
        missing = [k for k in ocr_keys if k not in drive_index]
        extra = [k for k in drive_index if k not in ocr_keys]
        print(f'   OCR records: {len(ocr_keys):,}')
        print(f'   drive index records: {len(drive_index):,}')
        print(f'   missing in drive index: {len(missing):,}')
        print(f'   extra in drive index: {len(extra):,}')

    print('=== done ===')


if __name__ == '__main__':
    main()
