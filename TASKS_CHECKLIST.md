# TASKS CHECKLIST

## 1) Data integrity + cross-ref
- [ ] สร้าง script `scripts/verify_data_integrity.py`
- [ ] สร้าง script `scripts/prepare_cross_reference.py` (ถ้ายังไม่มี)
- [ ] รัน cross-ref, export report

## 2) Postprocess + validation
- [ ] สร้าง script `scripts/check_postprocess_validation.py`
- [ ] รัน pipeline R0-R9 + V1-V11
- [ ] สร้าง regression tests

## 3) Review throughput
- [ ] priority queue filter in review app
- [ ] auto-approve low-risk items
- [ ] backlog monitor

## 4) CI/CD/ops
- [ ] เพิ่ม workflow file `.github/workflows/ci.yml`
- [ ] `npm test`, `pytest`, `lint`, `npm run build`
- [ ] nightly smoke test

## 5) Cost/perf metrics
- [ ] สร้าง `scripts/ocr_cost_report.py`
- [ ] สร้าง output `data/ocr_cost_report.json`
- [ ] สร้าง markdown summary `docs/cost_metrics.md`

## 6) Roadmap/docs
- [x] สร้าง `ROADMAP.md`
- [x] สร้าง `TASKS_CHECKLIST.md`
- [ ] สร้าง `.github/ISSUE_TEMPLATE/task-progress.md`
