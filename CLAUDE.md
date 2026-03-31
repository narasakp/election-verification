# CLAUDE.md

## Project structure (โครงสร้างโปรเจกต์)

- `election-verification/` (หลัก)
  - `data/` - JSON, dashboards, OCR results, indexes
  - `scripts/` - พวก utility สำหรับ analysis, build, export
  - `cloud/` - Google Cloud Functions, dispatch, collect, deploy scripts
  - `review-app/` - React frontend สำหรับ citizen review + analytics
  - `docs/` - static review UI (GitHub Pages) และคู่มือ
  - `assets/` - ไฟล์สื่อ/สไตล์
  - `DEVELOPMENT_LOG.md` - บันทึกขั้นตอนทั้งหมด (Phases 1-31)
  - `README.md`, `SECURITY.md` ฯลฯ

- สถิติสำคัญ (จาก log):
  - Python scripts 172+, React components 12+, unit tests 115+, data files 56+, OCR records 16,407
  - PDF 149,936 files, Google Drive backup 77/77 จังหวัด
  - Cloud Function (Gemini OCR), Dashboards 7

## OCR pipeline (สายงาน OCR)

1. **Data source discovery**
   - ค้นหา PDF สส.5/16/5/18 จากเว็บ ECT จ.ต่าง ๆ
   - `crawl_province_docs.py`, `extract_doc_links.py`, `download_ss518.py`

2. **Initial OCR evaluation**
   - Tesseract (ไม่ดี) → Google Cloud Vision → Gemini
   - `ocr_ss518.py`, `ocr_ss518_v2.py`, `ocr_cloud_vision.py`

3. **Drive staging**
   - เก็บ PDF ใน Google Drive (`download_to_drive.py`, `build_drive_index.py`)
   - แยก page-level (single-page upload) เพื่อให้ ReviewCard เลือกหน้าได้ตรง
   - `scripts/split_and_upload.py`

4. **Multi-model extraction**
   - `ocr_multimodel.py` + `cloud/function/main.py` + `cloud/ocr_local.py`
   - model chain: Gemini 2.5 flash / 2.5 flash lite / 3 flash preview + fallback, retries
   - adaptive DPI, JSON repair, page-level resume

5. **Distributed Cloud dispatch**
   - `cloud/dispatch.py`, `cloud/dispatch_missing.py`, `cloud/dispatch_slow.py`, `cloud/collect.py`
   - ตาก + เพชรบูรณ์ dispatched multi-runs, retries, error classification

6. **Postprocessing**
   - `postprocess.py` สำหรับ province-agnostic กับ 9 rules (R0-R9)
   - metadata fix, dedupe, totals, negative/outlier correction, candidate normalization + ECT reference, turnout flags
   - cross-validation with Killernay ground truth

7. **Validation & QA**
   - 11 review rules (`validation.js` in React app), anomaly flags, cross-reference 4 sources
   - spinner/UI for errors, gating, dark mode, key handling

## Current progress (สถานะปัจจุบัน)

- Phase 31 complete: OCR full completion for:
  - ชัยภูมิ 100% (5,595 front pages)
  - ตาก 99.3% (2,318/2,335 front pages)
  - เพชรบูรณ์ 80.1% (5,094/6,362 front pages)
- Total: 16,407 OCR records, 13,007 parsed front pages (91% coverage from 3 provinces)
- Cloud pipeline production: Gemini OCR in Cloud Functions + retries + rate-limit
- Google Drive backup end-to-end 149,936 PDF + 5,089 single-page PDFs + dashboard
- Review app production: React + GitHub Pages, 6,111 review items, dark mode, analytics dashboard, choropleth map, backup map
- Test suite 115 tests passed, reactive ErrorBoundary + accessibility
- Security fix: API key not in repo (`.env` + `.gitignore` + pre-commit hook), new key verified
- Cost plot: ~$14.14 total OCR cost, $0.0011/page

## Remaining open work (งานที่เหลือ)

1. **เพชรบูรณ์ coverage gap** ~20% pages missing (1,268), เนื่องจาก PDF ขาดหาย/502+ไม่สามารถดาวน์โหลด
   - ทางเลือก: หาแหล่ง PDF ทดแทน (ECT province site, Drive mirror, archive)
   - สำรวจ force-redownload / re-crawl ตั้งค่า throttle

2. **station-level API & data completeness**
   - กกต. ยังไม่มี API level-by-station; ต้องพึ่ง OCR/drive scraping
   - ปรับปรุง crosscheck กับ ECT ultimate snapshots เมื่อมี data ใหม่

3. **data quality / accuracy metric**
   - เสริม metric pipeline: bias per candidate, stall in/outliers, stop after tuned thresholds
   - ช่วยเตรียม SJR paper, elaborate on OCR error breakdown

4. **review throughput**
   - ลด manual review backlog: ถอดรายการ priority, crowdsourcing (citizen UI), online workflow technical stack
   - เพิ่ม automation for simple fixes (R3-R6) ก่อน human review

5. **full-province scaling** (beyond 3 provinces)
   - เตรียมการ OCR `149,936` PDFs nationwide
   - ปรับขนาด dispatcher + buckets + mapping
   - ตรวจว่า `postprocess.py` generalization รับ 77 provinces

6. **maintenance & docs**
   - update README+SECURITY for post-phase-31 findings
   - จัดลำดับ issue list and milestone on GitHub

---

## Notes

- สรุปนี้อ้างอิงจาก `DEVELOPMENT_LOG.md` อย่างละเอียด (Phases 1..31)
- ขณะนี้โครงการมีประวัติทำงานครบถ้วน, production-ready OCR+review UI
- ถามเพิ่มได้ถ้าต้องการให้สรุปเฉพาะไฟล์, target state, หรือ action plan ระยะสั้น/กลาง/ยาว
