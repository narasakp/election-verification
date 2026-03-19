#!/usr/bin/env python3
"""
Retry failed downloads from ss518_index.json.
Uses the rebuilt index (which has PDF URLs) and scans disk to find missing files.
"""
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from download_ss518 import download_file, safe_filename, DOWNLOAD_DIR

DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
INDEX_PATH = os.path.join(DATA_DIR, "ss518_index.json")


def main():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        idx = json.load(f)

    total_retry = 0
    total_success = 0
    total_still_failed = 0
    total_already_ok = 0
    failure_stats = []

    for prov in idx["provinces"]:
        slug = prov["slug"]
        pdf_urls = prov.get("pdfs", [])

        if not pdf_urls:
            continue

        prov_dir = os.path.join(DOWNLOAD_DIR, slug)
        os.makedirs(prov_dir, exist_ok=True)

        # Find which files are missing on disk
        missing = []
        ok = 0
        for url in pdf_urls:
            fname = safe_filename(url)
            dest = os.path.join(prov_dir, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                ok += 1
            else:
                missing.append((url, fname, dest))

        total_already_ok += ok

        if not missing:
            continue

        print(f"\n{'='*50}")
        print(f"\U0001f4cd {slug}: {len(missing)} missing, {ok} already ok")
        prov_success = 0
        prov_failed = 0

        for i, (url, fname, dest) in enumerate(missing):
            status = download_file(url, dest)
            total_retry += 1
            if status == "downloaded":
                total_success += 1
                prov_success += 1
                size = os.path.getsize(dest)
                print(f"  \u2705 [{i+1}/{len(missing)}] {fname} ({size:,} bytes)")
            else:
                total_still_failed += 1
                prov_failed += 1
                print(f"  \u274c [{i+1}/{len(missing)}] {status} - {fname}")
            time.sleep(0.5)

        failure_stats.append({
            "slug": slug,
            "retried": len(missing),
            "success": prov_success,
            "still_failed": prov_failed,
        })
        print(f"  \U0001f4ca {slug}: {prov_success}/{len(missing)} recovered")

    # Summary
    print(f"\n{'='*60}")
    print(f" Retry Summary")
    print(f"{'='*60}")
    print(f"  Already on disk: {total_already_ok}")
    print(f"  Total retried: {total_retry}")
    print(f"  Recovered: {total_success}")
    print(f"  Still failed: {total_still_failed}")
    if failure_stats:
        print(f"\n  Per-province failures:")
        for fs in sorted(failure_stats, key=lambda x: -x["still_failed"]):
            if fs["still_failed"] > 0:
                print(f"    {fs['slug']:30s} still_failed={fs['still_failed']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
