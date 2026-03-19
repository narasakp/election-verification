# -*- coding: utf-8 -*-
"""
Collect OCR results from Cloud Storage and merge into local JSON.

Usage:
  python cloud/collect.py --province tak
  python cloud/collect.py --province phetchabun --merge

Downloads all {province}/*.json blobs from the GCS bucket,
merges them into ocr_multimodel_{province}.json locally.
"""
import argparse
import json
import os
import sys

from google.cloud import storage

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

GCS_BUCKET = os.environ.get("GCS_BUCKET", "election69-ocr-results-th")

PROVINCE_SLUGS = {
    "ตาก": "tak", "ชัยภูมิ": "chaiyaphum", "เพชรบูรณ์": "phetchabun",
}


def main():
    parser = argparse.ArgumentParser(description="Collect OCR results from Cloud Storage")
    parser.add_argument("--province", required=True, help="Province (Thai or slug)")
    parser.add_argument("--bucket", default=GCS_BUCKET, help="GCS bucket name")
    parser.add_argument("--merge", action="store_true",
                        help="Merge with existing local results (default: replace)")
    args = parser.parse_args()

    # Resolve province
    slug = PROVINCE_SLUGS.get(args.province) or args.province

    print(f"[Province] {slug}")
    print(f"[Bucket]   gs://{args.bucket}/{slug}/")

    # List and download all blobs
    client = storage.Client()
    bucket = client.bucket(args.bucket)
    blobs = list(bucket.list_blobs(prefix=f"{slug}/"))

    print(f"[Found]    {len(blobs)} result files\n")

    cloud_results = []
    for i, blob in enumerate(blobs):
        if not blob.name.endswith('.json'):
            continue
        data = json.loads(blob.download_as_text())
        if isinstance(data, list):
            cloud_results.extend(data)
        elif isinstance(data, dict):
            cloud_results.append(data)
        if (i + 1) % 100 == 0:
            print(f"  Downloaded {i+1}/{len(blobs)}...")

    print(f"  Total records from cloud: {len(cloud_results)}")

    # Merge with existing local results
    out_path = os.path.join(DATA_DIR, f'ocr_multimodel_{slug}.json')
    existing = []
    if args.merge and os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        print(f"  Existing local records: {len(existing)}")

    # Deduplicate by (file, page)
    seen = set()
    merged = []
    for r in existing:
        key = (r.get('file', ''), r.get('page', 0))
        if key not in seen:
            seen.add(key)
            merged.append(r)
    for r in cloud_results:
        key = (r.get('file', ''), r.get('page', 0))
        if key not in seen:
            seen.add(key)
            merged.append(r)

    # Save
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    unique_files = len(set(r.get('file') for r in merged))
    print(f"\n{'='*50}")
    print(f"  Saved: {len(merged)} records ({unique_files} files)")
    print(f"  Output: {out_path}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
