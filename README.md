# Election Verification System

Open-source system for verifying Thailand's 2026 general election results by OCR-ing official station-level tally sheets (Form สส.5/16, สส.5/18) and cross-referencing with ECT (Election Commission of Thailand) digital data.

**Live Demo:** [narasakp.github.io/election-verification](https://narasakp.github.io/election-verification/)

---

## Overview

| Metric | Value |
|--------|-------|
| PDF documents scraped | 149,936 (77 provinces) |
| Provinces with OCR | 3 (Chaiyaphum, Tak, Phetchabun) |
| OCR records | 12,376 |
| Review items | 6,111 |
| React components | 5 |
| Python scripts | 60+ |
| Total dev hours | 256+ |

### What this project does

1. **Scrape** official election tally PDFs from all 77 ECT provincial websites
2. **Back up** all PDFs to Google Drive (149,936 files)
3. **OCR** handwritten Thai documents using multi-model AI (Gemini Flash, Cloud Vision, Claude)
4. **Postprocess** with a 9-rule pipeline to fix OCR errors and normalize data
5. **Cross-validate** against ECT digital results and Killernay ground truth
6. **Detect anomalies** across 8 statistical dimensions (turnout, invalid ballots, etc.)
7. **Citizen review** via React web app with Google Sign-In authentication

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

## Architecture

```
ECT Provincial Websites (77 provinces)
        |
        | download_ss518.py
        v
Google Drive (149,936 PDFs, 77 provinces)
        |
        | split_and_upload.py → single-page PDFs
        | build_drive_index.py
        v
OCR Pipeline
  ├── Gemini Flash (primary)
  ├── Gemini Flash-Lite (fallback)
  └── Cloud Vision + rule-based parser
        |
        | ocr_multimodel.py
        v
Postprocessing Pipeline (9 rules)
  R0a/b → R0c/d → R3/R4 → R5/R6 → R7 → R8/R9 → cross-val
        |
        v
React Review App (GitHub Pages)
  ├── ReviewCard — OCR data + PDF side-by-side
  ├── DataStatsPanel — statistics & quality metrics
  ├── BackupDashboard — Google Drive backup status
  ├── CandidateTable — candidate vote comparison
  └── Anomaly flags with incomplete-data awareness
```

---

## Project Structure

```
election-verification/
├── review-app/                # React Review App (Vite + TailwindCSS)
│   ├── src/
│   │   ├── App.jsx            # Main app with filters, pagination, review logic
│   │   ├── components/
│   │   │   ├── ReviewCard.jsx      # OCR data display + PDF viewer
│   │   │   ├── DataStatsPanel.jsx  # Stats dashboard + anomaly summary
│   │   │   ├── BackupDashboard.jsx # Google Drive backup status
│   │   │   └── CandidateTable.jsx  # Candidate vote table
│   │   ├── hooks/
│   │   │   └── useAuth.js     # Google Sign-In authentication
│   │   └── utils/
│   │       ├── validation.js  # Data validation rules
│   │       └── reviewLog.js   # Review state management
│   └── public/data/           # Static JSON data files
│       ├── review_data.json   # OCR results for review
│       ├── anomaly_flags.json # Anomaly detection results
│       └── backup_status.json # Drive backup status
│
├── scripts/                   # Python processing scripts
│   ├── download_ss518.py      # Scrape PDFs from ECT websites
│   ├── ocr_multimodel.py      # Multi-model OCR pipeline
│   ├── ocr_cloud_vision.py    # Cloud Vision OCR + parser
│   ├── postprocess.py         # 9-rule postprocessing pipeline
│   ├── prepare_review_data.py # Generate review JSON
│   ├── analyze_anomalies.py   # 8-dimension anomaly detection
│   ├── backup_to_drive.py     # Upload PDFs to Google Drive
│   ├── split_and_upload.py    # Split multi-page PDFs
│   ├── build_drive_index.py   # Index Drive files
│   ├── dashboard.py           # Backup status dashboard (port 8899)
│   └── ...                    # Various analysis & utility scripts
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
├── DEVELOPMENT_LOG.md         # Detailed development history (20 phases)
├── SECURITY.md                # API key security guide
└── README.md                  # This file
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TailwindCSS, Lucide icons |
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

### 9-Rule Postprocessing Pipeline
- **R0a/R0b**: Metadata extraction from file paths
- **R0c/R0d**: Deduplication (interleaved combined PDFs)
- **R3/R4**: Vote total validation and repair
- **R5/R6**: Ballot count consistency (with safety checks)
- **R7**: Candidate normalization via ECT reference
- **R8/R9**: Confidence scoring and flagging
- **Cross-validation**: Against Killernay ground truth data

### Anomaly Detection (8 dimensions)
- Turnout rate outliers (z-score + IQR)
- Invalid ballot ratio
- Blank ballot ratio
- Wasted vote ratio
- Candidate dominance
- Total vote vs ballot mismatch
- Registered voter anomalies
- Counting completeness awareness (filters unreliable flags from incomplete data)

### React Review App
- Side-by-side PDF viewer + OCR data
- Editable fields with validation
- Anomaly flags per item
- Google Drive backup status dashboard
- Province/constituency/search filters
- Keyboard shortcuts (J/K navigate)
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

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for the full 20-phase development history with commit hashes, problems, solutions, and results for each phase.

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

## Related Projects

| Project | Coverage | Form |
|---------|----------|------|
| **This project** | Station-level (สส.5/18) — 3 provinces | Handwritten tally sheets |
| [Killernay](https://github.com/killernay/election-69-OCR-result) | Constituency-level (สส.6/1) — nationwide | Summary forms |
| [Luengnat](https://luengnat.github.io/election-69-dashboard) | Constituency-level dashboard | ECT + Drive + Killernay |

---

## License

MIT License — free for educational and public interest use.

---

**Version:** 3.0  
**Last updated:** 18 March 2026
