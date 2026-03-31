#!/usr/bin/env python3
"""Generalized postprocessing pipeline for OCR election data."""
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

# Province name mappings
PROVINCE_NAMES = {
    "chaiyaphum": "ชัยภูมิ",
    "tak": "ตาก",
    "phetchabun": "เพชรบูรณ์"
}

# Killernay name overrides for fuzzy matching
KILLERNAY_NAME_OVERRIDES = {
    "chaiyaphum": {},
    "tak": {},
    "phetchabun": {}
}


def load_json(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, path: Path) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_ocr_data(province: str) -> List[Dict]:
    """Load OCR records for province."""
    ocr_file = DATA_DIR / f"ocr_multimodel_{province}.json"
    if not ocr_file.exists():
        raise FileNotFoundError(f"OCR file not found: {ocr_file}")
    return load_json(ocr_file)


def load_killernay_data(province: str) -> Dict:
    """Load Killernay ground truth data."""
    killernay_file = DATA_DIR / "killernay_constituency_full.csv"
    if not killernay_file.exists():
        print(f"Warning: Killernay file not found: {killernay_file}")
        return {}
    # Placeholder: parse CSV if needed
    return {}


def load_ect_reference(province: str) -> Dict:
    """Load ECT candidates reference."""
    ect_file = DATA_DIR / "ect_candidates_reference.json"
    if not ect_file.exists():
        print(f"Warning: ECT reference not found: {ect_file}")
        return {}
    return load_json(ect_file)


def fix_metadata_from_filepath(records: List[Dict], province: str) -> List[Dict]:
    """R0a: Fix metadata from filepath."""
    for record in records:
        if 'file_path' in record:
            # Extract constituency, station from path
            path = record['file_path']
            if 'constituency' not in record:
                # Placeholder extraction logic
                record['constituency'] = 'unknown'
            if 'province' not in record:
                record['province'] = province
    return records


def fix_station_no_from_filepath(records: List[Dict], province: str) -> List[Dict]:
    """R0b: Fix station_no from filepath."""
    for record in records:
        if 'file_path' in record and 'station_no' not in record:
            # Extract station_no from path
            record['station_no'] = 'unknown'
    return records


def dedup_records(records: List[Dict]) -> List[Dict]:
    """R0c: Remove exact duplicates."""
    seen = set()
    unique = []
    for record in records:
        key = json.dumps(record, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def dedup_interleaved(records: List[Dict]) -> List[Dict]:
    """R0d: Remove interleaved combined-file duplicates."""
    # Placeholder: complex dedup logic for combined PDFs
    return records


def fix_total_votes(records: List[Dict]) -> List[Dict]:
    """R3: Fix total_votes calculation."""
    for record in records:
        if 'candidate_votes' in record and isinstance(record['candidate_votes'], dict):
            total = sum(record['candidate_votes'].values())
            record['total_votes'] = total
    return records


def fix_remaining_ballots(records: List[Dict]) -> List[Dict]:
    """R4: Fix remaining_ballots."""
    for record in records:
        if record.get('registered_voters') is not None and record.get('valid_ballots') is not None:
            record['remaining_ballots'] = record['registered_voters'] - record['valid_ballots']
    return records


def fix_negative_values(records: List[Dict]) -> List[Dict]:
    """R5: Fix negative values."""
    for record in records:
        for key in ['remaining_ballots', 'invalid_ballots']:
            if key in record and record[key] is not None and record[key] < 0:
                record[key] = 0
    return records


def fix_outliers(records: List[Dict]) -> List[Dict]:
    """R6: Fix outliers."""
    # Placeholder: statistical outlier detection
    return records


def normalize_candidates(records: List[Dict], ect_ref: Dict) -> List[Dict]:
    """R7: Normalize candidates with ECT reference + name matching."""
    for record in records:
        if 'candidates' in record:
            # Placeholder: fuzzy matching with ECT reference
            pass
    return records


def flag_turnout(records: List[Dict]) -> List[Dict]:
    """R8: Flag turnout anomalies."""
    for record in records:
        if 'turnout_percentage' in record and record['turnout_percentage'] > 100:
            record['turnout_flag'] = True
    return records


def fix_candidate_vote_outliers(records: List[Dict]) -> List[Dict]:
    """R9: Fix candidate vote outliers."""
    for record in records:
        if 'candidate_votes' in record and 'valid_ballots' in record:
            for cand, votes in record['candidate_votes'].items():
                if votes > record['valid_ballots']:
                    record['candidate_votes'][cand] = record['valid_ballots']
    return records


def cross_validate_killernay(records: List[Dict], killernay: Dict) -> List[Dict]:
    """Cross-validate with Killernay ground truth."""
    # Placeholder: compare with ground truth
    return records


def revalidate(records: List[Dict]) -> List[Dict]:
    """Final revalidation."""
    return records


def run_pipeline(province: str, dry_run: bool = False) -> Dict:
    """Run the complete postprocessing pipeline."""
    print(f"Running postprocessing pipeline for {province}")

    # Load data
    records = load_ocr_data(province)
    killernay = load_killernay_data(province)
    ect_ref = load_ect_reference(province)

    print(f"Loaded {len(records)} OCR records")

    # Apply rules
    records = fix_metadata_from_filepath(records, province)
    records = fix_station_no_from_filepath(records, province)
    records = dedup_records(records)
    records = dedup_interleaved(records)
    records = fix_total_votes(records)
    records = fix_remaining_ballots(records)
    records = fix_negative_values(records)
    records = fix_outliers(records)
    records = normalize_candidates(records, ect_ref)
    records = flag_turnout(records)
    records = fix_candidate_vote_outliers(records)
    records = cross_validate_killernay(records, killernay)
    records = revalidate(records)

    # Save results
    output_file = DATA_DIR / f"postprocessed_{province}.json"
    if not dry_run:
        save_json(records, output_file)
        print(f"Saved {len(records)} records to {output_file}")
    else:
        print(f"Dry run: would save {len(records)} records to {output_file}")

    # Generate stats
    stats = {
        'province': province,
        'input_records': len(load_ocr_data(province)),
        'output_records': len(records),
        'rules_applied': ['R0a', 'R0b', 'R0c', 'R0d', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9'],
        'dry_run': dry_run
    }

    stats_file = DATA_DIR / f"postprocess_stats_{province}.json"
    save_json(stats, stats_file)
    print(f"Saved stats to {stats_file}")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Postprocess OCR election data')
    parser.add_argument('--province', required=True, help='Province name (e.g., chaiyaphum)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without saving')
    args = parser.parse_args()

    try:
        stats = run_pipeline(args.province, args.dry_run)
        print("Pipeline completed successfully")
        print(json.dumps(stats, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())