# CLAUDE.md

## Project structure (โครงสร้างโปรเจกต์)

- `election-verification/` (หลัก)
  - `data/` - JSON, OCR results, drive indexes, cross-reference, anomaly flags
  - `scripts/` - utility สำหรับ analysis, postprocessing, export, cross-reference
  - `cloud/` - Google Cloud Functions (OCR worker), dispatch, collect, retry, deploy scripts
  - `review-app/` - React frontend สำหรับ citizen review + analytics (port 3000)
    - `src/components/` - 15 React components
    - `src/hooks/` - useThailandMap.js, useDarkMode.js
    - `src/utils/` - validation.js, reviewLog.js, submitReview.js
    - `public/data/` - review_data.json, anomaly_flags.json, backup_status.json, cross_reference_sources.json, thailand-provinces.topojson
  - `docs/` - static citizen review UI (GitHub Pages)
  - `assets/` - ไฟล์สื่อ/สไตล์
  - `README.md` v4.0, `SECURITY.md`, `.githooks/pre-commit`

- สถิติสำคัญ (Phase 46):
  - Python scripts 180+, React components 15+, unit tests 115+, data files 60+
  - OCR records **17,628** (3 จังหวัด), coverage **99.6%** (14,228/14,292 front pages)
  - PDF 149,936 ไฟล์ (77 จังหวัด บน Google Drive) + single-page **7,975+** ไฟล์ (99.97%)
  - Review items **9,095** (deployed), vote type classification **99.99%**
  - Cloud Function (Gemini OCR, Gen2, 2048MB, asia-southeast1)
  - Git commits 40+, Dashboards 7, Development **381+ ชั่วโมง** (51 วัน)

---

## OCR pipeline (สายงาน OCR)

1. **Data source discovery**
   - ค้นหา PDF สส.5/16 / สส.5/18 จากเว็บ กกต. จ.ต่าง ๆ
   - `crawl_province_docs.py`, `extract_doc_links.py`, `download_ss518.py`
   - URL pattern: `https://www.ect.go.th/{slug}/th/election-2026`

2. **Initial OCR evaluation**
   - Tesseract (ไม่ดี) → Google Cloud Vision (ดีกว่า) → Gemini Flash (ดีที่สุด)
   - `ocr_ss518.py`, `ocr_ss518_v2.py`, `ocr_cloud_vision.py`

3. **Drive staging**
   - อัปโหลด PDF ไป Google Drive (`download_to_drive.py`, `build_drive_index.py`)
   - แยก page-level (single-page upload) เพื่อให้ ReviewCard แสดงหน้าที่ถูกต้อง
   - `scripts/split_and_upload.py` → 7,975+ single-page PDFs (99.97%)

4. **Multi-model extraction**
   - `ocr_multimodel.py` + `cloud/function/main.py` + `cloud/ocr_local.py`
   - Model chain: `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.0-flash-lite` (fallback)
   - Dynamic prompt: `build_prompt(meta, page_num, total_pages)` — ป้องกัน multi-station confusion
   - JSON repair (`_repair_json`), adaptive DPI (200→150→100), page-level resume

5. **Distributed Cloud dispatch**
   - `cloud/dispatch.py`, `cloud/dispatch_missing.py`, `cloud/dispatch_slow.py`
   - `cloud/collect.py` — collect + merge จาก GCS bucket `election69-ocr-results-th`
   - `cloud/retry_503.py` — retry เฉพาะ 503 errors (เพิ่ม CF memory 512MB→2048MB แก้ปัญหา)
   - Error classification: 503 (retryable) vs 502 PDF download failed (ถาวร)

6. **Postprocessing**
   - `postprocess.py` (generalized, `--province` flag) — 9+ กฎ:
     - R0a: fix metadata จาก filepath | R0b: fix station_no จาก filepath
     - R0c: dedup exact duplicates | R0d: dedup interleaved (combined PDF)
     - R3: fix total_votes | R4: fix remaining_ballots | R5: fix negative values
     - R6: fix outliers | R7: normalize candidates (fuzzy match กับ ECT reference)
     - R8: flag turnout > registered_voters | R9: fix candidate vote outliers
   - cross-validate กับ Killernay ground truth

7. **Validation & QA**
   - 11 กฎตรวจสอบ (`validation.js`) — V1 error → V11 warning
   - Anomaly flags (76 เขต, 5 หมวด, severity high/medium/low)
   - Cross-reference 4 แหล่ง: OCR / กกต. / Killernay / Luengnat
   - `verify_data_integrity.py` — ตรวจ OCR ↔ drive index consistency

---

## React Review App — Component Map

| Component | หน้าที่ |
|-----------|--------|
| `ReviewCard` | แสดง OCR record + PDF iframe + validation warnings + anomaly banner |
| `FilterBar` | ค้นหา/กรอง ตามสถานะ/จังหวัด/เขต/vote_type |
| `StatsBar` | แสดงสถิติรวม + progress bar |
| `CandidateTable` | ตารางคะแนนผู้สมัคร |
| `FieldRow` | แถวข้อมูลแต่ละ field พร้อม highlight ปัญหา |
| `DataStatsPanel` | สถิติต่อจังหวัด/เขต, PDF status, anomaly summary |
| `BackupDashboard` | สถานะ backup 77 จังหวัด + SVG Thailand map |
| `AnalyticsDashboard` | Donut/bar charts สถานะ review, validation breakdown, timeline |
| `ProvinceHeatmap` | SVG choropleth map (d3-geo + TopoJSON) แสดง % ความคืบหน้า |
| `ReviewerLeaderboard` | สถิติผู้ตรวจ + ranking 🥇🥈🥉 |
| `CrossReferencePanel` | เปรียบเทียบ 4 แหล่งข้อมูล, 401 เขต, bar chart diff |
| `AdminPanel` | จัดการ review log, merge, import/export |
| `UploadPanel` | อัปโหลด JSON/CSV review data |
| `AuthGate` | Google Sign-In wrapper |
| `ErrorBoundary` | React Error Boundary ครบ 10/10 components |

Hooks: `useThailandMap` (d3-geo, TopoJSON, 77 จังหวัด mapping), `useDarkMode` (localStorage + system pref)

---

## Current progress (สถานะปัจจุบัน — Phase 46)

### OCR Completion (Phase 32)

| จังหวัด | ไฟล์ PDF | OCR records | Front pages | ความสมบูรณ์ |
|---------|---------|------------|-------------|------------|
| ชัยภูมิ | 263 | 5,895 | 5,595/5,595 | **100.0%** ✅ |
| ตาก | 1,080 | 3,770 | 2,326/2,335 | **99.6%** ✅ |
| เพชรบูรณ์ | 1,106 | 7,963 | 6,307/6,362 | **99.1%** ✅ |
| **รวม** | **2,449** | **17,628** | **14,228/14,292** | **99.6%** |

หน้าที่เหลือ 64 หน้า = หน้าลายเซ็น/ว่าง/ปก หรือ PDF คุณภาพต่ำที่ Gemini อ่านไม่ได้ (ไม่ใช่ error)

### ต้นทุน OCR
- Gemini API: ~$10.88 | Cloud Functions: ~$3.25 | **รวม ~$14.14 ($0.0011/page)**

### Review App (GitHub Pages)
- 9,095 review items (3 จังหวัด), dark mode, code splitting (bundle 234KB)
- 115 unit tests passed, 10/10 error boundaries, 7/7 leaf components memoized
- Priority queue (anomaly-first), auto-approve low-risk, bulk confirm (Ctrl+B)
- Keyboard shortcuts: J/K navigate, 1/2/3/R status, Ctrl+A/B/P, Shift+A

### Security
- API key: `.env` + `.gitignore` + pre-commit hook (`scan AIzaSy pattern`)
- Cloud Function: อ่าน key จาก env vars เท่านั้น

---

## Remaining open work (งานที่เหลือ)

1. **64 หน้าที่ยังขาด** — หน้าลายเซ็น/ว่าง/ปก หรือ PDF คุณภาพต่ำ (ไม่ใช่ error)

2. **full-province scaling** (beyond 3 provinces → 77 จังหวัด)
   - ตรวจสอบ `postprocess.py` generalization รับ 77 provinces
   - ปรับขนาด dispatcher, GCS buckets, province mapping
   - ประมาณ OCR cost: 149,936 PDFs × $0.0011 ≈ $165

3. **data quality / accuracy metric สำหรับบทความ**
   - เสริม metric pipeline: bias per candidate, outlier thresholds
   - OCR error breakdown, cost/accuracy tradeoff analysis

4. **review throughput & crowdsourcing**
   - ขยาย citizen review ให้รองรับหลายจังหวัด
   - consensus model: 1/2/3 reviewers → low/medium/high trust

---

## Key architectural decisions & lessons learned

1. **กกต. ไม่เปิด station-level API** → ต้อง OCR จาก PDF ลายมือ → โปรเจกต์นี้เป็นโครงการ **เดียว** ที่มีข้อมูลระดับหน่วยเลือกตั้ง
2. **Dynamic prompt** (`build_prompt(meta, page_num, total_pages)`) แก้ปัญหา multi-station PDF อ่าน constituency ผิด (error 249.6% → 40.3%)
3. **Always-override metadata** จาก file path — ไม่ไว้ใจ OCR สำหรับ province/constituency
4. **Interleaved combined PDFs** เป็นสาเหตุ duplicate → ต้องมี R0d dedup
5. **Cloud Function memory** 512MB ไม่พอ PDF ขนาดใหญ่ → upgrade 2048MB แก้ 503 errors
6. **API key leak** จาก hardcoded ใน `_deploy.cmd` → ต้องมี pre-commit hook scan `AIzaSy`
7. **SVG choropleth** ด้วย d3-geo + TopoJSON (lazy-load) แทน grid heatmap → UX ดีขึ้นมาก
8. **Code splitting** React.lazy บน 8 heavy components → main bundle 382KB → 234KB (-39%)
9. **CSS-based dark mode** ด้วย Tailwind `darkMode: 'class'` + global CSS — ไม่ต้องแก้ทุก component

---

## Notes

- โครงการพัฒนา 51 วัน (12 ก.พ. – 3 เม.ย. 2569) รวม ~381+ ชั่วโมง, 46 phases
- ผู้พัฒนา: narasak poophayang
- อัปเดตล่าสุด: 4 เมษายน 2569
