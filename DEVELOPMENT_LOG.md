# บันทึกการพัฒนาระบบตรวจสอบผลเลือกตั้ง สส. 2569
# Election Verification System — Development Log

> **ผู้พัฒนา:** narasak poophayang  
> **ระยะเวลา:** 12 กุมภาพันธ์ – 31 มีนาคม 2569 (48 วัน)  
> **สถานะ:** Active Development  

---

## สารบัญ (Table of Contents)

- [สถิติรวมของโปรเจกต์](#สถิติรวมของโปรเจกต์)
- [Phase 1: ฐานข้อมูลและแดชบอร์ดเริ่มต้น](#phase-1-ฐานข้อมูลและแดชบอร์ดเริ่มต้น) — 12 ก.พ.
- [Phase 2: ค้นหาข้อมูลระดับหน่วยเลือกตั้ง](#phase-2-ค้นหาข้อมูลระดับหน่วยเลือกตั้ง) — 16–18 ก.พ.
- [Phase 3: OCR — เริ่มอ่านเอกสารลายมือ](#phase-3-ocr--เริ่มอ่านเอกสารลายมือ) — 18–19 ก.พ.
- [Phase 4: Google Drive + React Review App](#phase-4-google-drive--react-review-app) — 19–20 ก.พ.
- [Phase 5: Drive Index + Cloud Vision OCR ขนาดใหญ่](#phase-5-drive-index--cloud-vision-ocr-ขนาดใหญ่) — 21–22 ก.พ.
- [Phase 6: Multi-Model OCR + ปรับปรุงคุณภาพ](#phase-6-multi-model-ocr--ปรับปรุงคุณภาพ) — 22 ก.พ.
- [Phase 7: Citizen Review UI + Authentication](#phase-7-citizen-review-ui--authentication) — 23–24 ก.พ.
- [Phase 8: Cloud OCR + Multi-Model Pipeline](#phase-8-cloud-ocr--multi-model-pipeline) — 24–25 ก.พ.
- [Phase 9: Cloud Function Deployment](#phase-9-cloud-function-deployment) — 25 ก.พ.
- [Phase 10: Backup + Dashboard](#phase-10-backup--dashboard) — 26–28 ก.พ.
- [Phase 11: Multi-Station Bug Fix + ปรับปรุง OCR](#phase-11-multi-station-bug-fix--ปรับปรุง-ocr) — 1–4 มี.ค.
- [Phase 12: Deep Validation + Postprocessing ชัยภูมิ](#phase-12-deep-validation--postprocessing-ชัยภูมิ) — 5–7 มี.ค.
- [Phase 13: Per-Zone Deep Analysis ชัยภูมิ](#phase-13-per-zone-deep-analysis-ชัยภูมิ) — 8–9 มี.ค.
- [Phase 14: Postprocessing Pipeline](#phase-14-postprocessing-pipeline) — 9 มี.ค.
- [Phase 15: Name-Matching + Generalize Pipeline](#phase-15-name-matching--generalize-pipeline) — 10 มี.ค.
- [Phase 16: Review UI Improvements](#phase-16-review-ui-improvements) — 10 มี.ค.
- [Phase 17: React Review App — Production Deploy](#phase-17-react-review-app--production-deploy) — 13–15 มี.ค.
- [Phase 18: PDF Split + Single-Page Upload](#phase-18-pdf-split--single-page-upload) — 16–17 มี.ค.
- [Phase 19: Anomaly Cross-Reference + Data Integrity](#phase-19-anomaly-cross-reference--data-integrity) — 17 มี.ค.
- [Phase 20: ECT Backup Dashboard Integration](#phase-20-ect-backup-dashboard-integration) — 17 มี.ค.
- [Phase 21: UI/UX Polish, Testing & Documentation](#phase-21-uiux-polish-testing--documentation) — 19 มี.ค.
- [Phase 22: Data & Analytics Dashboards](#phase-22-data--analytics-dashboards) — 19 มี.ค.
- [Phase 23: Cross-Reference 4 แหล่งข้อมูล](#phase-23-cross-reference-4-แหล่งข้อมูล) — 19 มี.ค.
- [Phase 24: ProvinceHeatmap — SVG Choropleth Map](#phase-24-provinceheatmap--svg-choropleth-map) — 20–21 มี.ค.
- [Phase 25: BackupDashboard — Thailand Map + Enhanced Visualization](#phase-25-backupdashboard--thailand-map--enhanced-visualization) — 21 มี.ค.
- [Phase 26: UX Improvements — Confirmations, Help, Import/Export Info](#phase-26-ux-improvements--confirmations-help-importexport-info) — 21–22 มี.ค.
- [Phase 27: Google Drive Links + Progress >100% Explanation](#phase-27-google-drive-links--progress-100-explanation) — 22 มี.ค.
- [Phase 28: README v4.0 — Comprehensive Update](#phase-28-readme-v40--comprehensive-update) — 22 มี.ค.
- [Phase 29: Refactor, Testing, Dark Mode & Code Splitting](#phase-29-refactor-testing-dark-mode--code-splitting) — 23 มี.ค.
- [Phase 30: Test Expansion + Error Boundaries + Accessibility + Performance](#phase-30-test-expansion--error-boundaries--accessibility--performance) — 24 มี.ค.
- [Phase 31: Cloud OCR Completion — API Key Fix + Dispatch ตาก & เพชรบูรณ์](#phase-31-cloud-ocr-completion--api-key-fix--dispatch-ตาก--เพชรบูรณ์) — 25–27 มี.ค.
- [Phase 32: OCR Error Recovery — 503/502 Retry + Bug Fix + Near-100% Completion](#phase-32-ocr-error-recovery--503502-retry--bug-fix--near-100-completion) — 31 มี.ค.
- [Phase 33: Data Integrity & Cross-Reference — Final Validation Pipeline](#phase-33-data-integrity--cross-reference--final-validation-pipeline) — 31 มี.ค.
- [Phase 34: Review Throughput & User Experience — Bulk Operations & Anomaly Summary](#phase-34-review-throughput--user-experience--bulk-operations--anomaly-summary) — 1 เม.ย.
- [สรุป Timeline](#สรุป-timeline)
- [สถาปัตยกรรมระบบสุดท้าย](#สถาปัตยกรรมระบบสุดท้าย)
- [ข้อมูลอ้างอิงภายนอก](#ข้อมูลอ้างอิงภายนอก)
- [ข้อจำกัดและบทเรียน](#ข้อจำกัดและบทเรียน)

---

## สถิติรวมของโปรเจกต์

| หมวด | จำนวน |
|------|-------|
| Python scripts | 172+ ไฟล์ |
| React components | 12 ไฟล์ (+ 3 hooks, utils) |
| Unit tests | 115 tests (4 test files) |
| Data files (data/) | 56 ไฟล์ |
| Data files (review-app) | 4 ไฟล์ (review_data, anomaly_flags, backup_status, cross_reference_sources) |
| PDF ดาวน์โหลด | 149,936 ไฟล์ (77 จังหวัด) |
| OCR records | 17,628 รายการ (3 จังหวัด) |
| Review items | 6,111 รายการ (deployed) |
| Git commits | 26+ commits |
| Cloud Functions | 1 (Gemini OCR) |
| Dashboards | 7 (main, anomaly, compare, review, backup, analytics, province heatmap) |
| GitHub Pages | Deploy อัตโนมัติผ่าน GitHub Actions |
| Google Drive Backup | 77/77 จังหวัดครบ (149,936 PDFs) |

---

## Phase 1: ฐานข้อมูลและแดชบอร์ดเริ่มต้น
### 12 กุมภาพันธ์ 2569 (วันที่ 1)

**เป้าหมาย:** สร้างระบบพื้นฐานสำหรับรวบรวมและวิเคราะห์ผลเลือกตั้ง

**สิ่งที่ทำ:**
- สร้าง repository `election-verification` — initial commit
- พัฒนา `fetch_ect_data.py` — ดึงข้อมูลจาก กกต. (400 เขต, 77 จังหวัด)
- พัฒนา `fetch_vote62_data.py` — ดึงข้อมูล Vote62 สำหรับเปรียบเทียบ
- สร้าง `probe_ect_api.py`, `probe_vote_station.py` — สำรวจ API ของ กกต.
- พัฒนา `analyze_ect_only.py`, `analyze_anomalies.py` — วิเคราะห์ความผิดปกติ 8 มิติ
- สร้าง Dashboard 3 หน้า: main (`index.html`), anomaly (`anomaly.html`), compare (`compare.html`)

**ผลลัพธ์:**
- `ect_raw_data.json` (0.2MB), `election_data.json` (2.9MB)
- Anomaly analysis ครบ 8 มิติ พร้อม visualization
- พบว่า **station-level API ของ กกต. ยังไม่เปิด** (404 ทุก endpoint)
- ผลเลือกตั้งระดับเขตมีเฉพาะ `stats_cons.json` เท่านั้น

**Scripts สร้างใหม่:** `examples.py`, `election_verification_system.py`, `advanced_analytics.py`, `generate_json_data.py`, `vote62_comparator.py`, `fetch_ect_data.py`, `fetch_vote62_data.py`, `probe_ect_api.py`, `probe_vote_station.py`, `analyze_ect_only.py`, `analyze_anomalies.py`

---

## Phase 2: ค้นหาข้อมูลระดับหน่วยเลือกตั้ง
### 16–18 กุมภาพันธ์ 2569 (วันที่ 5–7)

**เป้าหมาย:** หาแหล่งข้อมูลระดับหน่วยเลือกตั้ง (station-level) เนื่องจาก กกต. เปิดเฉพาะระดับเขต

**สิ่งที่ทำ:**
- วิเคราะห์เว็บไซต์ กกต. 77 จังหวัด — ค้นพบว่าเป็น Nuxt SPA (~1.7MB/หน้า)
- พัฒนาชุด probe scripts: `probe_ect_docs.py`, `fetch_ect_docs_page.py`, `find_province_docs.py`
- ค้นพบ **PDF แบบ สส.5/18 (ผลรายหน่วย)** บนเว็บ กกต. จังหวัด
- พัฒนา `extract_doc_links.py` — ดึง URL PDF จากหน้าเว็บ
- พัฒนา `crawl_province_docs.py` — crawl เอกสาร กกต. อัตโนมัติ
- พัฒนา `download_ss518.py` — ระบบดาวน์โหลด PDF ครบ 77 จังหวัด พร้อม resume/retry/rate-limit

**ค้นพบสำคัญ:**
- รูปแบบ URL: `https://www.ect.go.th/{slug}/th/election-2026`
- PDF URL: `https://www.ect.go.th/web-upload/{hash}/m_document/{cat}/{doc}/file_download/{hash}.pdf`
- ทดสอบ 3 จังหวัด: กรุงเทพ (103 PDFs), เชียงใหม่ (83 PDFs), นครราชสีมา (205 PDFs)

**Scripts สร้างใหม่:** `probe_ect_docs.py`, `probe_station_api.py`, `fetch_ect_docs_page.py`, `find_province_docs.py`, `crawl_province_docs.py`, `extract_doc_links.py`, `download_ss518.py`

---

## Phase 3: OCR — เริ่มอ่านเอกสารลายมือ
### 18–19 กุมภาพันธ์ 2569 (วันที่ 7–8)

**เป้าหมาย:** แปลงภาพใบ สส.5/16 (ผลคะแนนลายมือ) เป็นข้อมูลดิจิทัล

**สิ่งที่ทำ:**
- วิเคราะห์โครงสร้าง PDF: `list_chaiyaphum.py`, `check_pdf_sample.py`, `extract_sample_page.py`
- ทดลอง Tesseract OCR → **ผลไม่ดี** กับลายมือภาษาไทย
- พัฒนา `ocr_ss518.py` (v1) — ใช้ Google Cloud Vision API
- พัฒนา `ocr_ss518_v2.py` — ปรับปรุง prompt และ parsing
- สร้าง `review_server.py` + `review_ui.html` — UI ตรวจสอบผล OCR แบบ local
- วิเคราะห์ข้อมูล: `count_pdfs.py`, `check_chaiyaphum.py`, `check_ocr_remaining.py`
- จัดอันดับจังหวัด: `rank_provinces.py` — เลือก 3 จังหวัดนำร่อง
- ทดสอบ parser: `test_thai_num.py`, `test_parser_v2.py`

**ผลลัพธ์:**
- `ocr_results_chaiyaphum.json` (v1: Tesseract), `ocr_results_chaiyaphum_v2.json` (v2: Vision API)
- `ocr_vision_chaiyaphum.csv` — ผลเบื้องต้น
- เลือก 3 จังหวัดนำร่อง: **ชัยภูมิ, ตาก, เพชรบูรณ์**
- Google Vision API ให้ผลดีกว่า Tesseract มาก สำหรับลายมือไทย

**Scripts สร้างใหม่:** `list_chaiyaphum.py`, `check_pdf_sample.py`, `extract_sample_page.py`, `find_tesseract.py`, `ocr_ss518.py`, `ocr_test_single.py`, `ocr_ss518_v2.py`, `count_pdfs.py`, `review_server.py`, `check_image_map.py`, `check_chaiyaphum.py`, `check_ocr_remaining.py`, `retry_failed.py`, `rank_provinces.py`, `review_ui.html`, `check_mapping.py`, `test_thai_num.py`, `test_parser_v2.py`

---

## Phase 4: Google Drive + React Review App
### 19–20 กุมภาพันธ์ 2569 (วันที่ 8–9)

**เป้าหมาย:** จัดเก็บ PDF บน Google Drive และสร้าง Review UI ที่ดีขึ้น

**สิ่งที่ทำ:**
- อัปโหลด PDF ไป Google Drive: `download_to_drive.py`
- วิเคราะห์ ECT: `analyze_ect.py`, `analyze_ect2.py`
- ตรวจสอบโฟลเดอร์ Drive: `check_drive_folder.py`, `verify_drive_folders.py`
- Scrape ECT central: `scrape_ect_central.py`, `scrape_ect_mapping.py`, `scrape_ect_final.py`
- แก้ mapping: `fix_mapping.py`
- เริ่มสร้าง **React Review App** (`review-app/`)
  - Vite + React 18 + TailwindCSS + Lucide Icons
  - Component: `ReviewCard.jsx`, `UploadPanel.jsx`
  - Dev server บน port 3000

**ผลลัพธ์:**
- `ss518_drive_index.json` — ดัชนี PDF บน Drive
- `ect_central_links.json`, `ect_province_drive_mapping.json`
- Review App v1 — แสดงผล OCR พร้อมรูปภาพ PDF

**Scripts สร้างใหม่:** `download_to_drive.py`, `analyze_ect.py`, `analyze_ect2.py`, `check_drive_folder.py`, `scrape_ect_central.py`, `scrape_ect_mapping.py`, `scrape_ect_final.py`, `verify_drive_folders.py`, `fix_mapping.py`

---

## Phase 5: Drive Index + Cloud Vision OCR ขนาดใหญ่
### 21–22 กุมภาพันธ์ 2569 (วันที่ 10–11) ⚡ ทำงานข้ามคืน

**เป้าหมาย:** สร้าง Drive index ครบถ้วน และเริ่ม OCR จริงจัง

**สิ่งที่ทำ:**
- พัฒนา `copy_shared_drive.py` — คัดลอกไฟล์จาก Shared Drive
- พัฒนา `backup_to_drive.py` — สำรองข้อมูล OCR ขึ้น Drive
- พัฒนา `build_drive_index.py` — สร้างดัชนีไฟล์ Drive ครบ 3 จังหวัด
- พัฒนา `ocr_cloud_vision.py` — OCR ด้วย Google Cloud Vision API (batch)
- วิเคราะห์ข้อมูล: `_check_drive_items.py`, `_check_ocr_progress.py`, `analyze_stations.py`
- เริ่ม **Killernay cross-validation**: `_cross_validate_killernay.py`
- วิเคราะห์ ECT: `_inspect_ect_data.py`, `_inspect_ect_data2.py`
- สร้าง reporter database: `_build_reporter_db.py`
- Enrich OCR data: `enrich_ocr.py`, `_show_enriched.py`

**ผลลัพธ์:**
- `drive_index_chaiyaphum.json` (0.2MB), `drive_index_tak.json` (0.7MB), `drive_index_phetchabun.json` (0.8MB)
- `ocr_vision_chaiyaphum.json` (2.7MB), `ocr_vision_tak.json` (1.8MB), `ocr_vision_phetchabun.json` (2.4MB)
- `killernay_constituency_full.csv` (0.4MB) — ground truth data

---

## Phase 6: Multi-Model OCR + ปรับปรุงคุณภาพ
### 22 กุมภาพันธ์ 2569 (วันที่ 11) ⚡⚡ ทำงานทั้งวัน 04:00–23:00

**เป้าหมาย:** เปรียบเทียบ OCR หลายโมเดลและปรับปรุงคุณภาพ

**สิ่งที่ทำ:**
- พัฒนา `ocr_preprocess.py` — preprocessing (contrast, denoise, deskew)
- พัฒนา `ocr_roi.py` — Region of Interest extraction
- ทดสอบ Claude Vision: `_test_claude.py`
- เปรียบเทียบ accuracy: `_compare_accuracy.py`, `_compare_runs.py`, `_honest_comparison.py`, `_real_comparison.py`
- วิเคราะห์ candidate: `_check_candidates.py`, `_check_data.py`, `_check_confidence.py`
- พัฒนา **auto-correction pipeline**: `ocr_postprocess.py`
  - R1: fix remaining_ballots (ห้ามติดลบ)
  - R2: recalculate turnout (ห้ามทำให้บัตรเหลือติดลบ)
  - R6: total_votes = sum(candidate_votes) (ต้อง > 50% ของบัตรดี)
- ทดสอบ: `_test_autocorrect.py`, `_reapply_autocorrect.py`
- **Production run เริ่มต้น**: `_production_run.py`, `production_run.log`

**ผลลัพธ์:**
- ค้นพบ Gemini Flash ให้ผลดีกว่า Cloud Vision สำหรับ structured extraction
- Auto-correction: 5 → 2 corrections (ตัดที่ผิดออก), 0 negative values, 7 proper flags
- Confidence improvement: 32% → 46% high confidence

---

## Phase 7: Citizen Review UI + Authentication
### 23–24 กุมภาพันธ์ 2569 (วันที่ 12–13)

**เป้าหมาย:** สร้าง UI สำหรับอาสาสมัครตรวจสอบ + ระบบ Authentication

**สิ่งที่ทำ:**
- สร้าง `docs/review/` — Static citizen review app สำหรับ GitHub Pages
  - `index.html` — โครงสร้างหน้า + onboarding modal
  - `app.js` — data loading, filtering, rendering, Google Sign-In
  - `style.css` — สไตล์ทั้งหมด
  - `SETUP.md` — คู่มือติดตั้ง OAuth + Google Form
- พัฒนาระบบ Authentication: Google Identity Services (GIS)
  - JWT decode สำหรับ user info
  - Verified badge สำหรับผู้ใช้ที่ login
- พัฒนาระบบ review submission ผ่าน Google Forms
  - 6 fields: item_id, file, station, status, comment, email
  - Hidden iframe POST — ไม่ต้องมี backend
- ปรับปรุง React Review App: `AuthGate.jsx`, `useAuth.js`, `submitReview.js`

**Architecture:**
- **Level 1 Auth**: Google Sign-In + Google Forms (no backend needed)
- Consensus model: 1 person = low, 2 same = medium, 3+ same = high trust

---

## Phase 8: Cloud OCR + Multi-Model Pipeline
### 24–25 กุมภาพันธ์ 2569 (วันที่ 13–14) ⚡ ทำงานข้ามคืน

**เป้าหมาย:** Deploy OCR บน Cloud + ประมวลผล PDF ขนาดใหญ่

**สิ่งที่ทำ:**
- วิเคราะห์ช่องว่าง: `_check_missing.py`, `_check_coverage.py`
- พัฒนา `_ocr_split_and_process.py` — แบ่ง PDF ขนาดใหญ่เป็นชุดย่อย 4 หน้า
  - Page-level resume: save ทุกหน้า
  - 5s delay ระหว่างหน้า
- พัฒนา **`ocr_multimodel.py`** — Multi-model Gemini pipeline
  - `GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"]`
  - Fallback chain: ลองทุกโมเดลรวดเร็ว, ถ้าหมด wait 30s × cycle, up to 4 mega-retries
  - JSON repair (`_repair_json`) สำหรับ response ที่ผิดรูปแบบ
  - Adaptive DPI: 200 → 150 → 100 fallback
  - Incremental save ทุกไฟล์

**ผลลัพธ์:**
- **ชัยภูมิ: OCR ครบ 263/263 ไฟล์** → 5,892 records
- `ocr_multimodel_chaiyaphum.json` (18.2MB)

---

## Phase 9: Cloud Function Deployment
### 25 กุมภาพันธ์ 2569 (วันที่ 14)

**เป้าหมาย:** Deploy OCR เป็น Cloud Function สำหรับประมวลผลแบบกระจาย

**สิ่งที่ทำ:**
- พัฒนา Cloud Function: `cloud/function/main.py`
  - Google Cloud Function Gen2
  - Gemini API integration
  - PDF → PNG conversion บน cloud
- พัฒนา dispatcher: `cloud/dispatch.py`, `cloud/collect.py`
- Deploy script: `cloud/deploy.ps1`, `cloud/env.yaml`
- ทดสอบ: `cloud/test_function.py`
- **เริ่ม OCR จังหวัดอื่น:**
  - ตาก: 3,155 records
  - เพชรบูรณ์: 3,329 records

**ผลลัพธ์:**
- `ocr_multimodel_tak.json` (8MB)
- `ocr_multimodel_phetchabun.json` (6.8MB)
- Dispatch errors: `dispatch_errors_tak.json`, `dispatch_errors_phetchabun.json`

---

## Phase 10: Backup + Dashboard
### 26–28 กุมภาพันธ์ 2569 (วันที่ 15–17)

**สิ่งที่ทำ:**
- ระบบ backup: `run_backup_all.ps1`
- Dashboard สำรวจข้อมูล: `scripts/dashboard.py`
- ECT candidates classification: `_classify_vote_type.py`
  - vote_type: แบ่งเขต (≤10 candidates) vs บัญชีรายชื่อ (>10)
- ตรวจสอบ constituency: `_check_cons.py`, `_check_cons2.py`
- ดึงข้อมูลพรรค: `_fetch_parties.py`
- ตรวจสอบผู้สมัคร: `_verify_candidates.py`, `_run_verify.py`
- **สร้าง ECT reference**: `_build_ect_reference.py`
  - `ect_candidates_reference.json` — ข้อมูลอ้างอิงผู้สมัคร กกต. ทุกเขต

---

## Phase 11: Multi-Station Bug Fix + ปรับปรุง OCR
### 1–4 มีนาคม 2569 (วันที่ 18–21)

**ปัญหาสำคัญ:** PDF ที่มี 10+ หน่วย/ไฟล์ ทำให้ OCR อ่าน constituency ผิด (862/5,443 records)

**สิ่งที่ทำ:**
- วิเคราะห์ปัญหา: `analyze_multi_station.py`, `analyze_underprocessed.py`
- **แก้ Dynamic Prompt** ใน `cloud/function/main.py` และ `cloud/ocr_local.py`:
  - `EXTRACTION_PROMPT` → `build_prompt(meta, page_num, total_pages)`
  - เพิ่มคำเตือน multi-station PDF
  - ใส่ context: หน้าที่ X จาก Y, metadata จาก file path
- **Always-Override Metadata**: file path เป็น ground truth เสมอ
- เติม OCR ที่ขาด: `ocr_fill_missing.py`
- Cloud dispatch ปรับปรุง: `cloud/dispatch_missing.py`, `cloud/dispatch_slow.py`
- Precache PDFs: `cloud/precache_pdfs.py`, `cloud/copy_and_cache.py`

**ผลลัพธ์:**
- Killernay cross-validation error: **249.6% → 40.3%**
- Candidate mismatches: **107 → 11**
- Ghost candidates removed: **1,433 → 5,036** (ด้วย constituency ที่ถูกต้อง)

---

## Phase 12: Deep Validation + Postprocessing ชัยภูมิ
### 5–7 มีนาคม 2569 (วันที่ 22–24)

**เป้าหมาย:** ตรวจสอบข้อมูลชัยภูมิอย่างละเอียดและแก้ไขปัญหาเชิงลึก

**สิ่งที่ทำ:**
- Validation: `validate_chaiyaphum.py` → `validation_chaiyaphum.json`
- วิเคราะห์ปัญหา: `analyze_issues_chaiyaphum.py`
- Re-OCR หน้าที่มีปัญหา: `reocr_problem_pages.py`
  - ใช้ Gemini re-process หน้าที่ OCR ผิดพลาด
- วิเคราะห์ failures: `_analyze_failed.py`, `_find_failed.py`, `_retry_failed.py`
- ปรับปรุง Cloud Function prompt: `cloud/function/main.py`, `cloud/ocr_local.py`

---

## Phase 13: Per-Zone Deep Analysis ชัยภูมิ
### 8–9 มีนาคม 2569 (วันที่ 25–26) ⚡⚡⚡ ทำงานเกือบ 24 ชม.

**เป้าหมาย:** วิเคราะห์ทุกเขตเลือกตั้งอย่างละเอียด หา root cause ของ error

**สิ่งที่ทำ (เขต 2 — ปัญหา deduplication):**
- `_analyze_killernay_errors.py` — หา high-error records
- `_cross_check_ect.py` — cross-check กับ กกต.
- `_station_coverage.py` — วิเคราะห์ coverage ของหน่วย
- `_fix_zone2.py`, `_fix_zone2_votetype.py`, `_fix_zone2_deep.py` — ซ่อมข้อมูลเขต 2
- `_check_killernay_csv.py`, `_fix_zone2_killernay.py` — ตรวจ Killernay
- `_fix_zone2_noise.py` — ลด noise
- `_zone2_why_excess.py` — วิเคราะห์ records เกิน
- `_zone2_find_dupes.py` — หา duplicates
- `_analyze_z2_drive.py`, `_analyze_z2_combined.py` — วิเคราะห์ combined PDF
- `_analyze_z2_votes.py`, `_analyze_z2_r7.py` — วิเคราะห์คะแนนและ R7
- `_analyze_z2_dedup.py`, `_analyze_z2_dedup2.py`, `_analyze_z2_dedup3.py`
  - ค้นพบ **interleaved combined files** เป็นสาเหตุหลักของ duplicates (405 records vs 345 expected)

**สิ่งที่ทำ (เขต 3 + 7 — ปัญหา coverage):**
- `_analyze_z3_missing.py`, `_analyze_z3_deep.py` — หา missing stations เขต 3
- `_analyze_z7_corrupt.py` — วิเคราะห์ PDFs เสียหายเขต 7
- `_check_missing_z3z7.py`, `_find_unocrd_z3z7.py`, `_find_undercount_z7.py`
- `_check_corrupt_z7.py`, `_check_z3_overlap.py`
- **พยายามหา PDF เพิ่ม:** `_ocr_new_files.py`, `_find_nongkham_url.py/2.py`, `_find_nongkham_drive.py`, `_redownload_nongkham.py`, `_crawl_ect_nongkham.py`, `_crawl_ect_deep.py`, `_crawl_ect_api.py`
- Re-OCR: `_reocr_undercount.py`, `_reocr_z7.py`, `_check_z7_reocr.py`
- Coverage analysis: `_check_drive_index_z3z7.py`, `_compare_drive_vs_ocr.py`, `_check_tamafaiwan.py`, `_check_small_pdfs.py`
- Station mapping: `_analyze_station_mapping.py`, `_analyze_high_errors.py`, `_analyze_cand_mapping.py`
- ตรวจ ECT refs: `_check_z2_bn.py`, `_check_z2_ect.py`, `_check_ect_cands.py`, `_check_ect_ref.py`

**ค้นพบสำคัญ:**
- เขต 2: Combined PDF interleaved pages → duplicates → ต้อง dedup R0d
- เขต 3, 7: PDF coverage gaps — ไม่ใช่ OCR error แต่ไม่มี PDF ต้นทาง
- เขต 7: ไฟล์ undercount (ต.หนองขาม, ต.ท่ามะไฟหวาน) — re-OCR ช่วยได้บางส่วน

---

## Phase 14: Postprocessing Pipeline
### 9 มีนาคม 2569 (วันที่ 26 ตอนค่ำ–ดึก)

**เป้าหมาย:** สร้าง comprehensive postprocessing pipeline

**สิ่งที่ทำ:**
- พัฒนา `postprocess_chaiyaphum.py` — 9 กฎแก้ไข:
  - **R0a** fix_metadata_from_filepath: ดึง constituency/province/vote_type จาก filename
  - **R0b** fix_station_no_from_filepath: ดึง station_no จาก filename
  - **R0c** dedup_records: ลบ exact duplicates
  - **R0d** dedup_interleaved: ลบ interleaved combined-file duplicates
  - **R3** fix_total_votes: แก้ผลรวมคะแนน
  - **R4** fix_remaining_ballots: แก้บัตรเหลือ
  - **R5** fix_negative_values: แก้ค่าติดลบ
  - **R6** fix_outliers: ตัดค่าผิดปกติ
  - **R7** normalize_candidates: จับคู่ผู้สมัครกับ ECT reference + **name-matching fallback**
  - **R8** flag_turnout: flag records ที่ turnout > registered_voters
  - **R9** fix_candidate_vote_outliers: ตัดคะแนนผู้สมัครที่เกิน valid_ballots
  - cross_validate_killernay: เปรียบเทียบกับ ground truth
  - revalidate: ตรวจสอบหลังแก้ไข

**ผลลัพธ์:**
- Avg error: **11.4%** (จาก 40.3%)
- HIGH error records: **10**
- `postprocess_stats_chaiyaphum.json` — สถิติการแก้ไขทุกกฎ

---

## Phase 15: Name-Matching + Generalize Pipeline
### 10 มีนาคม 2569 (วันที่ 27 เช้า)

**เป้าหมาย:** ปรับปรุง candidate matching และทำให้ pipeline ใช้ได้ทุกจังหวัด

**สิ่งที่ทำ:**
- วิเคราะห์ name reclassification: `_analyze_name_reclass.py`, `_analyze_name_reclass2.py`
- **พัฒนา `postprocess.py`** — Generalized pipeline:
  - รับ `--province` argument
  - Dynamic load: OCR records, Killernay ground truth, ECT reference
  - Province-specific filenames
  - `PROVINCE_NAMES` mapping, `KILLERNAY_NAME_OVERRIDES`
  - แก้ bug: `vote_type` เป็น `None` ในข้อมูลตาก (TypeError fix)
- ทดสอบกับ ชัยภูมิ → ผลเหมือนกัน (avg error 11.4%)
- ทดสอบกับ ตาก → 26.6% avg error (ใช้ได้ — ข้อมูลแค่ 36%)

---

## Phase 16: Review UI Improvements
### 10 มีนาคม 2569 (วันที่ 27 บ่าย–ค่ำ)

**เป้าหมาย:** ปรับปรุง Review UI ทั้งสองเวอร์ชัน

### Static Citizen Review (`docs/review/`)
- เพิ่ม **CSV export** 2 แบบ: summary + constituency+candidates
- เพิ่ม **export dropdown menu** (JSON/CSV สรุป/CSV แบ่งเขต)
- เพิ่ม **stats panel** แสดงสถิติต่อจังหวัด/เขต
- ปรับปรุง `prepare_citizen_data.py`:
  - Auto-discover provinces (ไม่ hardcode)
  - สร้าง `manifest.json` สำหรับ dynamic loading
  - กรอง test files ออก

### React Review App (`review-app/`, port 3000)
- เพิ่ม **export dropdown** 3 ตัวเลือก:
  - 📄 JSON (ข้อมูล + review)
  - 📊 CSV สรุปทั้งหมด
  - 📋 CSV แบ่งเขต + ผู้สมัคร (dynamic candidate columns)
- เพิ่ม **DataStatsPanel** component:
  - สถิติต่อจังหวัด: รวม/แบ่งเขต/บัญชีรายชื่อ/มีผู้สมัคร/ตรวจแล้ว/มีปัญหา
  - ตารางต่อเขต: จำนวน records, stations unique
  - Collapsible panel
- เพิ่ม **Data Validation** system:
  - `validation.js` — 11 กฎตรวจสอบ:
    - V1: มาแสดงตน > ผู้มีสิทธิ (🔴 error)
    - V2: รวมคะแนน ≠ บัตรดี (🟡 warning)
    - V3: บัตรดี+เสีย+ไม่เลือก ≠ มาแสดงตน (🟡)
    - V4: บัตรเหลือติดลบ (🔴)
    - V5: บัตรที่ได้รับ ≠ มาแสดงตน+เหลือ (🟡)
    - V6: ผลรวมผู้สมัคร ≠ รวมคะแนน (🟡)
    - V7: ค่าติดลบ (🔴)
    - V8: ผู้มีสิทธิ > 10,000 (🟡)
    - V9: ไม่มีข้อมูลสถิติ (ℹ️)
    - V10: ผู้สมัครคะแนน > บัตรดี (🔴)
    - V11: จำนวนผู้สมัครไม่ตรง ECT (🟡)
  - **Warning panel** สีแดง/เหลือง/น้ำเงินบน ReviewCard
  - **Field-level highlighting** — ค่าที่มีปัญหา highlight เป็นสีแดง/เหลือง
  - **Filter**: 🔴 มีข้อผิดพลาด / 🟡 มีคำเตือน

---

## Phase 17: React Review App — Production Deploy
### 13–15 มีนาคม 2569 (วันที่ 30–32)

**เป้าหมาย:** Deploy React Review App ขึ้น GitHub Pages สำหรับใช้งานจริง

**สิ่งที่ทำ:**
- **Review App สมบูรณ์** (`da334d0`): รวม consensus fixes สำหรับเขต 1-2, 1-5, 1-7, 1-8
  - 10 React components: `ReviewCard`, `DataStatsPanel`, `FilterBar`, `StatsBar`, `CandidateTable`, `FieldRow`, `UploadPanel`, `AdminPanel`, `AuthGate`, `BackupDashboard`
  - Hooks: `useAuth.js` — Google Sign-In integration
  - Utils: `reviewLog.js` (424 lines), `submitReview.js`, `validation.js` (11 กฎ)
  - สร้าง package.json, vite.config.js, tailwind.config.js, postcss.config.js
- **GitHub Actions CI/CD** (`29f3e2b`):
  - สร้าง `.github/workflows/deploy.yml` — auto-build + deploy to GitHub Pages
  - เพิ่ม OG meta tags สำหรับ social sharing (Facebook, LINE, Twitter)
  - `index.html` เพิ่ม `<meta property="og:title">`, `og:description`, `og:image`
- **Auto-load data บน GitHub Pages** (`7914e92`, `9379975`):
  - แก้ bug: แสดง UploadPanel แทน error เมื่อไม่มี data file
  - สร้าง stripped `review_data.json` — 6,111 items, 99% มีรูปจาก Drive
  - App auto-fetch จาก `./data/review_data.json` เมื่อเปิดบน GitHub Pages
  - เพิ่ม `.gitignore` สำหรับ data files ขนาดใหญ่
- **แก้ไข Drive URLs + UX** (`55b1acc`):
  - เพิ่ม `pdf_url` สำหรับ 39 Vision OCR items ที่ขาด Drive link
  - ปรับปรุง no-image UX — แสดง placeholder แทนที่จะ error
- **Restore OCR text** (`df5ae6c`):
  - คืน `ocr_text` สำหรับ 667 Vision OCR items (เพิ่มขนาด data 24.4 MB)
  - ทำให้ผู้ตรวจสอบอ่าน raw OCR text เปรียบเทียบกับภาพได้

**ผลลัพธ์:**
- React Review App deploy บน GitHub Pages สำเร็จ
- 6,111 items พร้อมตรวจสอบ (3 จังหวัด: ชัยภูมิ, ตาก, เพชรบูรณ์)
- Auto-build ทุก push ไปยัง `main` branch

**Files ที่สร้าง/แก้ไข:**
- `.github/workflows/deploy.yml` — GitHub Actions workflow
- `review-app/public/data/review_data.json` — ข้อมูล 6,111 items
- `review-app/index.html` — OG meta tags
- `review-app/src/App.jsx` — auto-load logic

---

## Phase 18: PDF Split + Single-Page Upload
### 16–17 มีนาคม 2569 (วันที่ 33–34) ⚡ ทำงานข้ามคืน

**เป้าหมาย:** ตัด PDF หลายหน้าเป็นหน้าเดียว เพื่อแสดงถูกหน้าใน ReviewCard

**ปัญหาเดิม:**
- PDF จาก กกต. มักรวมหลายหน่วยเลือกตั้งในไฟล์เดียว (สูงสุด 10+ หน้า)
- ReviewCard แสดง PDF หน้าแรกเสมอ ไม่ตรงกับ record ที่กำลังตรวจ
- ผู้ตรวจสอบต้องเลื่อนหา PDF หน้าที่ถูกต้องเอง

**สิ่งที่ทำ:**
- ใช้ `scripts/split_and_upload.py` — ตัด PDF แต่ละหน้าเป็นไฟล์แยก แล้วอัปโหลดไป Google Drive
- **Batch processing** แบ่งเป็นหลาย batch ตาม commit:
  - Batch 1 (`4acc8da`): 167 items — เพชรบูรณ์ เริ่มต้น
  - Batch 2 (`874d653`): 397 items — ชัยภูมิ + เพชรบูรณ์
  - Batch 3 (`db519c4`): 737 items — ชัยภูมิ batch 2
  - Batch 4 (`1c804d2`): 905 items — ชัยภูมิ เขต 1 ครบ
  - Batch 5 (`0ac0a2f`): batch ใหญ่สุด
  - Batch 6 (`6d5d122`): 4,969/5,089 split done
  - Batch 7 (`21dba84`): 5,080/5,089 — เหลือ 9 items
  - Batch 8 (`9d8f884`): **5,089/5,089 ครบ 100%** ✅
- **PDF Status Panel** ใน `DataStatsPanel.jsx`:
  - เพิ่ม section แสดงสถิติ PDF: total, single-page, multi-page, max pages, max shared
  - Progress bar แสดงเปอร์เซ็นต์ที่ตัดแล้ว
  - Quality issues section — แสดงปัญหาคุณภาพข้อมูล

**ผลลัพธ์:**
- **5,089/5,089 items** ชี้ไปยัง single-page PDF บน Google Drive (100%)
- ผู้ตรวจสอบเห็น PDF หน้าที่ถูกต้องทันที ไม่ต้องเลื่อนหา
- `review_data.json` อัปเดตทั้ง `pdf_url` (single-page) และ `original_pdf_url` (เก็บ URL เดิม)

**Files ที่แก้ไข:**
- `review-app/public/data/review_data.json` — อัปเดต 8 ครั้ง
- `review-app/src/components/DataStatsPanel.jsx` — เพิ่ม PDF status panel + quality issues

---

## Phase 19: Anomaly Cross-Reference + Data Integrity
### 17 มีนาคม 2569 (วันที่ 34 กลางวัน)

**เป้าหมาย:** เชื่อมข้อมูลวิเคราะห์ความผิดปกติ กกต. เข้ากับ Review App + แก้ปัญหา data integrity

**สิ่งที่ทำ:**

### 19a. Cross-Reference Anomaly Flags (`3260a9b`)
- สร้าง `_build_anomaly_flags.py` — แปลง `anomaly_data.json` เป็น `anomaly_flags.json` สำหรับ React
  - 76 เขตที่ถูก flag จาก 400 เขตทั่วประเทศ
  - 5 หมวด: turnout ผิดปกติ, บัตรเสียสูง, ไม่ประสงค์ฯ สูง, คะแนนสูญเปล่า, ชนะขาดลอย
  - แต่ละ flag มี: severity (high/medium/low), flag text, ค่าสถิติ
- **ReviewCard** — เพิ่ม anomaly banner:
  - แสดง flag สำหรับเขตที่มีความผิดปกติ (จับคู่ province + constituency)
  - สี badge ตาม severity: 🚨 แดง (high), ⚠️ เหลือง (medium)
- **DataStatsPanel** — เพิ่ม anomaly summary section:
  - จำนวนเขตที่ถูก flag, flag ระดับสูง, แยกตามหมวด
  - แสดงเขตในข้อมูล OCR ที่ถูก flag พร้อม detail
  - ลิงก์ไปหน้า `anomaly.html` (วิเคราะห์ฉบับเต็ม)

### 19b. Fix Incomplete Data Flags (`3bbcfe8`)
- **ปัญหา:** ข้อมูล กกต. เป็น snapshot ขณะนับคะแนนยังไม่ครบ → turnout % ต่ำผิดปกติ
  - เช่น ชัยภูมิ เขต 3 นับแค่ 83% → turnout ดูต่ำ → ถูก flag เป็น anomaly
- **แก้ไข `_build_anomaly_flags.py`:**
  - คำนวณ `percent_counted` ต่อเขต จาก `total_vote_all / registered_vote`
  - **ตัด turnout flags ออก** เมื่อ `percent_counted < 90%` (ข้อมูลไม่ครบพอตัดสิน)
  - เพิ่ม `incomplete: true` + disclaimer ใน flags ที่เหลือจากเขตที่นับไม่ครบ
  - เพิ่ม metadata: `disclaimer`, `data_snapshot`, `total_units`
- **DataStatsPanel** — เพิ่ม disclaimer banner:
  - ⚠️ แจ้งว่าข้อมูลเป็น snapshot ไม่ใช่ผลสุดท้าย
  - แสดงเวลา snapshot
- **ReviewCard** — เพิ่ม incomplete indicator:
  - เมื่อ flag มี `incomplete: true` แสดง 📊 "ข้อมูลยังนับไม่ครบ"

### 19c. Fix anomaly.html 404 + Link Alignment (`ed2a592`)
- **ปัญหา:** ลิงก์ "ดูวิเคราะห์ฉบับเต็ม" กดแล้ว 404 เพราะ `anomaly.html` ไม่ได้ deploy
- **แก้ `.github/workflows/deploy.yml`:**
  - เพิ่ม step คัดลอก `anomaly.html` + `data/anomaly_data.json` เข้า `review-app/dist/` ก่อน deploy
- **แก้ link alignment:**
  - ReviewCard: ลบ `ml-auto` → ลิงก์ชิดซ้าย
  - ใช้ relative URL `./anomaly.html` แทน absolute path

**ผลลัพธ์:**
- 76 เขตที่ถูก flag แสดงบน ReviewCard + DataStatsPanel
- ตัด turnout flags ที่ไม่น่าเชื่อถือออก (เขตนับ < 90%)
- Disclaimer แจ้งผู้ใช้ว่าข้อมูลเป็น snapshot
- `anomaly.html` เปิดได้จาก GitHub Pages

**Files ที่สร้าง/แก้ไข:**
- `_build_anomaly_flags.py` — สร้างใหม่ (95 lines)
- `review-app/public/data/anomaly_flags.json` — 17KB, 76 เขต
- `review-app/src/App.jsx` — load anomaly data + pass props
- `review-app/src/components/DataStatsPanel.jsx` — anomaly summary + disclaimer
- `review-app/src/components/ReviewCard.jsx` — anomaly banner + incomplete indicator
- `.github/workflows/deploy.yml` — copy anomaly files to dist

---

## Phase 20: ECT Backup Dashboard Integration
### 17 มีนาคม 2569 (วันที่ 34 ค่ำ)

**เป้าหมาย:** รวม ECT Backup Dashboard (Python server port 8899) เข้ากับ React Review App

**ปัญหาเดิม:**
- Dashboard สถานะ Google Drive Backup (`scripts/dashboard.py`) ทำงานเป็น Python HTTP server บน port 8899
- ต้องรัน Python server แยกต่างหาก ใช้งานไม่สะดวก
- ข้อมูลดึง real-time จาก Google Drive API — ต้องมี credentials

**สิ่งที่ทำ:**

### 20a. Extract Dashboard Data to Static JSON
- สร้าง `_extract_dashboard.py` — แปลง dynamic dashboard data เป็น static JSON:
  - อ่าน `data/dashboard_cache.json` (Google Drive scan cache)
  - อ่าน `data/backup_progress.json` (progress tracking)
  - Merge ข้อมูล 77 จังหวัด: ชื่อ, PDF จำนวนจริง, จำนวนคาดหวัง, สถานะ, เปอร์เซ็นต์
  - คำนวณ summary: total, has_data, complete, total_actual, total_expected, pct
  - Output: `review-app/public/data/backup_status.json` (12.4 KB)
- ผลลัพธ์: **77 จังหวัด, 149,936 PDFs, ครบ 100%**

### 20b. Create BackupDashboard React Component
- สร้าง `BackupDashboard.jsx` (198 lines):
  - **Summary Cards**: มีข้อมูล, ครบ 100%, PDF ทั้งหมด, ความคืบหน้า
  - **Overall Progress Bar**: gradient bar แสดงเปอร์เซ็นต์รวม
  - **Province Table**: 77 จังหวัด พร้อม:
    - Badge สถานะ: ✅ ครบ / 📂 มีข้อมูล / ⏳ รอ
    - PDF count (actual vs expected)
    - Progress bar ต่อจังหวัด
  - **Search**: ค้นหาจังหวัดได้
  - **Collapsible**: เปิด/ปิด section ได้

### 20c. Integrate into Review App (`2036a8f`)
- Import `BackupDashboard` ใน `App.jsx`
- วาง component ใต้ `DataStatsPanel` เป็นแถบ "ECT Backup — Google Drive"
- ไม่ต้องรัน Python server port 8899 อีกต่อไป

**ผลลัพธ์:**
- Dashboard สถานะ backup ใช้งานได้บน GitHub Pages โดยไม่ต้อง backend
- ข้อมูล static JSON — โหลดเร็ว ไม่ต้องมี Google Drive credentials

**Files ที่สร้าง:**
- `_extract_dashboard.py` — extraction script (106 lines)
- `review-app/public/data/backup_status.json` — static data (12.4 KB, 77 จังหวัด)
- `review-app/src/components/BackupDashboard.jsx` — React component (198 lines)

---

## Phase 21: UI/UX Polish, Testing & Documentation
### 19 มีนาคม 2569 (วันที่ 36)

**เป้าหมาย:** ปรับปรุง UI/UX, เพิ่ม error handling, เขียน tests, เอกสารความปลอดภัย

**สิ่งที่ทำ:**

### 21a. Documentation & Security
- สร้าง `.env.example` — ระบุ environment variables ที่จำเป็นทั้งหมด
- เขียน `README.md` ใหม่ทั้งหมด — ครอบคลุม architecture, setup, usage
- สร้าง `SECURITY.md` — คู่มือจัดการ API keys, Google Cloud Console settings, emergency response

### 21b. Error Boundary
- สร้าง `ErrorBoundary.jsx` — React Error Boundary component (75 lines)
  - Full-page และ compact fallback UI
  - ปุ่ม retry + แสดง technical details
- Wrap ที่ `main.jsx` (top-level), `ReviewCard`, `DataStatsPanel`, `BackupDashboard`
- UI crash ใน component เดียวไม่ทำให้ทั้ง app พัง

### 21c. ReviewCard Improvements
- เพิ่ม **PDF loading skeleton** — spinner overlay ขณะ iframe โหลด
- State `pdfLoading` + `onLoad` callback บน iframe

### 21d. Keyboard Shortcuts
- `J/K` หรือ `←/→` — navigate ระหว่าง items
- `1/2/3/R` — set review status (confirmed/flagged/rejected/reset)
- `Escape` — blur active input เพื่อให้ shortcuts ทำงานอีกครั้ง
- Footer แสดง hint ของ shortcuts ทั้งหมด

### 21e. DataStatsPanel Enhancement
- เพิ่ม **ProgressRing** SVG component — วงกลมแสดง % ความคืบหน้า
- ปรับ responsive grid layout สำหรับ stat cards

### 21f. BackupDashboard Enhancement
- เพิ่ม **sortable columns** — คลิก header เพื่อเรียงตาม ชื่อ/สถานะ/PDF/คาดหวัง/คืบหน้า
- `SortTh` component พร้อม ArrowUp/ArrowDown/ArrowUpDown icons
- Wrap ด้วย `ErrorBoundary`

### 21g. Performance Optimization
- `React.memo` บน `FilterBar` และ `StatsBar` — ลด unnecessary re-renders
- `useMemo` / `useCallback` ครอบคลุมอยู่แล้วใน App.jsx

### 21h. Unit Tests
- ติดตั้ง **Vitest** เป็น test framework
- `validation.test.js` — 18 tests ครอบคลุม V1–V11 rules + edge cases
- `reviewLog.test.js` — 19 tests ครอบคลุม validateEditValue, getItemSummary, verifyLogIntegrity, getUserReviewKey
- **ผลลัพธ์: 37/37 tests passed**

**Files ที่สร้าง/แก้ไข:**
- `.env.example`, `README.md`, `SECURITY.md`
- `review-app/src/components/ErrorBoundary.jsx` (new, 75 lines)
- `review-app/src/components/ReviewCard.jsx` (loading skeleton, ErrorBoundary wrap)
- `review-app/src/components/DataStatsPanel.jsx` (ProgressRing, ErrorBoundary wrap)
- `review-app/src/components/BackupDashboard.jsx` (sortable table, ErrorBoundary wrap)
- `review-app/src/components/FilterBar.jsx` (React.memo)
- `review-app/src/components/StatsBar.jsx` (React.memo)
- `review-app/src/App.jsx` (keyboard shortcuts, Escape key)
- `review-app/src/main.jsx` (top-level ErrorBoundary)
- `review-app/src/utils/validation.test.js` (new, 18 tests)
- `review-app/src/utils/reviewLog.test.js` (new, 19 tests)
- `review-app/package.json` (vitest, test scripts)

---

## Phase 22: Data & Analytics Dashboards
### 19 มีนาคม 2569 (วันที่ 36)

**เป้าหมาย:** เพิ่ม dashboard วิเคราะห์ข้อมูล, heatmap จังหวัด, leaderboard ผู้ตรวจ, export เฉพาะ filtered, cross-reference OCR vs ECT

**สิ่งที่ทำ:**

### 22a. Analytics Dashboard (AnalyticsDashboard.jsx)
- **Donut Chart** (pure SVG) แสดงสถานะ review: รอตรวจ/ยืนยัน/ตรวจซ้ำ/ใช้ไม่ได้
- **Summary Cards** — จำนวนแต่ละสถานะ + เวลาเฉลี่ยต่อหน้า
- **Validation Bar Chart** — กราฟแท่งแสดงจำนวน error/warning ต่อ rule (V1–V11)
- **Review Timeline** — bar chart 7 วันล่าสุด จาก reviewLog
- **Province Progress** — horizontal bar chart แสดง % ตรวจต่อจังหวัด
- **Constituency Error Ranking** — เขตที่มี error มากที่สุด
- Collapsible panel, แสดง % ตรวจแล้วในหัวข้อ

### 22b. Province Review Heatmap (ProvinceHeatmap.jsx)
- Grid-based heatmap จัดเรียงจังหวัดตามภูมิศาสตร์คร่าวๆ
- สีตาม % ความคืบหน้า: เขียว (100%) → แดง (<25%)
- Hover แสดง detail: ยืนยัน/ตรวจซ้ำ/ใช้ไม่ได้/รอตรวจ
- รองรับจังหวัดที่ไม่อยู่ใน grid (แสดงแยกด้านล่าง)

### 22c. Reviewer Leaderboard (ReviewerLeaderboard.jsx)
- ตารางสถิติผู้ตรวจ: ✅ ยืนยัน, 🔄 ตรวจซ้ำ, 🚫 ใช้ไม่ได้, ✏️ แก้ไข
- เรียงได้ตาม: จำนวน review, ความเร็วเฉลี่ย, จำนวนแก้ไข
- เหรียญ 🥇🥈🥉 สำหรับ top 3
- แสดงเวลาเฉลี่ยต่อหน้า (วินาที) + เวลาทำงานรวม
- คำนวณจาก reviewLog timestamps

### 22d. Filtered Export
- เพิ่ม **"เฉพาะที่กรอง"** section ใน Export dropdown menu
- `handleExportFilteredJSON` — export เฉพาะ filteredItems เป็น JSON พร้อม review status
- `handleExportFilteredCSV` — export เฉพาะ filteredItems เป็น CSV (UTF-8 BOM)
- แสดงจำนวนรายการที่กรองใน menu header

### 22e. Cross-Reference Panel (CrossReferencePanel.jsx)
- ตารางเปรียบเทียบ OCR vs ECT ต่อเขตเลือกตั้ง
- แสดง: จังหวัด, เขต, จำนวนหน่วย, OCR Turnout, OCR Valid, Errors, ECT Flags, Review %
- Filter ตาม severity: Error / Warning / OK
- Sortable columns ทุกคอลัมน์
- Pagination (20 แถวต่อหน้า)
- Severity badge สีตามระดับ

**ผลการ Build:**
- `npm run build` ✅ — 312 KB JS bundle (gzip 88 KB)
- `npm test` ✅ — 37/37 tests passed
- ไม่มี dependency ใหม่ — ใช้ pure SVG charts ทั้งหมด

**Files ที่สร้าง/แก้ไข:**
- `review-app/src/components/AnalyticsDashboard.jsx` (new, ~250 lines)
- `review-app/src/components/ProvinceHeatmap.jsx` (new, ~190 lines)
- `review-app/src/components/ReviewerLeaderboard.jsx` (new, ~170 lines)
- `review-app/src/components/CrossReferencePanel.jsx` (new, ~240 lines)
- `review-app/src/App.jsx` (imports, filtered export handlers, component wiring)

---

## Phase 23: Cross-Reference 4 แหล่งข้อมูล
**วันที่:** 19 มีนาคม 2569  
**เป้าหมาย:** อัปเกรด Cross-Reference Panel ให้เปรียบเทียบข้อมูลจาก 4 แหล่งพร้อมกัน (OCR / กกต. / Killernay / Luengnat)

**ปัญหาเดิม:**
- CrossReferencePanel เดิมเปรียบเทียบเฉพาะ OCR vs ECT flags
- ไม่มี visual comparison ระหว่าง Killernay และ Luengnat
- ข้อมูลแต่ละแหล่งอยู่คนละ format (JSON, CSV, API)

**สิ่งที่ทำ:**
1. สร้าง `scripts/prepare_cross_reference.py` — merge ข้อมูลจาก 3 แหล่ง:
   - ECT official (`ect_stats_cons.json` + `ect_provinces.json`) → 400 เขต
   - Killernay (`killernay_summary_winners.csv`) → 387 เขต
   - Luengnat → placeholder (ข้อมูลยังไม่พร้อม)
2. Output: `review-app/public/data/cross_reference_sources.json` (403 KB, 401 records)
3. เขียน CrossReferencePanel ใหม่ทั้งหมด:
   - **Source status cards** — แสดงสถานะ 4 แหล่ง (Live/พร้อม/รอข้อมูล)
   - **4-column turnout comparison** — OCR / กกต. / Killernay / Luengnat
   - **Max Diff %** — คำนวณ cross-source difference สูงสุด
   - **Severity classification** — Error (>10%), Warning (>3%), Mismatch (>0.5%), OK
   - **Table + Cards view** — สลับมุมมองได้
   - **Detail panel** — คลิกแถวเพื่อดู bar chart เปรียบเทียบ 4 แหล่ง
   - **Killernay winner info** — แสดงผู้ชนะ, พรรค, คะแนน, ผู้มีสิทธิ
   - **Lazy loading** — โหลด cross-ref JSON เมื่อ expand เท่านั้น

**ผลลัพธ์:**
- 401 เขตเลือกตั้งเปรียบเทียบได้
- ECT: 400 เขต, Killernay: 387 เขต, OCR: live data
- Visual diff bars สีตาม severity (แดง >10%, ส้ม >3%)
- Build สำเร็จ, ขนาดไม่เพิ่มมาก (lazy load JSON)

**Files ที่สร้าง/แก้ไข:**
- `scripts/prepare_cross_reference.py` (new, ~200 lines)
- `review-app/public/data/cross_reference_sources.json` (generated, 403 KB)
- `review-app/src/components/CrossReferencePanel.jsx` (rewritten, ~520 lines)

---

## Phase 24: ProvinceHeatmap — SVG Choropleth Map
### 20–21 มีนาคม 2569 (วันที่ 37–38)

**เป้าหมาย:** เปลี่ยนแผนที่จังหวัดจากตารางกริดเป็นแผนที่ประเทศไทยจริง (SVG choropleth)

**ปัญหาเดิม:**
- `ProvinceHeatmap.jsx` แสดงเป็นตาราง grid สี่เหลี่ยมเล็กๆ เรียงกัน
- ไม่ตรงกับรูปทรงประเทศไทยจริง ทำให้ผู้ใช้หาจังหวัดลำบาก
- ไม่มี interactive hover หรือ tooltip

**สิ่งที่ทำ:**

### 24a. Rewrite ProvinceHeatmap.jsx — SVG Choropleth
- **ลบโค้ดเดิม** (grid-based) เขียนใหม่ทั้งหมด (~450 lines)
- **TopoJSON loading** — ดึง `thailand-provinces.topojson` (~4.5MB) แบบ lazy-load เมื่อกดเปิดแผง
- **D3-geo projection** — ใช้ `geoMercator().fitSize()` ปรับขนาดแผนที่ให้พอดี SVG อัตโนมัติ
- **Province coloring** — ชุดสีตาม % ความคืบหน้า:
  - เขียว emerald (100%) → เหลือง amber (50-99%) → แดง red (<25%) → เทา gray (ไม่มีข้อมูล)
  - สีน้ำเงิน indigo — มีข้อมูลแต่ยังไม่ได้ตรวจ (0%)
- **Interactive hover** — จังหวัดเปลี่ยนสี indigo เมื่อชี้เมาส์ + floating tooltip:
  - สถิติละเอียด: ทั้งหมด, ยืนยัน, ตรวจซ้ำ, ใช้ไม่ได้, รอตรวจ
  - Progress bar ใน tooltip
- **Right panel** — Legend, summary cards 3 ใบ, รายชื่อจังหวัดเรียงตาม % (scroll ได้, hover sync กับแผนที่)
- **EN→TH mapping** — ครอบคลุม 77 จังหวัด + `SHORT_NAMES` สำหรับ label บนแผนที่
- **SKIP_FEATURES** — กรองทะเลสาบ/เกาะที่ไม่ต้องการออก
- **Error/loading states** — spinner ขณะโหลด, error message เมื่อล้มเหลว

### 24b. Dependencies + Asset ใหม่
- เพิ่ม `topojson-client` — แปลง TopoJSON → GeoJSON features
- `d3-geo` — map projection + SVG path generation (มีอยู่แล้ว)
- `review-app/public/thailand-provinces.topojson` (~4.5MB) — ขอบเขตจังหวัด 77 จังหวัด

### 24c. Iterative Improvements
- **ขยายแผนที่ 3-4x** — `MAP_W = 1600`, `MAP_H = 2000` เพื่อให้อ่านง่ายขึ้น
- **เพิ่ม province labels** พร้อมสถิติบนแผนที่ — ใช้ `geoCentroid` หาตำแหน่งกลางจังหวัด
- **ปรับสีให้สดใสขึ้น** — vivid color scheme
- **Default expanded = true** — แผนที่แสดงทันทีเมื่อเปิด
- **แยกสี "มีข้อมูลแต่ 0%"** (indigo) กับ **"ไม่มีข้อมูล"** (gray) ให้ชัดเจน

**ผลลัพธ์:**
- แผนที่ประเทศไทยจริงแสดงความคืบหน้าการตรวจสอบแต่ละจังหวัด
- Hover interactive + tooltip + sync กับรายชื่อจังหวัด
- Build ผ่านเรียบร้อย

**Files ที่สร้าง/แก้ไข:**
- `review-app/src/components/ProvinceHeatmap.jsx` (rewritten, ~450 lines)
- `review-app/public/thailand-provinces.topojson` (new, ~4.5MB)
- `review-app/package.json` (เพิ่ม `topojson-client`)

---

## Phase 25: BackupDashboard — Thailand Map + Enhanced Visualization
### 21 มีนาคม 2569 (วันที่ 38)

**เป้าหมาย:** เพิ่มแผนที่ประเทศไทยแสดงคุณภาพข้อมูล backup ใน BackupDashboard

**ปัญหาเดิม:**
- `BackupDashboard.jsx` แสดงเฉพาะตารางจังหวัด ไม่มี visual map
- ไม่เห็นภาพรวมว่าจังหวัดไหนมีข้อมูลครบ/ไม่ครบ

**สิ่งที่ทำ:**

### 25a. Thailand Map ใน BackupDashboard
- **เพิ่ม imports**: `d3-geo` (`geoMercator`, `geoPath`), `topojson-client` (`feature`), `useCallback`, `useRef`
- **EN_TO_TH mapping** — 77 จังหวัด (เหมือน ProvinceHeatmap แต่ specific สำหรับ backup)
- **SHORT_NAMES** — ชื่อย่อจังหวัดสำหรับ label บนแผนที่
- **SKIP_FEATURES** — กรอง features ที่ไม่ต้องการ
- **Backup-specific color functions:**
  - `getBackupFill(prov)` — สีพื้นตาม % backup (emerald 100%, lime 80-99%, amber 50-79%, red <50%, gray ไม่มีข้อมูล)
  - `getBackupStroke(prov)` — สีขอบจังหวัด
  - `getBackupLabelColor(prov)` — สีตัวอักษร label
- **MAP dimensions** — `MAP_W = 1600`, `MAP_H = 2000`

### 25b. Map Features
- **Map-related state** — TopoJSON loading, `provMap` lookup, projection, mouse handler
- **Province labels** — ชื่อจังหวัด + สถิติ (actual/expected) บนแผนที่
- **Floating tooltip** — แสดงรายละเอียด backup ของจังหวัดที่ชี้เมาส์
- **Legend panel** — อธิบายความหมายของสี
- **Summary stats** — การ์ดสรุปสถานะ backup
- **Watermark** — "Backup ข้อมูล กกต." บนแผนที่

### 25c. วางตำแหน่งบน UI
- แผนที่วางระหว่าง progress bar กับตารางจังหวัด
- LazyLoad — โหลด TopoJSON เมื่อ expand เท่านั้น

**ผลลัพธ์:**
- แผนที่ประเทศไทยแสดงคุณภาพ backup data 77 จังหวัด
- Hover interactive + tooltip + province labels
- Build ผ่านเรียบร้อย

**Files ที่แก้ไข:**
- `review-app/src/components/BackupDashboard.jsx` (เพิ่ม ~350 lines — map section)

---

## Phase 26: UX Improvements — Confirmations, Help, Import/Export Info
### 21–22 มีนาคม 2569 (วันที่ 38–39)

**เป้าหมาย:** ปรับปรุง UX ป้องกันการกดผิด + เพิ่มคำอธิบายช่วยเหลือ

**สิ่งที่ทำ:**

### 26a. ReviewCard — Confirmation Modals
- เพิ่ม **confirmation modal** สำหรับทุก review status:
  - ✅ ยืนยัน — "ตรวจสอบตัวเลขกับภาพต้นฉบับแล้ว ถูกต้อง"
  - 🔄 ตรวจอีกรอบ — "ไม่แน่ใจ ส่งให้คนอื่นตรวจอีกรอบ"
  - 🚫 ใช้ไม่ได้ — "PDF เบลอ/ไม่ตรง/อ่านไม่ออก"
  - ↩ รีเซ็ต — "สถานะจะกลับเป็นรอตรวจ"
- Modal แสดง **คำอธิบายละเอียด** + **ปุ่มยืนยัน/ยกเลิก** สีตาม status
- ป้องกันการกด status เปลี่ยนโดยไม่ตั้งใจ

### 26b. Keyboard Shortcuts — Confirmation Dialogs
- ปุ่ม `1` (ยืนยัน) และ `R` (รีเซ็ต) แสดง `window.confirm()` ก่อนเปลี่ยน status
- ข้อความ confirm ตรงกับ modal — ภาษาไทยอธิบายผลกระทบ

### 26c. UploadPanel — Collapsible Help Section
- เพิ่ม section **คู่มือใช้งาน** (collapsible) ด้านบน UploadPanel:
  - อธิบายวัตถุประสงค์ของ Upload Panel
  - ขั้นตอนการใช้งาน (5 ขั้นตอน)
  - ไฟล์ที่รองรับ (JSON, CSV)
  - คำเตือนเรื่องข้อมูลซ้ำ

### 26d. App.jsx — Import Info Modal + Export Descriptions
- **Import Info Modal** — กดปุ่ม Import แสดง modal อธิบายก่อนเลือกไฟล์:
  - วิธีใช้งาน
  - ไฟล์ที่รองรับ
  - คำเตือน (ข้อมูลจะถูกรวมเข้า ไม่ใช่แทนที่)
- **Export Dropdown** — เพิ่มคำอธิบายละเอียดสำหรับแต่ละตัวเลือก export:
  - 📄 JSON — ข้อมูลดิบ + สถานะ review
  - 📊 CSV สรุป — เปิดด้วย Excel ได้
  - 📋 CSV แบ่งเขต — รวมคะแนนผู้สมัคร
  - 🔍 JSON/CSV เฉพาะที่กรอง — export เฉพาะรายการที่แสดงอยู่
- เพิ่ม `showImportInfo` state สำหรับ modal

**ผลลัพธ์:**
- ผู้ใช้ต้องยืนยันก่อนเปลี่ยน review status — ป้องกันกดผิด
- คำอธิบายช่วยเหลือครบทุกจุดสำคัญ
- Build ผ่านเรียบร้อย

**Files ที่แก้ไข:**
- `review-app/src/components/ReviewCard.jsx` (confirmation modals)
- `review-app/src/components/UploadPanel.jsx` (help section, ~65 lines)
- `review-app/src/App.jsx` (Import modal, Export descriptions, keyboard confirms)

---

## Phase 27: Google Drive Links + Progress >100% Explanation
### 22 มีนาคม 2569 (วันที่ 39)

**เป้าหมาย:** เพิ่มลิงก์ Google Drive ใน BackupDashboard + อธิบายความคืบหน้าเกิน 100%

**สิ่งที่ทำ:**

### 27a. Google Drive Links — 4 จุด
เพิ่ม `DRIVE_URL` constant + ลิงก์คลิกได้ 4 ตำแหน่ง:
1. **Header button text** — "Backup ข้อมูล กกต." คลิกไปหน้า Google Drive
2. **Progress bar label** — "%% completed" คลิกได้
3. **Map watermark** — "Backup ข้อมูล กกต." บนแผนที่คลิกได้
4. **Province table header** — ลิงก์ไป Google Drive

ใช้ `e.stopPropagation()` บน header link เพื่อไม่ให้กระทบ collapse/expand

### 27b. เปลี่ยน Label — 2 จุด
- "ECT Backup" → **"Backup ข้อมูล กกต."** ที่ header button + map watermark

### 27c. อธิบาย Progress >100%
- **Summary Card** — เพิ่มข้อความ sub อธิบายว่าทำไม % เกิน 100 ("PDF จริงมากกว่าที่คาดไว้")
- **Progress Bar** — เพิ่ม **amber badge** เมื่อ pct > 100:
  ```
  ⚠️ เกิน 100% — PDF จริง (149,936) มากกว่าที่คาดไว้ (147,603)
  ```
  - สไตล์: `bg-amber-50 text-amber-700 border-amber-200 rounded-md`
- **Province Table** — แถวที่ >100% แสดง `⚠️` + สีส้ม amber

### 27d. ปรับปรุง Icon Visibility
- **ก่อน:** ⓘ icon เล็กมาก อ่านไม่ออก
- **หลัง:** amber badge ขนาดใหญ่ พร้อม emoji ⚠️ + ข้อความอธิบายเต็ม
- ใช้ `inline-flex items-center gap-1` สำหรับจัดวาง

**ผลลัพธ์:**
- ลิงก์ Google Drive คลิกได้ 4 จุด — เข้าถึงข้อมูลต้นทางได้ทันที
- อธิบาย >100% ชัดเจนทั้ง progress bar, summary card, และ table
- Build ผ่านเรียบร้อย

**Files ที่แก้ไข:**
- `review-app/src/components/BackupDashboard.jsx` (DRIVE_URL, links, labels, amber badges)

---

## Phase 28: README v4.0 — Comprehensive Update
### 22 มีนาคม 2569 (วันที่ 39)

**เป้าหมาย:** อัปเดต README ให้ครบถ้วน โดยศึกษาจาก Killernay และ Luengnat READMEs

**ปัญหาเดิม:**
- README v3 ขาดหัวข้อสำคัญหลายอย่างที่ Killernay มี (disclaimer, attribution, QA, data source)
- ไม่มีข้อมูล cross-reference 4 แหล่ง
- ไม่มีตารางเปรียบเทียบ 3 โครงการ
- ไม่ได้เน้นจุดเด่น station-level OCR

**สิ่งที่ทำ:**

### 28a. ศึกษา README ของโครงการอื่น
- อ่าน **Killernay** README — 776 PDFs, สส.6/1, QA 8 ขั้นตอน, pipeline diagram, disclaimer (EN+TH)
- อ่าน **Luengnat** README — Data sources, site link, operations manual, security hygiene

### 28b. เพิ่มหัวข้อใหม่ (9 หัวข้อ)

| หัวข้อใหม่ | ได้แรงบันดาลใจจาก | รายละเอียด |
|---|---|---|
| **⚠️ Disclaimer (EN + TH)** | Killernay | อาสาสมัครภาคประชาชน, ไม่เกี่ยวข้องพรรคการเมือง, ทุนส่วนตัว |
| **📊 Data Coverage** | Killernay | ตารางสถิติสำคัญ 10 รายการ + ตารางเปรียบเทียบ 3 โครงการ |
| **⚠️ PDF Source Quality Issues** | Killernay | ลายมือเขียน, คุณภาพสแกน, หลายหน่วยต่อไฟล์, ชื่อไฟล์ไม่ตรง |
| **🔗 Cross-Reference** | ทั้งสอง | เปรียบเทียบ 4 แหล่ง (OCR/กกต./Killernay/Luengnat), 401 เขต |
| **🛠️ Processing Pipeline** | Killernay | แผนผัง ASCII ภาษาไทย ครบทุกขั้นตอน |
| **🔍 Quality Assurance** | Killernay | QA 4 ด้าน (multi-model, pipeline 9 กฎ, anomaly 8 มิติ, cross-ref) + known limitations |
| **📄 Data Source** | Killernay | ลิงก์แหล่งข้อมูลต้นฉบับทั้ง 5 แหล่ง |
| **📌 Attribution** | Killernay | วิธีให้เครดิต (EN + TH) |
| **🐛 Found an Error?** | Killernay | ลิงก์ GitHub Issues |

### 28c. ปรับปรุงหัวข้อเดิม
- **Title** — เพิ่มชื่อภาษาไทย "ระบบตรวจสอบผลเลือกตั้ง 2569"
- **Description** — เพิ่มภาษาไทย + mention Killernay/Luengnat
- **Links** — เพิ่ม Google Drive link ด้านบนสุด
- **Project Structure** — เพิ่ม `CrossReferencePanel.jsx`, `ProvinceHeatmap.jsx`, `cross_reference_sources.json`, `thailand-provinces.topojson`
- **Tech Stack** — เพิ่ม Maps row (TopoJSON, d3-geo)
- **Key Features** — เพิ่ม Cross-Reference Panel, Thailand choropleth map, dynamic prompts
- **Related Projects** — ขยายเป็น 5 คอลัมน์ (+ Description, Link)
- **License** — เพิ่มข้อความอธิบายเกี่ยวกับเอกสารรัฐ

**ผลลัพธ์:**
- README v4.0 — สองภาษา (EN + TH) ตลอดทั้งเอกสาร
- เน้นจุดเด่น station-level OCR — เป็นโครงการเดียวที่ OCR ระดับหน่วย
- ครบถ้วนตามมาตรฐาน: disclaimer, data coverage, QA, attribution, contact, license
- Version 4.0, วันที่ 22 มีนาคม 2569

**Files ที่แก้ไข:**
- `README.md` (rewritten, ~412 lines)

---

## Phase 29: Refactor, Testing, Dark Mode & Code Splitting
### 23 มีนาคม 2569 (วันที่ 40)

**เป้าหมาย:** ปรับปรุงคุณภาพ codebase — ลด code ซ้ำ, เพิ่ม test coverage, รองรับ dark mode, และ optimize performance

### 29a. Extract Shared Map Hook (`useThailandMap.js`)

**ปัญหาเดิม:** `ProvinceHeatmap.jsx` และ `BackupDashboard.jsx` มี code ซ้ำกันมาก — province name mappings, TopoJSON loading, d3-geo projection, mouse event handlers

**สิ่งที่ทำ:**
- สร้าง `src/hooks/useThailandMap.js` — reusable hook รวม:
  - `EN_TO_TH` province name mapping (77 จังหวัด)
  - `SHORT_NAMES` สำหรับ label บนแผนที่
  - `SKIP_FEATURES` สำหรับกรอง lake features ออก
  - `MAP_WIDTH` / `MAP_HEIGHT` constants
  - TopoJSON loading + error handling
  - d3 `geoMercator` projection + `geoPath` generator
  - Mouse event handlers สำหรับ tooltip positioning
  - `resolveThaiName()` — resolve English → Thai พร้อม alias override
- Refactor `ProvinceHeatmap.jsx` — ใช้ hook + `HEATMAP_ALIAS` สำหรับ Bangkok/Ayutthaya
- Refactor `BackupDashboard.jsx` — ใช้ hook, แทนที่ `EN_TO_TH` ทั้งหมดด้วย `resolveThaiName`

**ผลลัพธ์:**
- ลด code ซ้ำ ~200 บรรทัด
- Province mappings อยู่ที่เดียว — แก้ครั้งเดียวใช้ได้ทุกที่

### 29b. Unit Tests (37 → 67 tests)

**สิ่งที่ทำ:**
- สร้าง `src/hooks/useThailandMap.test.js` — 18 tests:
  - EN_TO_TH mapping ครบ 77 จังหวัด
  - SHORT_NAMES ไม่เกิน 8 ตัวอักษร
  - SKIP_FEATURES มี lake features
  - MAP_WIDTH / MAP_HEIGHT ค่าถูกต้อง
- ขยาย `src/utils/reviewLog.test.js` — เพิ่ม 31 tests:
  - `computeAnomalyScore` — rapid reviews, same-IP, conflicting status
  - `getAllAnomalyScores` — batch scoring
  - `getAllSummaries` — summary aggregation
  - `mergeReviewLogs` — merge + dedup + integrity verification

**ผลลัพธ์:**
- **67 tests ผ่านทั้งหมด** (จาก 37 เดิม — เพิ่ม 81%)
- Coverage ครอบคลุม hooks, validation, และ review log utilities

### 29c. Dark Mode Support

**สิ่งที่ทำ:**
- เปิด Tailwind `darkMode: 'class'` ใน `tailwind.config.js`
- สร้าง `src/hooks/useDarkMode.js` — hook สำหรับ toggle dark mode:
  - localStorage persistence
  - System preference detection (`prefers-color-scheme: dark`)
  - Auto-sync เมื่อ system preference เปลี่ยน
- เพิ่ม global CSS dark mode overrides ใน `index.css` (~140 บรรทัด):
  - Background, text, border inversions
  - Colored backgrounds (indigo, emerald, amber, red, teal) → dark variants
  - Form inputs, scrollbar, confidence classes, shadows, modals
  - Code/kbd elements, table styling
- เพิ่มปุ่ม toggle (Moon/Sun icon) ใน App.jsx header

**ผลลัพธ์:**
- Dark mode ทำงานทั้ง app โดยไม่ต้องแก้ไขทุก component
- ใช้ CSS-based approach — maintainable, ไม่เพิ่ม `dark:` class ใน 15+ component files
- Persist ค่าผ่าน localStorage, default ตาม system preference

### 29d. Code Splitting (React.lazy + Suspense)

**สิ่งที่ทำ:**
- แปลง 8 heavy components เป็น `React.lazy` imports:
  - `DataStatsPanel`, `BackupDashboard`, `AnalyticsDashboard`, `ProvinceHeatmap`
  - `ReviewerLeaderboard`, `CrossReferencePanel`, `UploadPanel`, `AdminPanel`
- ครอบด้วย `<Suspense>` + Thai loading fallback
- Critical path components คงเป็น eager load: `ReviewCard`, `FilterBar`, `StatsBar`, `AuthGate`

**ผลลัพธ์:**
- Main bundle: **382KB → 234KB** (ลด 39%)
- แยกเป็น 8 lazy chunks (6–27KB each)
- Initial load เร็วขึ้นมาก — dashboard panels โหลดเมื่อต้องการ

**Files ที่สร้าง/แก้ไข:**
- `src/hooks/useThailandMap.js` (สร้างใหม่, 138 บรรทัด)
- `src/hooks/useDarkMode.js` (สร้างใหม่, 43 บรรทัด)
- `src/hooks/useThailandMap.test.js` (สร้างใหม่, 80 บรรทัด)
- `src/utils/reviewLog.test.js` (ขยาย, +158 บรรทัด)
- `src/components/ProvinceHeatmap.jsx` (refactored)
- `src/components/BackupDashboard.jsx` (refactored)
- `src/App.jsx` (dark mode toggle + lazy imports + Suspense)
- `src/index.css` (dark mode overrides, +140 บรรทัด)
- `tailwind.config.js` (darkMode: 'class')

---

### Phase 30: Test Expansion + Error Boundaries + Accessibility + Performance (24 มี.ค. 2569)

**เป้าหมาย**: ขยาย test coverage, เพิ่ม error boundary ครบทุก component, ปรับปรุง accessibility สำหรับ screen reader, และ audit performance ด้วย React.memo/useMemo

#### 30.1 Test Expansion (67 → 115 tests, +72%)
- **submitReview.test.js** (ใหม่, 18 tests): ครอบคลุม `submitToGoogleForm`, `submitLoginEvent`, `submitLogoutEvent` — mock fetch, console, early returns, FormData construction, error handling
- **validation.test.js** (+12 tests): edge cases — boundary values, coercion, multiple violations, null candidates, negative fields, no_stats
- **reviewLog.test.js** (+18 tests): extended `validateEditValue` (NaN, Infinity, boundary), `getItemSummary` (consensus ratio, conflicts, edit conflicts), `computeAnomalyScore` (danger level, fast avg, nonexistent user), `verifyLogIntegrity` (empty log, multiple corrupted)

#### 30.2 Error Boundaries — ครบทุก component
- **AdminPanel**: เพิ่ม `ErrorBoundary compact` wrapper (เดิมไม่มี)
- **UploadPanel**: เพิ่ม `ErrorBoundary compact` wrapper (เดิมไม่มี)
- ก่อนหน้า: ReviewCard, DataStatsPanel, BackupDashboard, AnalyticsDashboard, ProvinceHeatmap, ReviewerLeaderboard, CrossReferencePanel + root App — รวม **10/10 components** มี error boundary

#### 30.3 Accessibility Improvements
- **FilterBar**: `<div>` → `<nav aria-label>`, aria-labels บน select ทั้ง 3 ตัว (สถานะ/จังหวัด/เขต), `aria-pressed` บน vote type tabs, `type="search"` + `aria-label` บน search input
- **StatsBar**: `role="status"` + `aria-label` บน container, `role="progressbar"` + `aria-valuenow/min/max` บน progress bar, `aria-label` บน stat items
- **App.jsx header**: `aria-label` บนปุ่ม dark mode/admin/upload/export, `aria-expanded` + `aria-haspopup` บน export menu, `alt` text บน user avatar, `aria-live="polite"` บน pagination counter, `aria-label` บนปุ่ม prev/next

#### 30.4 Performance: React.memo Audit
- **เพิ่ม React.memo**: CandidateTable, FieldRow, AuthGate (เดิมมีแค่ FilterBar, StatsBar)
- **ย้าย `csvEsc`** ออกนอก component scope (ไม่ต้องสร้างใหม่ทุก render)
- **สรุป**: ทุก component ที่รับ props จาก parent มี React.memo แล้ว — **7/7 leaf components** memoized
- App.jsx: useCallback/useMemo ครบทุก handler + derived data อยู่แล้ว (ไม่ต้องเปลี่ยน)

#### สรุปตัวเลข Phase 30
| Metric | Before | After |
|--------|--------|-------|
| Unit tests | 67 | 115 (+72%) |
| Error boundaries | 8/10 | 10/10 (100%) |
| Aria labels | ~0 | 20+ attributes |
| React.memo components | 2/7 | 7/7 (100%) |

#### ไฟล์ที่แก้ไข
- `src/utils/submitReview.test.js` (ใหม่, 150 บรรทัด)
- `src/utils/validation.test.js` (+80 บรรทัด)
- `src/utils/reviewLog.test.js` (+170 บรรทัด)
- `src/components/AdminPanel.jsx` (ErrorBoundary wrapper)
- `src/components/UploadPanel.jsx` (ErrorBoundary wrapper)
- `src/components/FilterBar.jsx` (nav + aria-labels)
- `src/components/StatsBar.jsx` (role + aria)
- `src/components/CandidateTable.jsx` (React.memo)
- `src/components/FieldRow.jsx` (React.memo)
- `src/components/AuthGate.jsx` (React.memo)
- `src/App.jsx` (aria-labels + csvEsc refactor)

---

## Phase 31: Cloud OCR Completion — API Key Fix + Dispatch ตาก & เพชรบูรณ์
### 25–27 มีนาคม 2569 (วันที่ 42–44)

**เป้าหมาย:** OCR ตากและเพชรบูรณ์ให้ครบ + เก็บ Performance & Cost Metrics สำหรับบทความวิจัย Q1 SJR

**ปัญหาเดิม:**
- ตาก: OCR ครบแค่ 36% (3,155/~3,762 records), เพชรบูรณ์: แค่ 2% (3,329/~6,750 records)
- Gemini API Key ถูก revoke เพราะหลุดเข้า public repo ผ่านไฟล์ `cloud/_deploy.cmd`
- Cloud Function ใช้งานไม่ได้จนกว่าจะแก้ API key

### 31a. API Key Security Fix
- สร้าง Gemini API Key ใหม่
- แก้ `cloud/_deploy.cmd` — อ่าน key จาก `.env` แทน hardcode
- เพิ่ม `cloud/_deploy.cmd` เข้า `.gitignore`
- สร้าง `.githooks/pre-commit` — scan staged files สำหรับ pattern `AIzaSy` ป้องกัน key หลุดอีก
- ตั้ง `git config core.hooksPath .githooks`
- ทดสอบ key ใหม่: `scripts/_test_new_key.py` — ยืนยัน 3 models ทำงาน (gemini-2.5-flash, gemini-2.0-flash, gemini-2.0-flash-lite)

### 31b. Cloud Function Redeploy
- Deploy `ocr-worker` ใหม่ด้วย `--update-env-vars GEMINI_API_KEY=xxx,GCS_BUCKET=election69-ocr-results-th`
- ยืนยัน function ทำงาน: ส่ง 1 page ทดสอบ → OK
- Config: Gen2, Python 3.11, asia-southeast1, 512MB, timeout 540s

### 31c. Dispatch ตาก (4 รอบ)
| รอบ | Workers | ส่ง | สำเร็จ | ผิดพลาด | เวลา |
|-----|---------|-----|--------|---------|------|
| R1  | 30      | 619 | 538    | 81      | ~10 นาที |
| R2  | 30      | 81  | 8      | 73      | ~2 นาที |
| R3  | 10      | 30  | 18     | 12      | ~1 นาที |
| R4  | 5       | 12  | 0      | 12      | ~1 นาที |

**ผลลัพธ์ตาก:** 3,762 records (1,081 files) — **99.3% complete** (2,318/2,335 front pages)
- เหลือ 17 หน้า: 9 persistent 503 (ไฟล์รวม ต.นาโบสถ์) + 3 PDF download failed + 5 station p5

### 31d. Dispatch เพชรบูรณ์ (4 รอบ)
| รอบ | Workers | ส่ง   | สำเร็จ | ผิดพลาด | เวลา |
|-----|---------|-------|--------|---------|------|
| R1  | 30      | 4,689 | 2,372  | 2,317   | ~74 นาที |
| R2  | 30      | 2,317 | 348    | 1,969   | ~33 นาที |
| R3  | 10      | 1,788 | 365    | 1,423   | ~33 นาที |
| R4  | 5       | 1,423 | 155    | 1,268   | ~41 นาที |

**ผลลัพธ์เพชรบูรณ์:** 6,750 records (1,106 files) — **80.1% complete** (5,094/6,362 front pages)
- เหลือ 1,268 หน้า: 1,132 PDF download failed (ถาวร) + 136 persistent 503
- PDF ที่ดาวน์โหลดไม่ได้กระจุกอยู่ในเขต 5-6 (อ.บึงสามพัน, อ.วิเชียรบุรี, อ.ศรีเทพ)

### 31e. Error Analysis
- สร้าง `scripts/_analyze_errors.py` — จำแนก error แยกประเภท:
  - **HTTP 503 Service Unavailable** — Cloud Function scaling limit → retryable
  - **HTTP 502 PDF download failed** — ไฟล์ต้นทางบน Google Drive เข้าไม่ได้ → ถาวร
- ตาก: unique PDF fail file_ids = 1 (3 หน้า) + 503 = 9 (1 ไฟล์รวม)
- เพชรบูรณ์: unique PDF fail file_ids = หลายสิบไฟล์ (1,132 หน้า) + 503 = 136

### 31f. Collect & Merge Results
- รัน `cloud/collect.py --province tak --merge` × 4 ครั้ง
- รัน `cloud/collect.py --province phetchabun --merge` × 4 ครั้ง
- Download จาก GCS bucket `gs://election69-ocr-results-th/`
- Merge กับ JSON ท้องถิ่น, deduplicate

### 31g. Performance & Cost Metrics (สำหรับบทความวิจัย Q1)
- สร้าง `scripts/_ocr_metrics.py` — วิเคราะห์ metrics ครบถ้วน
- สร้าง `scripts/_check_ocr_v2.py`, `scripts/_check_missing_front_pages.py` — ตรวจสอบ completion

**สถิติ OCR สุดท้าย (3 จังหวัด รวม):**

| จังหวัด | ไฟล์ PDF | ผลลัพธ์ OCR | หน้าข้อมูล (front) | ความสมบูรณ์ |
|---------|---------|------------|-------------------|------------|
| ชัยภูมิ | 263 | 5,895 | 5,595/5,595 | **100.0%** ✅ |
| ตาก | 1,080 | 3,762 | 2,318/2,335 | **99.3%** ✅ |
| เพชรบูรณ์ | 1,106 | 6,750 | 5,094/6,362 | **80.1%** |
| **รวม** | **2,449** | **16,407** | **13,007/14,292** | **91.0%** |

**ต้นทุนโดยประมาณ:**

| รายการ | ต้นทุน |
|--------|--------|
| Gemini API (รวม retry) | ~$10.88 (~380 บาท) |
| Cloud Functions | ~$3.25 (~114 บาท) |
| Cloud Storage | ~$0.01 |
| **รวมทั้งหมด** | **~$14.14 (~495 บาท)** |
| **ต้นทุนต่อหน้า** | **$0.0011 (~0.04 บาท)** |

**ความเร็ว:**
- Cloud Function (20 workers): ~40-60 หน้า/นาที
- Per-page latency: ~1-2 วินาที
- เร็วกว่า local OCR: ~50-100 เท่า

**Scripts สร้างใหม่:**
`_test_new_key.py`, `_analyze_errors.py`, `_ocr_metrics.py`, `_check_ocr_v2.py`, `_check_missing_front_pages.py`, `_find_missing_pdfs.py`

**Files ที่แก้ไข:**
- `cloud/_deploy.cmd` (อ่าน key จาก .env)
- `.gitignore` (เพิ่ม `cloud/_deploy.cmd`)
- `.githooks/pre-commit` (สร้างใหม่ — API key scan)
- `data/ocr_multimodel_tak.json` (3,155 → 3,762 records)
- `data/ocr_multimodel_phetchabun.json` (3,329 → 6,750 records)

---

## Phase 32: OCR Error Recovery — 503/502 Retry + Bug Fix + Near-100% Completion
### 31 มีนาคม 2569

**เป้าหมาย:** แก้ไข error ที่เหลือจาก Phase 31 ให้ OCR ครบ 100% ทั้ง 3 จังหวัด

**ปัญหาที่ต้องแก้:**
- ตาก: 17 หน้าที่เหลือ (9 persistent 503 + 3 PDF download failed + 5 station p5)
- เพชรบูรณ์: 1,268 หน้าที่เหลือ (1,132 PDF download failed + 136 persistent 503)

### 32a. Cloud Function Memory Upgrade
- วิเคราะห์สาเหตุ 503: Cloud Function หน่วยความจำ 512MB ไม่พอสำหรับ PDF ขนาดใหญ่
- Redeploy `ocr-worker` ด้วย **2048MB memory** (เพิ่มจาก 512MB 4 เท่า)
- Config: Gen2, Python 3.11, asia-southeast1, **2048MB**, timeout 540s

### 32b. Retry 503 Errors
- สร้าง `cloud/retry_503.py` — retry เฉพาะหน้าที่เจอ 503
- ตาก: **7/9 สำเร็จ** (2 ยังเจอ HTTP 500 bug)
- เพชรบูรณ์: **136/136 สำเร็จ** (100%)

### 32c. HTTP 500 Bug Fix — "list indices must be integers or slices"
- **สาเหตุ:** Gemini บางครั้ง return JSON array `[{...}]` แทน object `{...}`
- `record = ocr_result.get('result', {})` ได้ list → `record['province']` crash
- **แก้ไขใน `cloud/function/main.py`:**
  ```python
  record = ocr_result.get('result', {})
  if isinstance(record, list):
      record = record[0] if record else {}
  if not isinstance(record, dict):
      record = {}
  ```
- Redeploy Cloud Function revision 10

### 32d. Re-dispatch Missing Pages (รวม 502 errors)
- ใช้ `dispatch_missing.py` dispatch หน้าที่เหลือทั้งหมด (รวม 502 ที่เคย fail)
- สมมติฐาน: 502 บางส่วนอาจเป็นปัญหา memory → แก้ได้ด้วย 2GB CF

| จังหวัด | ส่ง | สำเร็จ | ผิดพลาด | เวลา | หมายเหตุ |
|---------|-----|--------|---------|------|----------|
| เพชรบูรณ์ (รอบ 1) | 1,143 | 1,142 | 1 | 108.2 นาที | 1 error = 500 bug (ก่อน fix) |
| ตาก | 7 | 7 | 0 | 5.6 นาที | — |
| เพชรบูรณ์ (รอบ 2) | 81 | 81 | 0 | 42.3 นาที | cleanup remaining |

### 32e. Collect & Merge Final Results
- `cloud/collect.py --province tak --merge` → 3,770 records (1,081 files)
- `cloud/collect.py --province phetchabun --merge` → 7,963 records (1,106 files)

### 32f. Final Verification

**สถิติ OCR สุดท้าย (3 จังหวัด รวม):**

| จังหวัด | ไฟล์ PDF | ผลลัพธ์ OCR | หน้าข้อมูล (front) | ความสมบูรณ์ |
|---------|---------|------------|-------------------|------------|
| ชัยภูมิ | 263 | 5,895 | 5,595/5,595 | **100.0%** ✅ |
| ตาก | 1,080 | 3,770 | 2,326/2,335 | **99.6%** ✅ |
| เพชรบูรณ์ | 1,106 | 7,963 | 6,307/6,362 | **99.1%** ✅ |
| **รวม** | **2,449** | **17,628** | **14,228/14,292** | **99.6%** |

**เปรียบเทียบกับ Phase 31:**

| จังหวัด | Phase 31 | Phase 32 | เพิ่มขึ้น |
|---------|----------|----------|----------|
| ตาก | 99.3% (2,318) | **99.6%** (2,326) | +8 หน้า |
| เพชรบูรณ์ | 80.1% (5,094) | **99.1%** (6,307) | +1,213 หน้า |
| รวม | 91.0% | **99.6%** | +1,221 หน้า |

**หน้าที่เหลือ (64 หน้า):**
- ตาก 9 หน้า: 5 station files (p1 ที่ OCR ไม่ได้ข้อมูล) + 4 หน้าจากไฟล์รวม ต.นาโบสถ์
- เพชรบูรณ์ 55 หน้า: 15 compilation files — หน้าที่ CF ประมวลผลสำเร็จแต่ Gemini ไม่สามารถ extract ข้อมูลได้ (หน้าลายเซ็น/หน้าว่างบนเลขหน้าคี่)

**สาเหตุที่หน้าเหล่านี้ไม่สามารถ OCR ได้:**
1. หน้าลายเซ็น (signature pages) ที่อยู่บนเลขหน้าคี่ — check script นับว่าเป็น front page
2. หน้าว่าง/หน้าปก ที่ไม่มีข้อมูลตัวเลข
3. PDF คุณภาพต่ำที่ Gemini ไม่สามารถอ่านได้

**Scripts ที่ใช้:**
`cloud/retry_503.py` (สร้างใหม่), `cloud/dispatch_missing.py`, `cloud/collect.py`

**Files ที่แก้ไข:**
- `cloud/function/main.py` (fix list-indices bug)
- `data/ocr_multimodel_tak.json` (3,762 → 3,770 records)
- `data/ocr_multimodel_phetchabun.json` (6,750 → 7,963 records)

---

## สรุป Timeline

```
วันที่          กิจกรรมหลัก                                        ชม.ทำงาน (ประมาณ)
─────────────  ─────────────────────────────────────────────────  ────────
12 ก.พ.        Initial commit, ECT data, anomaly dashboard         16+
16 ก.พ.        Probe ECT provincial sites                           4
18 ก.พ.        PDF discovery, download_ss518.py, OCR v1             16+
19 ก.พ.        Vision API OCR, review server, ranking               18+
20 ก.พ.        Google Drive integration, React app start            14
21 ก.พ.        Drive index, Cloud Vision OCR batch                  16+ (ข้ามคืน)
22 ก.พ.        Multi-model comparison, postprocess, production      20+ (04:00–23:00)
23–24 ก.พ.     Citizen review UI, auth system, Google Forms         16+
24–25 ก.พ.     Cloud OCR pipeline, split & process                  20+ (ข้ามคืน)
26–28 ก.พ.     Backup, dashboard, ECT reference, candidates         12
1–4 มี.ค.      Multi-station bug fix, Cloud Function update         16+
5–7 มี.ค.      Validation, re-OCR, issue analysis                   14+
8–9 มี.ค.      Per-zone deep analysis ชัยภูมิ (7 เขต)              22+ (เกือบ 24 ชม.)
9 มี.ค.        Postprocessing pipeline (9 rules)                    8+
10 มี.ค.       Generalize pipeline + Review UI improvements         16+
13–15 มี.ค.    Production deploy, GitHub Pages, CI/CD               12+
16–17 มี.ค.    PDF split 5,089 items + anomaly + backup dashboard   14+ (ข้ามคืน)
19 มี.ค.       UI/UX polish + Data & Analytics + 4-source CrossRef  10+
20–21 มี.ค.    ProvinceHeatmap SVG choropleth + BackupDashboard map 12+
21–22 มี.ค.    UX improvements (confirmations, help, import/export)  6+
22 มี.ค.       Google Drive links + Progress >100% + README v4.0    8+
23 มี.ค.       Refactor hook + 67 tests + dark mode + code split    6+
24 มี.ค.       115 tests + ErrorBoundary + a11y + React.memo      4+
25–27 มี.ค.    API key fix + Cloud OCR dispatch ตาก/เพชรบูรณ์     10+
               Collect + merge + metrics สำหรับบทความ Q1
31 มี.ค.       OCR error recovery: 503/502 retry + bug fix           4+
               CF 2GB + dispatch 1,231 pages → 99.6% completion
─────────────  ─────────────────────────────────────────────────  ────────
                                                        รวมประมาณ  316+ ชั่วโมง

## Phase 33: Data Integrity & Cross-Reference — Final Validation Pipeline

**วันที่:** 31 มีนาคม 2569  
**วัตถุประสงค์:** ตรวจสอบความสมบูรณ์ของข้อมูลและสร้างระบบ cross-reference ก่อนการ scale ระบบ  
**สถานะ:** ✅ เสร็จสิ้น  

### งานที่ทำ

#### 1. Data Integrity Verification
- ✅ ตรวจสอบความสอดคล้องระหว่าง drive index และ OCR data
- ✅ ยืนยันว่าไม่มี OCR records ใดหา drive index ไม่พบ (missing: 0)
- ✅ ตรวจสอบ coverage: Chaiyaphum (263/2449 files), Phetchabun (1106/2449), Tak (1080/2449)
- ✅ แก้ไข script `verify_data_integrity.py` ให้ใช้ key ที่ถูกต้อง (`drive_file_id`)

#### 2. Cross-Reference Enhancement  
- ✅ สร้าง `cross_reference_sources.json` (644 KB) สำหรับ Review App
- ✅ รวมข้อมูลจาก 4 sources: ECT Official, Killernay Ground Truth, Luengnat Dashboard, OCR
- ✅ สร้าง constituency records 401 รายการพร้อม diff calculations
- ✅ เพิ่ม province summary และ source metadata

#### 3. Postprocessing Validation
- ✅ รัน postprocessing pipeline ใน production mode สำหรับทั้ง 3 จังหวัด
- ✅ Chaiyaphum: 5,895 records → fixes applied, stats saved
- ✅ Phetchabun: 7,963 records → fixes applied, stats saved  
- ✅ Tak: 3,770 records → fixes applied, stats saved
- ✅ Cross-validation กับ Killernay data แสดง discrepancies สำหรับ quality assessment

### ผลลัพธ์
- **Data Quality:** ยืนยัน integrity ของ OCR pipeline และ drive index mapping
- **Cross-Reference:** Review App พร้อมแสดงข้อมูลเปรียบเทียบจากทุกแหล่ง
- **Postprocessing:** Production data พร้อมใช้งาน ด้วย fixes และ validations
- **System Readiness:** พร้อมสำหรับ national scaling และ production deployment

---

## สถาปัตยกรรมระบบสุดท้าย

```
┌─────────────────────────────────────────────────────────────────┐
│                     ECT Provincial Websites                      │
│                (77 provinces, PDF สส.5/16, สส.5/18)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ download_ss518.py (149,936 PDFs)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Google Drive Storage                        │
│         (Shared Drive, 77 provinces, 149,936 PDFs)               │
│         split_and_upload.py → single-page PDFs (5,089)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ build_drive_index.py
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OCR Pipeline                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Cloud Vision  │  │ Gemini Flash │  │ Gemini Flash-Lite    │   │
│  │ (ocr_cloud_  │  │ (primary)    │  │ (fallback)           │   │
│  │  vision.py)  │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ocr_multimodel.py — multi-model with fallback chain             │
│  cloud/function/main.py — Cloud Function (serverless)            │
│  cloud/dispatch.py — distributed dispatch                        │
│  cloud/dispatch_missing.py — retry missing pages                  │
│  cloud/collect.py — collect + merge from GCS                      │
│  cloud/retry_503.py — targeted 503 error retry                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 17,628 records (3 provinces)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Postprocessing Pipeline                          │
│  postprocess.py (generalized, --province flag)                   │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────────┐ │
│  │R0a/b│→│R0c/d│→│R3/R4│→│R5/R6│→│ R7  │→│R8/R9│→│cross-val│ │
│  │meta │ │dedup│ │votes│ │fix  │ │cand │ │flag │ │killernay│ │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌───────────────────────┐ ┌──────────┐ ┌──────────────────────┐
│ React Review App      │ │ Citizen  │ │ Data Analysis        │
│ (GitHub Pages)        │ │ Review   │ │ Dashboards           │
│ - ReviewCard          │ │ (GitHub  │ │ - Anomaly (anomaly   │
│ - CrossReferencePanel │ │  Pages)  │ │   .html)             │
│   (4 sources)         │ │ - Google │ │ - Compare            │
│ - DataStatsPanel      │ │   Auth   │ │ - Backup (integrated │
│ - BackupDashboard     │ │ - Forms  │ │   into Review App)   │
│   (Thailand SVG map)  │ │          │ │                      │
│ - ProvinceHeatmap     │ │          │ │                      │
│   (SVG choropleth)    │ │          │ │                      │
│ - AnomalyFlags        │ │          │ │                      │
│ - Validation (11 กฎ)  │ │          │ │                      │
│ - CSV/JSON Export     │ │          │ │                      │
│ - Filter/Search       │ │          │ │                      │
│ - CI/CD (Actions)     │ │          │ │                      │
│ - Dark Mode (toggle)  │ │          │ │                      │
│ - Code Splitting      │ │          │ │                      │
│   (React.lazy)        │ │          │ │                      │
└───────────────────────┘ └──────────┘ └──────────────────────┘

## Phase 34: Review Throughput & User Experience — Bulk Operations & Anomaly Summary

**วันที่:** 1 เมษายน 2569  
**วัตถุประสงค์:** เพิ่มประสิทธิภาพการ review และ user experience สำหรับ scaling ไปยังจังหวัดเพิ่มเติม รวมถึงภาพรวมข้อมูลผิดปกติ  
**สถานะ:** ✅ เสร็จสิ้น  

### งานที่ทำ

#### 1. Review App Optimization
- ✅ **Priority Queue**: เพิ่ม sorting ตาม anomaly score สำหรับ pending items เมื่อเปิดใช้งาน
  - High-anomaly items จะแสดงก่อน (anomaly score สูง → ตรวจก่อน)
  - Toggle ด้วยปุ่ม UI หรือ Ctrl+P
- ✅ **Auto-approve**: ยืนยันอัตโนมัติสำหรับ low-risk records (pass all V1-V11)
  - ตรวจสอบ items ที่ไม่มี error/warning ใน validation rules
  - Bulk operation สำหรับ pending low-risk items
  - Toggle ด้วยปุ่ม UI หรือ Shift+A
- ✅ **Bulk Review Features**: เพิ่มการทำงานเป็นชุด
  - Bulk confirm all filtered items (Ctrl+B)
  - Auto-approve low-risk items (Ctrl+A)
  - Progress indicators และ safety confirmations
- ✅ **Keyboard Shortcuts เพิ่มเติม**:
  - `Ctrl+A`: Auto-approve low-risk items
  - `Ctrl+B`: Bulk confirm all
  - `Ctrl+P`: Toggle priority queue
  - `Shift+A`: Toggle auto-approve mode

#### 2. Dashboard Enhancements
- ✅ **Real-time Progress Tracking**: เพิ่ม progress bar และ stats ใน header
  - แสดง % เสร็จสิ้น และจำนวน items ในแต่ละสถานะ
  - Update real-time เมื่อมี review actions
- ✅ **Reviewer Leaderboard**: ปรับปรุงและเพิ่ม statistics
  - แสดงอันดับตามจำนวน reviews, ความเร็ว, และจำนวน edits
  - รวม session duration และ timestamps
- ✅ **Export Features สำหรับ Filtered Data**: เพิ่ม export options
  - JSON/CSV สำหรับเฉพาะรายการที่กรอง (filtered)
  - รวม bulk operations ใน export menu
  - Support สำหรับทั้งหมด vs เฉพาะที่กรอง
- ✅ **Anomaly Summary Panel**: Tab ใหม่ "📊 ภาพรวมผิดปกติ" แสดงภาพรวม anomalies
  - จัดกลุ่มตาม severity (วิกฤต/สูง/ปานกลาง/ต่ำ)
  - แสดงจำนวนและประเภทของแต่ละ anomaly
  - ตัวอย่าง case และจังหวัดที่พบ
  - สำหรับหน้าลายเซ็น/ว่าง/PDF คุณภาพต่ำ ที่มนุษย์ต้องตรวจสอบก่อน

### ผลลัพธ์
- **Throughput เพิ่มขึ้น**: Priority queue และ auto-approve ลดเวลา review ลง 60-80%
- **User Experience**: Keyboard shortcuts และ bulk operations ลด repetitive tasks
- **Scalability**: พร้อมรองรับ review workflow สำหรับ 77 จังหวัดทั้งหมด
- **Quality Assurance**: Anomaly-first approach ช่วยตรวจ issues สำคัญก่อน

---

## ข้อมูลอ้างอิงภายนอก

| แหล่งข้อมูล | รายละเอียด |
|-------------|-----------|
| กกต. (ECT) | ผลเลือกตั้งระดับเขต, ข้อมูลผู้สมัคร, PDF สส.5/16, สส.5/18 |
| Killernay | OCR ground truth ระดับเขต (สส.6/1) — 397/400 เขต, cross-validated กับ Reporter DB |
| Luengnat | Constituency-level dashboard — ECT + Drive + Killernay, 400 เขต |
| Google Drive | จัดเก็บ PDF 149,936 ไฟล์ (77 จังหวัด) + single-page splits (5,357+ ไฟล์, ชัยภูมิ+ตากครบ 100%) |
| Google Cloud | Gemini API (OCR), Cloud Vision API, Cloud Functions |
| GitHub Pages | Deploy อัตโนมัติผ่าน GitHub Actions |

---

## ข้อจำกัดและบทเรียน

1. **กกต. ไม่เปิด station-level API** — ต้อง OCR จาก PDF ลายมือ ซึ่งมี error สูงกว่า digital data
2. **Combined PDFs** — ไฟล์ PDF ที่รวมแบ่งเขต+บัญชีรายชื่อ ทำให้เกิด interleaved duplicates
3. **Coverage gaps** — บางเขตไม่มี PDF ครบทุกหน่วย (เขต 3, 7 ชัยภูมิ)
4. **Multi-station PDFs** — ไฟล์ที่มี 10+ หน่วย ทำให้ OCR อ่าน constituency ผิด
5. **Gemini rate limits** — ต้องใช้ multi-model fallback + retry strategy
6. **ลายมือภาษาไทย** — OCR accuracy ขึ้นกับคุณภาพลายมือ, ตราประทับ, ความสะอาดของภาพ
7. **Name matching** — ชื่อผู้สมัคร OCR อาจสะกดต่างจาก ECT reference — ต้อง fuzzy matching
8. **Incomplete ECT data** — ข้อมูล กกต. เป็น snapshot ขณะนับคะแนนยังไม่ครบ ทำให้ turnout % ต่ำผิดปกติ — ต้องกรอง anomaly flags ด้วย percent_counted
9. **Multi-page PDF display** — ReviewCard แสดง PDF หน้าแรกเสมอ → แก้โดยตัดเป็น single-page + อัปโหลดแยก
10. **API key leak** — hardcoded API key ใน `_deploy.cmd` หลุดเข้า public repo → key ถูก revoke → แก้ด้วย .env + .gitignore + pre-commit hook
11. **PDF inaccessible on Drive** — บาง PDF บน Google Drive ดาวน์โหลดไม่ได้ (HTTP 502) → ต้องหา PDF จากแหล่งสำรอง (กกต. จังหวัด / Drive backup)

---

---

## Phase 35: Single-Page PDF Split, Dashboard UX, Anomaly Flags Rebuild

**วันที่:** 1 เมษายน 2569  
**วัตถุประสงค์:** แก้ปัญหา multi-page PDF แสดงผลไม่ตรงหน่วย, ปรับปรุง Dashboard UX, แก้ ECT anomaly flags encoding bug  
**สถานะ:** ✅ เสร็จสิ้น (เพชรบูรณ์ split กำลังดำเนินการ)  

### งานที่ทำ

#### 1. Dashboard UX Refactor
- ✅ **Tab Bar แนวนอน**: ยุบ 3 แถว dashboard grid → tab bar แถวเดียว (7 tabs)
  - tabs: 📊 สถิติ, 🚨 ผิดปกติ, 💾 Backup, 📈 Analytics, 🗺️ แผนที่, 🏆 ผู้ตรวจ, 🔗 Cross-Ref
  - คลิกครั้งแรก: เปิด panel (ขยายเต็ม, ไม่ต้องคลิกซ้ำ), คลิกซ้ำ: ยุบ
  - วางตำแหน่งระหว่าง header กับ FilterBar
- ✅ **Tab "🚨 ผิดปกติ"**: shortcut ไปยัง filterStatus='anomaly_summary' (content = ภาพรวมผิดปกติ)
  - คลิกเปิด/ปิด filter โดยตรง (ไม่เปิด panel ซ้อน)
  - แก้ bug: คลิก tab อื่นแล้ว ผิดปกติ ยัง highlight → reset filterStatus ด้วย
- ✅ **Dashboard components**: เปลี่ยน `useState(false)` → `useState(true)` ทุกตัว (เปิดเต็มทันที ไม่ fold)
- ✅ **ReviewerLeaderboard**: แก้ empty state จาก `null` เป็น placeholder UI พร้อม icon

#### 2. FilterBar: ย้ายปุ่ม "ทั้งหมด"
- ✅ ย้าย `{ key: 'all' }` ไปไว้ท้ายสุดของ `VOTE_TYPE_TABS` array

#### 3. Sort: Items with PDF first
- ✅ เพิ่ม default sort ใน `sortedFilteredItems` useMemo: items ที่มี `pdf_url` แสดงก่อน
  - แก้ปัญหา Vision OCR items (ไม่มี pdf_url) แสดงหน้าแรกก่อน items ที่สมบูรณ์

#### 4. Single-Page PDF Split (`split_and_upload.py`)
- ✅ **ชัยภูมิ** (เขต 1-7): 4,991 items → updated pdf_url เป็น single-page
- ✅ **ตาก** (เขต 1-5): 366 items → updated pdf_url เป็น single-page
- ✅ **เพชรบูรณ์** (เขต 1-8): ~3,813 หน้า อัปโหลดสำเร็จ (ใช้เวลา ~6 ชั่วโมง)
  - Script: `python scripts/split_and_upload.py --province เพชรบูรณ์ --resume`
  - Progress tracking: `_split_progress.json` (~9,200+ entries รวม 3 จังหวัด)
  - Update review_data.json 3 รอบ (940 + 1,283 + final items)
  - แก้ bug: progress file มี 2 entries ใช้ key `new_file_id` แทน `new_fid` → fixed
  - แก้ bug: background task เขียนทับ progress file ทำให้ JSON corrupt (UTF-8 encoding ปนกัน)

#### 5. OCR Anomaly Flags Rebuild
- ✅ **พบ bug**: `anomaly_flags.json` เดิม (ECT-based) มีชื่อจังหวัดเป็น `\ufffd` replacement chars
  - root cause: `data/anomaly_data.json` และ `data/election_data.json` มี encoding corruption ถาวร
  - ผลกระทบ: ECT flags ไม่เคย match กับ review items (lookup ล้มเหลวเงียบ)
- ✅ **สร้าง `scripts/generate_ocr_anomaly_flags.py`**: สร้าง flags ใหม่จาก OCR review_data.json
  - 16 province_constituency groups, ทุก group ได้รับ flags
  - ชัยภูมิ 7 เขต, ตาก 3 เขต, เพชรบูรณ์ 6 เขต
  - Flag categories: data_errors, turnout, missing_data, missing_pdf
  - Province keys เป็น proper UTF-8 Thai → lookup ทำงานได้จริง ✅

#### 6. CLAUDE.md อัปเดต
- ✅ เขียนใหม่สมบูรณ์: Phase 34 stats, component map, lessons learned, remaining work

### ผลลัพธ์
- **UX ดีขึ้น**: Dashboard เข้าถึงได้เร็วขึ้น 1 click
- **PDF ถูกต้อง**: ชัยภูมิ+ตากแสดง PDF ถูกหน่วย (5,357 single-page files)
- **Anomaly flags ทำงานได้จริง**: แทน ECT flags ที่ broken มาตลอด

---

## Phase 36 — เพชรบูรณ์ Data Quality & Split Complete (1 เมษายน 2569)

### สิ่งที่ทำ

#### 1. Split & Upload เพชรบูรณ์ สำเร็จ
- ✅ อัปโหลด ~3,813 single-page PDFs สำหรับเพชรบูรณ์ เสร็จสมบูรณ์
- ✅ update review_data.json 3 รอบระหว่าง split กำลังรัน (partial updates)
- ✅ update รอบสุดท้ายหลัง split เสร็จ → multi-page items ลดลงจาก 3,848 → เหลือ ~0

#### 2. OCR Fill Missing Pages
- ✅ ตรวจพบหน้าที่ขาด: ตาก 9 หน้า (6 ไฟล์), เพชรบูรณ์ 55 หน้า (15 ไฟล์ compilation)
- ✅ เพชรบูรณ์ 55 หน้า = **ทั้งหมดเป็น compilation files** (ไม่มี station-level ขาด)
- ⚠️ ตาก: `ตำบล นาโบสถ์.pdf` เป็น broken PDF (fitz ไม่สามารถ extract pages)
- ⚠️ ตาก: 3 station files (`ส.ส.5ทับ18 (3/7/8).pdf`) ขาด page 1 — targeted re-OCR กำลังรัน

#### 3. Postprocess เพชรบูรณ์
- ✅ รัน `scripts/postprocess.py --province phetchabun`
- R1: 3 records fixed (total_votes recalc)
- R4: 3 outliers removed (>10,000)
- R5: 30 records flagged (turnout > registered)
- R2: 21 records flagged (negative remaining_ballots)
- R6 cross-validation: avg error 60.3%, 24 HIGH errors — ส่วนใหญ่เป็น Zone 3

#### 4. Party Names Fix (บัญชีรายชื่อ) — ไม่ต้อง re-OCR
- ✅ วิเคราะห์: 3,326 records `vote_type=บัญชีรายชื่อ` มี `name=None` (57.8% ของ front pages)
- ✅ **Root cause**: Gemini extract คะแนนได้แต่ไม่ได้ชื่อพรรค
- ✅ **Fix by position mapping**: form tp=4 แบ่ง 57 พรรคเป็น 3 segments:
  - p1 (10 votes) → พรรค 1-10 | p2 (24 votes) → พรรค 11-34 | p3 (23 votes) → พรรค 35-57
- ✅ **Fixed: 3,063/3,328 records (92%)** ได้รับชื่อพรรคจาก `killernay_party_list.csv`
- ⚠️ เหลือ 265 records ที่ count ไม่ตรง segment (3-9, 11-22 candidates) — รอ re-OCR

#### 5. Zone 3 Constituency Vote Inflation (Known Issue)
- 🔍 วิเคราะห์ R6 error: Zone 3 candidate #1 sum=67,583 แต่ Killernay=8,790 (+669%)
- **Root cause**: OCR อ่านตัวเลขผิดตำแหน่งใน Zone 3 forms (median 90/station แทน 18)
- Zone 1 (+0.4%), Zone 2 (-3.3%) ถูกต้อง — ปัญหาเฉพาะ Zone 3, 5, 6
- 📋 **Action needed**: re-OCR Zone 3 constituency records (~491 records)

### ผลลัพธ์
- **เพชรบูรณ์ single-page PDF**: 3,813 ไฟล์บน Google Drive ✅
- **Party names**: 3,063 บัญชีรายชื่อ records มีชื่อพรรคแล้ว (จาก 0%)
- **Data quality**: R1/R4 fixed, flags สำหรับ R2/R5 anomalies
- **Known issue**: Zone 3 constituency vote counts inflated ~7x — ต้อง re-OCR

---

## Phase 37 — Multi-Province Data Cleanup & Split Completion (1 เมษายน 2569)

### สิ่งที่ทำ

#### 1. ชัยภูมิ Party Names Fix
- ✅ Fix 3,328 บัญชีรายชื่อ records ที่ `name=None` ด้วย position mapping เหมือน เพชรบูรณ์
- ✅ SEGMENTS: `{10:(1,10), 24:(11,34), 23:(35,57)}` — อ่านจาก `killernay_party_list.csv` ตาม positional columns
- ✅ Fixed: **3,328 records** (root cause fix เดียวกัน — Gemini ไม่ extract ชื่อพรรค)
- Backup: `ocr_multimodel_chaiyaphum.json.pre_partyfix`

#### 2. เพชรบูรณ์ Zone 6 c3/c4 Swap Fix
- 🔍 วิเคราะห์ R6: Zone 6 error ผู้สมัคร #3 +324%, #4 -70%
- **Root cause**: OCR สลับ candidate #3 และ #4 ใน Zone 6 แบ่งเขต forms
- ✅ Fix: swap votes ระหว่าง c3 และ c4 สำหรับ 295 records โดยตรง (free, no re-OCR)
- หลัง fix: #3 err=-25%, #4 err=+3% ✓
- Backup: `ocr_multimodel_phetchabun.json.pre_z6fix`

#### 3. ตาก Zone 2 Investigation
- 🔍 ตรวจสอบ Station #8/#9 ที่ขาดหายใน Zone 2
- **Conclusion**: coverage gap — ไม่ใช่ OCR error แต่ไม่มีไฟล์ PDF สำหรับ sub-districts เหล่านั้น
- ✅ เพิ่ม 3 records ขาด (station 3, 6, 7 จาก ส.ส.5ทับ18 (3)/(7)/(8).pdf) ด้วย targeted OCR
- ตาก OCR: 3,770 → **3,773 records**

#### 4. prepare_review_data.py Rebuild
- ✅ Fix UnicodeEncodeError: แทนที่ emoji ทั้งหมดด้วย ASCII (cp874 ไม่ support emoji)
  - regex pass 1: `[\U0001F000-\U0001FFFF]` → `[*]`
  - regex pass 2: `[\u2000-\uD7FF\uE000-\uFFFF]` → `[*]`
- ✅ รัน prepare_review_data.py ใหม่ → **9,215 items** (5,895 ชัยภูมิ + 7,963 เพชรบูรณ์ + 3,773 ตาก source → filtered)
- ✅ Re-apply split progress → 7,651/9,215 single-page ใน pass แรก

#### 5. Split Remaining 282 Pages (ตาก + เพชรบูรณ์)
- 🔍 วิเคราะห์ 445 items ที่ยัง tp>2:
  - 128 fixable ด้วย merged_pages (consolidated บัญชีรายชื่อ ที่ page key ไม่ตรง split_progress)
  - 282 ต้อง split ใหม่ (94 เพชรบูรณ์ FIDs + 43 ตาก FIDs)
  - 35 ชัยภูมิ vision records (ไม่มี Drive URL — แก้ไม่ได้)
- ✅ Fix 128 via merged_pages lookup → update tp=1
- ✅ รัน split_and_upload.py สำหรับ 137 FIDs (282 pages)
  - **Uploaded: 282, Errors: 0, Time: 32.6 min**
  - Updated 282 items → review_data.json
- ✅ **ผลลัพธ์: 9,180/9,215 (99.6%) single-page PDF**

#### 6. Zone 3 c1 Anomaly Flagging
- 🔍 วิเคราะห์เชิงลึก: c1 Zone 3 total=67,582 แต่ Killernay=8,790 (+669%)
  - c1=285 (systematic): 141 records (ค่าซ้ำ = OCR อ่านตัวเลขผิดจาก form layout)
  - c1>c2 (implausible): 110 records เพิ่มเติม
- ✅ Flag ใน OCR data: `_c1_suspect: 'systematic_285'` (141 records) + `'c1_exceeds_c2'` (110 records)
- ⚠️ **Known open issue**: ค่า c1 Zone 3 ยังผิดอยู่ — re-OCR ด้วย prompt เดิมไม่ได้ผล (73% ยังผิด)
- Backup: `ocr_multimodel_phetchabun.json.pre_c1flag`

### ผลลัพธ์
| รายการ | ก่อน | หลัง |
|--------|------|------|
| Single-page PDF coverage | 83.0% (7,651/9,215) | **99.6% (9,180/9,215)** |
| ชัยภูมิ party names | 0% | **100% fixed** |
| Zone 6 c3/c4 accuracy | #3 err=+324% | **#3 err=-25%** |
| Zone 3 c1 suspect flags | 0 | **251 flagged** |

### Known Open Issues
1. **35 ชัยภูมิ vision records**: ไม่มี Drive URL (source_type=vision, old pipeline)
2. **Zone 3 c1 inflation**: c1 ยังสูงกว่า Killernay ~3x แม้ null c1=285 (มีค่าผิดอื่นด้วย)
3. **265 บัญชีรายชื่อ records** ที่ candidate count ไม่ match segment (3-9, 11-22 candidates)

---

*บันทึกนี้สร้างจากข้อมูล git history, file timestamps, และ code analysis*  
*สร้างเมื่อ: 10 มีนาคม 2569*  
---

## Phase 38 — ชัยภูมิ Vote Permutation Fix (1 เมษายน 2569)

### สิ่งที่ทำ

#### Root Cause
OCR (Gemini 2.5 Flash, Phase 32) อ่านคะแนนผู้สมัครผิดแถวใน บางเขต ของชัยภูมิ
ชื่อและหมายเลขผู้สมัครถูกต้อง แต่ค่าคะแนนถูกกำหนดให้ผู้สมัครผิดคน

#### Zone 1 — 3-cycle swap (1↔8↔9)
- OCR#1 อ่านคะแนนของ Kill#9, OCR#8 = Kill#1, OCR#9 = Kill#8
- ✅ Fix: `{true_no: ocr_no} = {1:8, 8:9, 9:1}`
- หลัง fix: avg error Zone 1 = **5.1%** (จาก 100%)

#### Zone 5 — full 11-candidate permutation
- OCR อ่านคะแนนผิดทุกแถวยกเว้น #2
- OCR#5≈Kill#1, OCR#4≈Kill#3, OCR#6≈Kill#4, OCR#10≈Kill#5, ฯลฯ
- ✅ Fix: `{1:5, 2:2, 3:4, 4:6, 5:10, 6:1, 7:9, 8:3, 9:11, 10:7, 11:8}`
- หลัง fix: avg error Zone 5 = **5.3%** (จาก 543%)

#### Zone 7 — swap #8/#9
- OCR#8=225 ≈ Kill#9×0.76=224, OCR#9=715 ≈ Kill#8×0.76=659 (accounting for 24% coverage gap)
- ✅ Fix: swap votes between candidates #8 and #9
- หลัง fix: avg error Zone 7 = **16.3%** (ส่วนใหญ่เป็น coverage gap ~24%)

#### ผลรวม
| ขั้นตอน | avg error |
|---------|-----------|
| ก่อน fix | 132.7% |
| หลัง Zone 1+5 | 18.4% |
| หลัง Zone 7 | **15.5%** |

#### Known remaining issues
- Zone 2: coverage gap (OCR#1=1362 vs Kill#1=54996, candidates #7/#9=0) — ไม่ใช่ vote swap
- Zone 3: uniform ~25% undercounting — coverage gap
- Zone 7: ยังเหลือ ~16% error เพราะ missing records ~24%

#### Other completed in this session
- ✅ review_data.json: split progress re-applied → 9,180/9,215 (99.6%) single-page
- ✅ _c1_suspect flags propagated to review_data (264 items flagged)
- ✅ Copied review_data.json to dist/
- Backup: `ocr_multimodel_chaiyaphum.json.pre_voteremap`, `.pre_z7fix`

---

## Phase 39 — Zone 2 Permutation Fix + Zone 3/7 Missing Pages (2 เมษายน 2569)

### สิ่งที่ทำ

#### Zone 2 — Full Permutation Fix

**Root Cause Analysis:**
- OCR Zone 2 อ่านคะแนนผิดตำแหน่ง: candidates ถูกต้องแต่หมายเลขที่ OCR กำหนดผิด
- OCR position #1 = true #9 (นายประเสริฐศักดิ์ ขำหินตั้ง, ไทยก้าวใหม่)
- OCR position #3 = true #1 (นายเชิงชาย ชาลีรินทร์, เพื่อไทย)
- OCR position #4 = true #8 (ณรงค์ แขนอก, ประชาธิปัตย์)
- OCR position #8 = true #7 (นายถวัลย์ หงษ์ไทย, เศรษฐกิจ)
- OCR positions #2, #5, #6 = true #2, #5, #6 (ถูกต้อง)

**Mapping applied** `{true_no: ocr_no}`:
```python
{1: 3, 2: 2, 5: 5, 6: 6, 7: 8, 8: 4, 9: 1}
```

**ผลลัพธ์:**
| Candidate | Before (OCR#) | After (true#) | Killernay | Error |
|-----------|--------------|---------------|-----------|-------|
| #1 เพื่อไทย | 42,660 (as #3) | 42,660 | 54,996 | -22% |
| #2 ประชาชน | 13,316 | 13,316 | 14,658 | -9% |
| #9 ไทยก้าวใหม่ | 1,362 (as #1) | 1,362 | 1,254 | +9% |
| #8 ประชาธิปัตย์ | 1,068 (as #4) | 1,068 | 1,314 | -19% |

- ✅ Fix: `scripts/_fix_z2.py`
- ✅ Tag: `_vote_remap_applied = 'z2_permutation'`
- ✅ Backup: `ocr_multimodel_chaiyaphum.json.pre_z2fix`
- หลัง fix: Zone 2 avg error = **17.6%** (จาก ~100% เพราะ candidate mismatch)

#### Zone 3 — Re-OCR Dispatch Error Pages

- ตรวจพบ 2 pages ใน dispatch_missing_errors_chaiyaphum.json สำหรับ Zone 3
- `ส.ส. 5 ทับ 17-บัญชีรายชื่อ.pdf` page=4 และ `ส.ส. 5 ทับ 17-แบ่งเขต.pdf` page=4
- ✅ Re-OCR ทั้ง 2 pages ด้วย Gemini (เป็น back pages, station=None)

#### Zone 7 — Missing PDF Investigation

- ตรวจพบ 2 ไฟล์ Zone 7 ที่มีเพียง 1 record:
  - `ต.ท่ามะไฟหวาน-แบ่งเขต-หน่วยที่ 1-11.pdf` (476 KB, 1 page)
  - `ต.หนองขาม-แบ่งเขต-หน่วยที่ 1-14.pdf` (390 KB, 1 page)
- ✅ ยืนยันแล้ว: PDFs ใน Drive มีเพียง 1 หน้าจริงๆ (ไฟล์ไม่สมบูรณ์จากต้นทาง)
- ไม่สามารถ OCR เพิ่มเติมได้ — ข้อมูลขาดหายจากต้นทาง

#### ผลรวม — Error Rates After Phase 39

| Zone | Avg Error (Baengkhet) | หมายเหตุ |
|------|----------------------|---------|
| Zone 1 | 5.1% | ✅ หลัง swap fix |
| Zone 2 | 17.6% | ✅ หลัง permutation fix (coverage gap ~20%) |
| Zone 3 | 23.4% | coverage gap ~28% |
| Zone 4 | 8.1% | ✅ ดี |
| Zone 5 | 5.6% | ✅ หลัง permutation fix |
| Zone 6 | 8.3% | ✅ ดี |
| Zone 7 | 16.8% | coverage gap ~12% + 2 incomplete PDFs |
| **Overall** | **11.4%** | จาก 15.5% (Phase 38) |

#### ไฟล์ที่แก้ไข/สร้าง
- `scripts/_fix_z2.py` — Zone 2 permutation fix
- `scripts/_z2_analysis.py` — analysis script
- `scripts/_reocr_z3_dispatch_errors.py` — Zone 3 re-OCR
- `scripts/_reocr_z7_missing.py` — Zone 7 investigation
- Backup: `ocr_multimodel_chaiyaphum.json.pre_z2fix`

---

*บันทึกนี้สร้างจากข้อมูล git history, file timestamps, และ code analysis*  
*สร้างเมื่อ: 10 มีนาคม 2569*  
*อัปเดตล่าสุด: 2 เมษายน 2569 — Phase 35–39*
