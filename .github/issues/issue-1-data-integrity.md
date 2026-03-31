# Issue 1: Data integrity + cross-ref

## Description
Implement data integrity verification and cross-reference updates for OCR data.

## Tasks
- [ ] Create/update `scripts/verify_data_integrity.py` to handle drive_index as list/dict
- [ ] Fix key mapping for `file_id`, `station_id`, `path` in verification script
- [ ] Run verification on all 3 provinces (chaiyaphum, tak, phetchabun)
- [ ] Update `scripts/prepare_cross_reference.py` if needed
- [ ] Rerun cross-reference pipeline and update anomaly_flags
- [ ] Generate missing coverage report by province/zone/candidate

## Acceptance Criteria
- Verification script runs without errors
- Cross-reference data updated with latest OCR results
- Missing data report generated and reviewed

## Labels
enhancement, data-integrity, high-priority