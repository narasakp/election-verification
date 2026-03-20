# บันทึกการพัฒนาระบบตรวจสอบผลเลือกตั้ง สส. 2569
# Election Verification System — Development Log

> **ผู้พัฒนา:** narasak poophayang  
> **ระยะเวลา:** 12 กุมภาพันธ์ – 19 มีนาคม 2569 (36 วัน)  
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
- [สรุป Timeline](#สรุป-timeline)
- [สถาปัตยกรรมระบบสุดท้าย](#สถาปัตยกรรมระบบสุดท้าย)
- [ข้อมูลอ้างอิงภายนอก](#ข้อมูลอ้างอิงภายนอก)
- [ข้อจำกัดและบทเรียน](#ข้อจำกัดและบทเรียน)

---

## สถิติรวมของโปรเจกต์

| หมวด | จำนวน |
|------|-------|
| Python scripts | 172+ ไฟล์ |
| React components | 10 ไฟล์ (+ hooks, utils) |
| Data files (data/) | 56 ไฟล์ |
| Data files (review-app) | 3 ไฟล์ (review_data, anomaly_flags, backup_status) |
| PDF ดาวน์โหลด | 149,936 ไฟล์ (77 จังหวัด) |
| OCR records | 12,376 รายการ (3 จังหวัด) |
| Review items | 6,111 รายการ (deployed) |
| Git commits | 25 commits |
| Cloud Functions | 1 (Gemini OCR) |
| Dashboards | 5 (main, anomaly, compare, review, backup) |
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
─────────────  ─────────────────────────────────────────────────  ────────
                                                        รวมประมาณ  266+ ชั่วโมง
```

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
└──────────────────────────┬──────────────────────────────────────┘
                           │ 12,376 records (3 provinces)
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
┌──────────────────┐ ┌──────────┐ ┌──────────────────────┐
│ React Review App │ │ Citizen  │ │ Data Analysis        │
│ (GitHub Pages)   │ │ Review   │ │ Dashboards           │
│ - ReviewCard     │ │ (GitHub  │ │ - Anomaly (anomaly   │
│ - DataStatsPanel │ │  Pages)  │ │   .html)             │
│ - BackupDashboard│ │ - Google │ │ - Compare            │
│ - AnomalyFlags   │ │   Auth   │ │ - Backup (integrated │
│ - Validation     │ │ - Forms  │ │   into Review App)   │
│ - CSV/JSON Export│ │          │ │                      │
│ - Filter/Search  │ │          │ │                      │
│ - CI/CD (Actions)│ │          │ │                      │
└──────────────────┘ └──────────┘ └──────────────────────┘
```

---

## ข้อมูลอ้างอิงภายนอก

| แหล่งข้อมูล | รายละเอียด |
|-------------|-----------|
| กกต. (ECT) | ผลเลือกตั้งระดับเขต, ข้อมูลผู้สมัคร, PDF สส.5/16, สส.5/18 |
| Killernay | ข้อมูล ground truth ระดับหน่วยเลือกตั้ง (แบ่งเขต + บัญชีรายชื่อ) |
| Google Drive | จัดเก็บ PDF 149,936 ไฟล์ (77 จังหวัด) + single-page splits (5,089 ไฟล์) |
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

---

*บันทึกนี้สร้างจากข้อมูล git history, file timestamps, และ code analysis*  
*สร้างเมื่อ: 10 มีนาคม 2569*  
*อัปเดตล่าสุด: 19 มีนาคม 2569 — เพิ่ม Phase 23 (Cross-Reference 4 แหล่งข้อมูล)*
