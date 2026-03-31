# ROADMAP - Election Verification OCR Project

## Vision
ปิด coverage 100% ของ 77 จังหวัด, data pipeline ตรวจสอบได้, review flow scale-out, docs ตรง, cost controlled.

## 30 วัน (Phase 32)

1. data integrity + cross-ref
   - เพิ่ม verification scripts
   - รัน full data (ชัยภูมิ, ตาก, เพชรบูรณ์) และ log gaps
   - rerun `scripts/prepare_cross_reference.py` + update outputs
2. postprocess + validation
   - set baseline rule coverage
   - add regression tests (postprocess + validation)
3. review throughput
   - priority queue, auto-approve low-risk
4. CI/CD
   - add full pipeline commit check
5. cost metrics
   - daily OCR cost report script
6. docs
   - complete `ROADMAP.md`, `TASKS_CHECKLIST.md`, issue template

## 60 วัน (Phase 33)

1. นำเพชรบูรณ์ฯ 80.1% ✕ ต่อด้วย 100% โดยเชื่อม PDF สำรอง
2. เปิด cross-ref ฐาน 77 จังหวัด
3. deploy production review app version 2 with QA sprint
4. add map + metrics dashboard + benchmark

## 90 วัน (Phase 34)

1. finish national run (149,936 PDFs)
2. automate daily ingestion 1 province per day
3. publish technical report (cost/performance, accuracy)
4. archive version + reproducible scripts

## Success criteria

- [x] 3 provinces OCR data integrity > 99%
- [ ] Postprocess errors <5% by rule
- [ ] Review app backlog < 1,000 items
- [ ] CI green on every PR
- [ ] Cost <= $0.0015/page
- [ ] Documentation complete for handoff
