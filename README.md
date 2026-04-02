# Election Verification System — ระบบตรวจสอบผลเลือกตั้ง 2569

Open-source system for verifying Thailand's 2026 general election results by OCR-ing official **station-level** tally sheets (Form สส.5/16, สส.5/18) and cross-referencing with ECT digital data, Killernay, and Luengnat datasets.

ระบบโอเพนซอร์สสำหรับตรวจสอบผลการเลือกตั้ง 2569 โดยแปลง PDF แบบ สส.5/18 (ระดับหน่วยเลือกตั้ง) ด้วย OCR แล้วเปรียบเทียบกับข้อมูลดิจิทัลจาก กกต., Killernay และ Luengnat

**🌐 Live Demo:** [narasakp.github.io/election-verification](https://narasakp.github.io/election-verification/)  
**📂 Google Drive Backup:** [149,936 PDFs — 77 จังหวัด](https://drive.google.com/drive/u/0/folders/14TWIziWEesoRiyii38yvVA5gVFC4joNm)

---

## ⚠️ Disclaimer

This dataset is produced through OCR processing with multi-model AI cross-validation. We do **not** alter, modify, or manipulate any election data. This is an independent volunteer civic effort to help digitize official election results published by the Election Commission of Thailand (กกต.). All processing costs are self-funded — this project has **no affiliation** with any business, political party, or organization.

For official and authoritative results, please always refer to the original documents from กกต.

## ⚠️ ข้อสงวนสิทธิ์

ข้อมูลชุดนี้สร้างจาก OCR โดยผ่านการตรวจสอบความถูกต้องข้ามระบบ (cross-validation) ด้วย AI หลายตัว เราไม่มีส่วนเกี่ยวข้องในการแก้ไข ดัดแปลง หรือบิดเบือนข้อมูลผลการเลือกตั้งใดๆ ทั้งสิ้น

โครงการนี้จัดทำขึ้นโดยสมัครใจเพื่อช่วย กกต. ในการ digitize ผลการเลือกตั้งอย่างเป็นทางการ ค่าใช้จ่ายทั้งหมดเป็นทุนส่วนตัว — โครงการนี้ **ไม่มีความเกี่ยวข้อง** กับธุรกิจ พรรคการเมือง หรือองค์กรใดๆ

สำหรับผลการเลือกตั้งที่เป็นทางการ กรุณาอ้างอิงจากเอกสารต้นฉบับของ กกต. เสมอ

---

## 📊 Data Coverage / ความครอบคลุมของข้อมูล

### ตัวเลขสำคัญ

| Metric | Value |
|--------|-------|
| PDF ที่ดาวน์โหลดจาก กกต. | **149,936** ไฟล์ (77 จังหวัดครบ) |
| สำรองข้อมูลบน Google Drive | **149,936** / 147,603 ที่คาดไว้ (101.6%) |
| จังหวัดที่ผ่าน OCR | **3** จังหวัด (ชัยภูมิ, ตาก, เพชรบูรณ์) |
| เขตเลือกตั้งที่มี OCR | **16** เขต |
| รายการ OCR (records) | **17,628** records |
| รายการรอตรวจสอบ (review items) | **10,238** items |
| Single-page PDF splits | **5,357+** ไฟล์ (ชัยภูมิ+ตากครบ 100%, เพชรบูรณ์กำลังดำเนินการ) |
| แหล่งข้อมูล Cross-Reference | **4** แหล่ง (OCR ของเรา, กกต., Killernay, Luengnat) |
| เขตเลือกตั้งใน Cross-Reference | **401** เขต (ทั้งแบ่งเขต + บัญชีรายชื่อ) |
| Python scripts | **172+** scripts |
| ชั่วโมงพัฒนา | **316+** ชั่วโมง |

### จุดเด่นของโครงการนี้ — Station-Level OCR

| | โครงการนี้ | Killernay | Luengnat |
|---|---|---|---|
| **แบบฟอร์ม** | สส.5/18 (ระดับหน่วย) | สส.6/1 (ระดับเขต) | สส.6/1 (ระดับเขต) |
| **ความละเอียด** | **สถานี/หน่วยเลือกตั้ง** | เขตเลือกตั้ง | เขตเลือกตั้ง |
| **ครอบคลุม** | 3 จังหวัด (กำลังขยาย) | 397/400 เขต | 400 เขต |
| **PDF ต้นทาง** | 149,936 ไฟล์ (77 จว.) | 776 ไฟล์ | — |
| **ข้อมูลระดับหน่วย** | ✅ มี | ❌ ไม่มี | ❌ ไม่มี |
| **Cross-validation** | 4 แหล่ง | Reporter DB | ECT + Killernay |

> **ข้อมูลระดับหน่วยเลือกตั้ง (station-level)** ไม่มีในโครงการอื่น — เฉพาะโครงการนี้เท่านั้นที่ OCR จาก แบบ สส.5/18 ซึ่งมีรายละเอียดคะแนนแยกตามหน่วยเลือกตั้ง

## ⚠️ PDF Source Quality Issues / ปัญหาคุณภาพไฟล์ต้นทาง

PDF จาก กกต. ทั้งหมดเป็น **scanned images** (ไม่มี text layer) ต้อง OCR ทั้งหมด ทำให้เกิดข้อผิดพลาดได้หลายจุด:

- **ลายมือเขียน** — แบบ สส.5/18 เป็นเอกสารเขียนมือ ไม่ใช่พิมพ์ OCR accuracy ต่ำกว่า printed text มาก
- **คุณภาพสแกน** — บางไฟล์เบลอ หมุน หรือถ่ายเอียง
- **หลายหน่วยต่อไฟล์** — PDF ไฟล์เดียวรวมข้อมูลหลายสถานี (10+ หน่วย) ทำให้ OCR สับสนเลขเขต
- **ชื่อไฟล์ไม่ตรง** — บางจังหวัดตั้งชื่อไฟล์ไม่ตรงกับเนื้อหา

> สรุป: Scanned PDF ≠ Digital data — หากต้องการข้อมูล 100% ต้องสร้าง PDF จากระบบดิจิทัลโดยตรง

---

## 🔗 Cross-Reference — เปรียบเทียบ 4 แหล่งข้อมูล

ระบบนี้เปรียบเทียบข้อมูลจาก **4 แหล่ง** พร้อมกัน เพื่อตรวจหาความคลาดเคลื่อน:

| แหล่งข้อมูล | รายละเอียด | จำนวน records |
|---|---|---|
| **🔬 ระบบ OCR ของเรา** | OCR จาก สส.5/18 — 3 จังหวัด (ชัยภูมิ, ตาก, เพชรบูรณ์) | 16 เขต |
| **🏛 กกต. (ECT Official)** | ข้อมูลดิจิทัลจาก ectreport69.ect.go.th | 400 เขต |
| **📊 Killernay** | OCR จาก สส.6/1 — cross-validated กับ Reporter DB | 397 เขต |
| **📊 Luengnat** | Dashboard รวม ECT + Drive + Killernay | 400 เขต |

### ผลการเปรียบเทียบ (Cross-Reference Panel)

- **401 เขตเลือกตั้ง** (constituency + party-list)
- แสดงคะแนนรวมเทียบกันจากทุกแหล่ง
- ตรวจจับ **Error** (ข้อมูลไม่ตรงอย่างมีนัยสำคัญ) และ **Warning** (ส่วนต่างเล็กน้อย)
- สามารถกรองตามจังหวัด, เขต, สถานะ

---

## What this project does / สิ่งที่โครงการนี้ทำ

1. **📥 Scrape** — ดาวน์โหลด PDF แบบ สส.5/18 จากเว็บไซต์ กกต. ทั้ง 77 จังหวัด
2. **☁️ Backup** — สำรองข้อมูลทั้งหมด 149,936 ไฟล์ไปยัง [Google Drive](https://drive.google.com/drive/u/0/folders/14TWIziWEesoRiyii38yvVA5gVFC4joNm)
3. **🤖 OCR** — แปลงเอกสารลายมือด้วย AI หลายรุ่น (Gemini Flash, Cloud Vision, Claude)
4. **🔧 Postprocess** — แก้ไข OCR errors ด้วย pipeline 9 กฎ
5. **🔍 Cross-validate** — เปรียบเทียบกับ กกต., Killernay, Luengnat
6. **📊 Detect anomalies** — ตรวจจับความผิดปกติ 8 มิติ
7. **👥 Citizen review** — ตรวจสอบโดยประชาชนผ่าน React web app

---

## Quick Start

### View the Review App (no setup needed)

Visit [narasakp.github.io/election-verification](https://narasakp.github.io/election-verification/) to browse OCR results, view scanned PDFs, and check anomaly flags.

### Run locally

```bash
# Clone
git clone https://github.com/narasakp/election-verification.git
cd election-verification

# Setup API keys
cp .env.example .env
# Edit .env with your API keys (see .env.example for details)

# Install Python dependencies
pip install -r requirements.txt

# Run the React Review App
cd review-app
npm install
npm run dev -- --port 3000
# Open http://localhost:3000
```

### Run OCR pipeline

```bash
# OCR a province (requires Gemini API key)
python scripts/ocr_multimodel.py --province chaiyaphum --all --resume

# Postprocess OCR results
python scripts/postprocess.py --province chaiyaphum

# Generate review data for the React app
python scripts/prepare_review_data.py
```

---

## 🛠️ Processing Pipeline

```
เว็บไซต์ กกต. 77 จังหวัด
        │
        │  download_ss518.py (scrape 149,936 PDFs)
        ▼
Google Drive Backup (149,936 ไฟล์ / 77 จังหวัด)
        │
        │  split_and_upload.py → แยกเป็น PDF หน้าเดียว
        │  build_drive_index.py
        ▼
OCR Pipeline (Multi-Model)
  ├── Gemini Flash (primary)
  ├── Gemini Flash-Lite (fallback)
  └── Cloud Vision + rule-based parser
        │
        │  ocr_multimodel.py → 12,376 records
        ▼
Postprocessing Pipeline (9 กฎ)
  R0a/b  →  Metadata จาก file path
  R0c/d  →  Deduplication
  R3/R4  →  Vote total validation
  R5/R6  →  Ballot count consistency
  R7     →  Candidate normalization (ECT reference)
  R8/R9  →  Confidence scoring + flagging
        │
        ▼
Cross-Validation (4 แหล่ง)
  ├── เทียบกับ กกต. (ECT Official) — 400 เขต
  ├── เทียบกับ Killernay — 397 เขต
  └── เทียบกับ Luengnat — 400 เขต
        │
        ▼
React Review App (GitHub Pages)
  ├── ReviewCard — OCR + PDF เคียงข้าง
  ├── CrossReferencePanel — เปรียบเทียบ 4 แหล่ง
  ├── DataStatsPanel — สถิติ + anomaly
  ├── BackupDashboard — แผนที่คุณภาพข้อมูล
  ├── ProvinceHeatmap — แผนที่ความคืบหน้า
  └── CandidateTable — ตารางคะแนนผู้สมัคร
```

---

## 🔍 Quality Assurance / การตรวจสอบคุณภาพ

### 1. Multi-Model Cross-Validation
- OCR ด้วย **3 AI models** พร้อม fallback อัตโนมัติ
- **Self-consistency checks** — OCR ซ้ำด้วย temperature ต่างกัน เปรียบเทียบผลลัพธ์

### 2. Postprocessing Pipeline (9 กฎ)
- **R0a/R0b**: ดึง metadata จาก file path (จังหวัด, เขต, ประเภท)
- **R0c/R0d**: ลบข้อมูลซ้ำ (deduplication) จาก combined PDFs
- **R3/R4**: ตรวจสอบและแก้ไขยอดรวมคะแนน
- **R5/R6**: ตรวจสอบจำนวนบัตร (ได้รับ/ดี/เสีย/ไม่ลง) พร้อม safety checks
- **R7**: ปรับชื่อผู้สมัครให้ตรงกับฐานข้อมูล กกต.
- **R8/R9**: ให้คะแนนความเชื่อมั่น + ตั้ง flag
- **Cross-validation**: เทียบกับ Killernay ground truth

### 3. Anomaly Detection (8 มิติ)
- อัตราการใช้สิทธิ (turnout) — z-score + IQR
- อัตราบัตรเสีย (invalid ballot ratio)
- อัตราบัตรไม่ประสงค์ลงคะแนน (blank ballot ratio)
- อัตราคะแนนสูญเปล่า (wasted vote ratio)
- ความครอบงำของผู้สมัคร (candidate dominance)
- คะแนนรวม vs จำนวนบัตร (vote-ballot mismatch)
- ผู้มีสิทธิเลือกตั้งผิดปกติ (registered voter anomalies)
- ความครบถ้วนของข้อมูล (completeness-aware filtering)

### 4. Cross-Reference (4 แหล่ง)
- เปรียบเทียบข้อมูลระดับเขตจาก **4 แหล่งอิสระ** พร้อมกัน
- ตรวจจับ Error / Warning อัตโนมัติ
- แสดงค่า MAX DIFF เพื่อระบุความเชื่อถือได้

### Known Limitations
- OCR จากเอกสารลายมือมีความแม่นยำต่ำกว่า printed text
- PDF หลายหน่วยต่อไฟล์ทำให้ constituency number อาจผิดพลาด (แก้ด้วย metadata override)
- ครอบคลุมเพียง 3 จังหวัดสำหรับ station-level OCR (กำลังขยาย)

---

## Project Structure

```
election-verification/
├── review-app/                # React Review App (Vite + TailwindCSS)
│   ├── src/
│   │   ├── App.jsx            # Main app with filters, pagination, review logic
│   │   ├── components/
│   │   │   ├── ReviewCard.jsx          # OCR data display + PDF viewer
│   │   │   ├── CrossReferencePanel.jsx # Cross-reference 4 data sources
│   │   │   ├── DataStatsPanel.jsx      # Stats dashboard + anomaly summary
│   │   │   ├── BackupDashboard.jsx     # Google Drive backup + Thailand map
│   │   │   ├── ProvinceHeatmap.jsx     # Province review progress map
│   │   │   └── CandidateTable.jsx      # Candidate vote table
│   │   ├── hooks/
│   │   │   └── useAuth.js     # Google Sign-In authentication
│   │   └── utils/
│   │       ├── validation.js  # Data validation rules
│   │       └── reviewLog.js   # Review state management
│   └── public/
│       ├── data/              # Static JSON data files
│       │   ├── review_data.json              # OCR results (6,111 items)
│       │   ├── anomaly_flags.json            # Anomaly detection results
│       │   ├── backup_status.json            # Drive backup status (77 จังหวัด)
│       │   └── cross_reference_sources.json  # Cross-ref 4-source data (401 เขต)
│       └── thailand-provinces.topojson       # Thailand map geometry
│
├── scripts/                   # Python processing scripts (60+)
│   ├── download_ss518.py          # Scrape PDFs from ECT websites
│   ├── ocr_multimodel.py          # Multi-model OCR pipeline
│   ├── ocr_cloud_vision.py        # Cloud Vision OCR + parser
│   ├── postprocess.py             # 9-rule postprocessing pipeline
│   ├── prepare_review_data.py     # Generate review JSON
│   ├── prepare_cross_reference.py # Generate cross-reference data
│   ├── analyze_anomalies.py       # 8-dimension anomaly detection
│   ├── backup_to_drive.py         # Upload PDFs to Google Drive
│   ├── split_and_upload.py        # Split multi-page PDFs
│   ├── build_drive_index.py       # Index Drive files
│   └── ...                        # Various analysis & utility scripts
│
├── cloud/                     # Cloud Function for distributed OCR
│   ├── function/main.py       # Cloud Function entry point
│   ├── dispatch.py            # Parallel task dispatcher
│   └── deploy.ps1             # Deployment script
│
├── data/                      # Data files (large, not in git)
├── .github/workflows/
│   └── deploy.yml             # CI/CD: auto-deploy to GitHub Pages
│
├── .env.example               # API key template
├── DEVELOPMENT_LOG.md         # Detailed development history (35 phases)
├── SECURITY.md                # API key security guide
└── README.md                  # This file
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TailwindCSS, Lucide icons, d3-geo |
| **Maps** | TopoJSON, d3-geo (SVG choropleth maps of Thailand) |
| **Auth** | Google Identity Services (GIS), Google Forms |
| **OCR** | Gemini Flash/Flash-Lite, Cloud Vision API, Claude |
| **Backend** | Python 3.7+, Google Cloud Functions |
| **Storage** | Google Drive API, Google Cloud Storage |
| **Deploy** | GitHub Pages, GitHub Actions CI/CD |
| **Data** | Static JSON (zero-backend architecture) |

---

## Key Features

### Multi-Model OCR Pipeline
- **3 AI models** with automatic fallback: Gemini Flash → Flash-Lite → Cloud Vision
- **Adaptive DPI** for large PDFs (200 → 150 → 100)
- **Self-consistency checks** with temperature variation
- **JSON repair** for malformed API responses
- **Incremental save** — resume interrupted batches
- **Dynamic prompts** with metadata context for multi-station PDFs

### React Review App
- Side-by-side PDF viewer + OCR data
- **Cross-Reference Panel** — เปรียบเทียบ 4 แหล่งข้อมูลพร้อมกัน
- **Thailand choropleth map** — แผนที่แสดงคุณภาพข้อมูลและความคืบหน้า
- Editable fields with validation
- Anomaly flags per item (8 มิติ)
- Google Drive backup status dashboard (77 จังหวัด)
- Province/constituency/search filters
- Keyboard shortcuts (J/K navigate, 1/2/3 set status)
- Google Sign-In for verified reviews
- CSV/JSON export
- Auto-deploy via GitHub Actions

---

## Security

See [SECURITY.md](SECURITY.md) for detailed API key management guidelines.

**Quick checklist:**
- [ ] API keys in `.env` only (never commit)
- [ ] Budget alert set in Google Cloud Console
- [ ] API key restricted to specific APIs + IPs
- [ ] Gemini API daily quota configured
- [ ] Cloud Function uses IAM authentication

---

## Development

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for the full 35-phase development history with commit hashes, problems, solutions, and results for each phase.

### Running tests

```bash
cd review-app
npm test
```

### Building for production

```bash
cd review-app
npm run build
# Output in review-app/dist/
```

### Deployment

Push to `main` branch triggers automatic deployment to GitHub Pages via GitHub Actions.

---

## 🔗 Related Projects / โครงการที่เกี่ยวข้อง

| Project | Description | Coverage | Form | Link |
|---------|-----------|----------|------|------|
| **This project** | Station-level OCR + cross-validation | 3 จว. (station) / 77 จว. (backup) | สส.5/18 | [Live Demo](https://narasakp.github.io/election-verification/) |
| **Killernay** | Constituency-level OCR + Reporter DB match | 397/400 เขต | สส.6/1 | [GitHub](https://github.com/killernay/election-69-OCR-result) |
| **Luengnat** | Constituency-level dashboard + verification | 400 เขต | ECT + Drive + Killernay | [Dashboard](https://luengnat.github.io/election-69-dashboard/) |

---

## 📄 Data Source / แหล่งข้อมูลต้นฉบับ

- **แบบ สส.5/18** — ใบสรุปผลคะแนนระดับหน่วย/สถานี จากสำนักงาน กกต. จังหวัด
- **ECT Digital Data** — [ectreport69.ect.go.th](https://static-ectreport69.ect.go.th/data/records/stats_cons.json)
- **เว็บไซต์ กกต.** — [www.ect.go.th](https://www.ect.go.th) (77 จังหวัด)
- **Killernay OCR** — [github.com/killernay/election-69-OCR-result](https://github.com/killernay/election-69-OCR-result)
- **Luengnat Dashboard** — [luengnat.github.io/election-69-dashboard](https://luengnat.github.io/election-69-dashboard/)

---

## 📌 Attribution / การอ้างอิง

If you use this dataset or code, please credit:

**Narasak Phuphayang** — or link back to this repository: [election-verification](https://github.com/narasakp/election-verification)

หากนำข้อมูลหรือโค้ดไปใช้ กรุณาให้เครดิต **นายนรศักดิ์ ภูผายาง** หรืออ้างอิงกลับมาที่ repository นี้

---

## 🐛 Found an Error? / พบข้อผิดพลาด?

If you find any inaccuracies in the data, please report via:

- **GitHub Issues**: [Open an issue](https://github.com/narasakp/election-verification/issues)

หากพบข้อผิดพลาดในข้อมูล สามารถแจ้งได้ที่ GitHub Issues — จะรีบตรวจสอบและแก้ไข

---

## 📜 License

MIT License — free for educational and public interest use.

This data is derived from publicly available official government documents published by กกต. The structured output (JSON/CSV) and source code are provided freely for public use.

---

**Version:** 4.0  
**Last updated:** 22 March 2026
