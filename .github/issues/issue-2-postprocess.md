# Issue 2: Postprocess + validation

## Description
Enhance postprocessing pipeline and add comprehensive validation tests.

## Tasks
- [ ] Fix `check_postprocess_validation.py` to call correct postprocess.py path
- [ ] Run postprocess pipeline (R0-R9) on all 3 provinces
- [ ] Run validation rules (V1-V11) and generate reports
- [ ] Create regression tests for postprocess functions
- [ ] Add unit tests for validation edge cases
- [ ] Generate postprocess stats and validation summary reports

## Acceptance Criteria
- Postprocess runs successfully on all provinces
- Validation reports generated with error/warning counts
- Regression tests pass
- Pipeline stats show improvement over baseline

## Labels
enhancement, postprocess, validation, high-priority