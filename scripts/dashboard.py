#!/usr/bin/env python3
"""
Dashboard สำหรับดูสถานะ ECT Backup — real-time จาก Google Drive
รัน: python scripts/dashboard.py
เปิด: http://localhost:8899

Hybrid approach:
  1) backup_progress.json — baseline counts (instant)
  2) Drive scan caches — expected counts per province
  3) Shallow Drive counting — actual counts (budgeted API calls, gradual)
"""
import json
import os
import sys
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

try:
    import httplib2
    import google_auth_httplib2
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("❌ pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token_dashboard.json"
CACHE_FILE = DATA_DIR / "dashboard_cache.json"
PROGRESS_FILE = DATA_DIR / "backup_progress.json"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DRIVE_ROOT_NAME = "สส.5_18_ข้อมูลเลือกตั้ง_2569"
SCAN_INTERVAL = 60          # seconds between scan cycles
PROVS_PER_CYCLE = 5         # deep-count this many provinces per cycle
MAX_API_PER_PROV = 25       # budget: max API calls per province deep-count

RANKING_ORDER = [
    "บุรีรัมย์", "ตาก", "ชัยภูมิ", "เพชรบูรณ์", "เพชรบุรี",
    "นครราชสีมา", "อุบลราชธานี", "พะเยา", "นครสวรรค์", "อ่างทอง",
    "อุทัยธานี", "สุรินทร์", "เลย", "สุพรรณบุรี", "ระยอง",
    "ศรีสะเกษ", "เชียงใหม่", "แพร่", "เชียงราย", "นครศรีธรรมราช",
    "สระแก้ว", "ชัยนาท", "สุโขทัย", "ระนอง", "ขอนแก่น",
    "ร้อยเอ็ด", "กาฬสินธุ์", "สกลนคร", "นครพนม", "ลำปาง",
    "แม่ฮ่องสอน", "กาญจนบุรี", "สตูล", "นราธิวาส",
    "กรุงเทพมหานคร", "พิจิตร", "สมุทรปราการ", "หนองบัวลำภู", "ปัตตานี",
    "พระนครศรีอยุธยา", "ลพบุรี", "สระบุรี", "ชลบุรี", "จันทบุรี",
    "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "นครนายก", "สงขลา",
    "ยโสธร", "อำนาจเจริญ", "บึงกาฬ", "นนทบุรี", "อุดรธานี",
    "หนองคาย", "มหาสารคาม", "มุกดาหาร", "ลำพูน", "อุตรดิตถ์",
    "น่าน", "กำแพงเพชร", "พิษณุโลก", "ประจวบคีรีขันธ์", "ราชบุรี",
    "นครปฐม", "สมุทรสาคร", "สมุทรสงคราม", "ปทุมธานี", "กระบี่",
    "พังงา", "ภูเก็ต", "สิงห์บุรี", "ชุมพร", "ตรัง",
    "พัทลุง", "ยะลา", "สุราษฎร์ธานี",
]


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------
def _retry_api(func, max_retries=5, base_delay=2):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err = str(e)
            retryable = any(c in err for c in [
                "500", "503", "429", "Internal", "Rate",
                "Errno", "BrokenPipe", "ConnectionReset",
                "timeout", "SSL", "Connection aborted",
            ])
            if retryable and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            raise


def authenticate():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ ไม่พบ {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())
    authed_http = google_auth_httplib2.AuthorizedHttp(
        creds, http=httplib2.Http(timeout=60)
    )
    return build("drive", "v3", http=authed_http)


def find_root_folder(svc):
    q = (
        f"name = '{DRIVE_ROOT_NAME}' and "
        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    r = _retry_api(lambda: svc.files().list(q=q, fields="files(id)", pageSize=5).execute())
    files = r.get("files", [])
    return files[0]["id"] if files else None


def list_folder(svc, folder_id):
    """List all items in a folder (paginated). Returns list of {id,name,mimeType}."""
    items, pt = [], None
    while True:
        r = _retry_api(
            lambda t=pt: svc.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000, pageToken=t,
            ).execute()
        )
        items.extend(r.get("files", []))
        pt = r.get("nextPageToken")
        if not pt:
            break
    return items


def shallow_count_pdfs(svc, folder_id, budget):
    """Count PDFs up to 2 levels deep with a limited API call budget.
    Returns (pdf_count, calls_used).
    """
    if budget <= 0:
        return 0, 0
    calls = 0
    count = 0
    # Level 1 — list province folder
    try:
        items = list_folder(svc, folder_id)
        calls += 1
    except Exception:
        return 0, 1
    subfolders = []
    for f in items:
        if f["mimeType"] == "application/vnd.google-apps.folder":
            subfolders.append(f["id"])
        elif f["name"].lower().endswith(".pdf"):
            count += 1
    # Level 2 — list each subfolder (constituencies)
    for sf_id in subfolders:
        if calls >= budget:
            break
        try:
            sub_items = list_folder(svc, sf_id)
            calls += 1
            for f in sub_items:
                if f["name"].lower().endswith(".pdf"):
                    count += 1
                elif f["mimeType"] == "application/vnd.google-apps.folder":
                    # Level 3 — just count the subfolder contents too
                    if calls < budget:
                        try:
                            l3 = list_folder(svc, f["id"])
                            calls += 1
                            count += sum(1 for x in l3 if x["name"].lower().endswith(".pdf"))
                        except Exception:
                            calls += 1
        except Exception:
            calls += 1
    time.sleep(0.3)
    return count, calls


def read_scan_cache(svc, file_id):
    """Download a _scan_cache_*.json file and return the item count."""
    try:
        content = _retry_api(lambda: svc.files().get_media(fileId=file_id).execute())
        data = json.loads(content)
        return len(data) if isinstance(data, list) else None
    except Exception:
        return None


def load_progress_file():
    """Read backup_progress.json for baseline actual counts."""
    result = {}
    if PROGRESS_FILE.exists():
        try:
            d = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            for r in d.get("results", []):
                prov = r.get("province")
                if not prov:
                    continue
                uploaded = r.get("uploaded", 0) or 0
                skipped = r.get("skipped", 0) or 0
                failed = r.get("failed", 0) or 0
                pdf_count = r.get("pdf_count", 0) or 0
                actual = uploaded + skipped
                exp = pdf_count if pdf_count > 0 else None
                pct = round(actual / exp * 100, 1) if exp and exp > 0 and actual > 0 else None
                comp = (failed == 0 and actual > 0) if actual > 0 else None
                result[prov] = {
                    "actual": actual,
                    "expected": exp,
                    "pct": pct,
                    "complete": comp,
                    "uploaded": uploaded,
                    "skipped": skipped,
                    "failed": failed,
                    "status": r.get("status", ""),
                    "source": "progress_file",
                }
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.scanning = False
        self.scan_progress = ""
        self.last_scan_ts = None
        self.scan_duration = 0
        self.provinces = {}   # {prov_name: {actual, expected, pct, complete, source, ...}}
        self.error = None
        self.deep_scan_idx = 0  # round-robin index for gradual deep scans
        self._load_cache()

    def _load_cache(self):
        if CACHE_FILE.exists():
            try:
                d = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                self.provinces = d.get("provinces", {})
                self.last_scan_ts = d.get("last_scan_ts")
                self.deep_scan_idx = d.get("deep_scan_idx", 0)
            except Exception:
                pass

    def save_cache(self):
        d = {
            "provinces": self.provinces,
            "last_scan_ts": self.last_scan_ts,
            "deep_scan_idx": self.deep_scan_idx,
        }
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def api_response(self):
        with self.lock:
            has_data = sum(1 for p in self.provinces.values() if p.get("actual", 0) > 0)
            complete = sum(1 for p in self.provinces.values() if p.get("complete"))
            total_a = sum(p.get("actual", 0) for p in self.provinces.values())
            total_e = sum(p.get("expected", 0) for p in self.provinces.values() if p.get("expected"))
            return json.dumps({
                "scanning": self.scanning,
                "scan_progress": self.scan_progress,
                "last_scan_ts": self.last_scan_ts,
                "scan_duration": self.scan_duration,
                "error": self.error,
                "summary": {
                    "has_data": has_data, "complete": complete,
                    "total": len(RANKING_ORDER),
                    "total_actual": total_a, "total_expected": total_e,
                    "pct": round(total_a / total_e * 100, 1) if total_e > 0 else 0,
                },
                "provinces": [
                    {"name": p, **(self.provinces.get(p) or {"actual": 0})}
                    for p in RANKING_ORDER
                ],
            }, ensure_ascii=False)


STATE = State()


# ---------------------------------------------------------------------------
# Scanner thread
# ---------------------------------------------------------------------------
def scanner_thread():
    # ── Phase 1: instant data from progress file ──
    print("📄 อ่าน backup_progress.json...", flush=True)
    prog = load_progress_file()
    if prog:
        with STATE.lock:
            for prov, info in prog.items():
                STATE.provinces[prov] = info
        print(f"  → {len(prog)} provinces from progress file", flush=True)

    # ── Phase 2: connect to Drive ──
    print("🔗 เชื่อมต่อ Google Drive...", flush=True)
    try:
        svc = authenticate()
    except Exception as e:
        print(f"❌ Auth failed: {e}", flush=True)
        with STATE.lock:
            STATE.error = f"Auth failed: {e}"
        return

    root_id = find_root_folder(svc)
    if not root_id:
        print(f"❌ ไม่พบ folder '{DRIVE_ROOT_NAME}'", flush=True)
        with STATE.lock:
            STATE.error = "Root folder not found"
        return
    print(f"📁 Root: {root_id}", flush=True)

    scan_count = 0
    while True:
        scan_count += 1
        t0 = time.time()
        with STATE.lock:
            STATE.scanning = True
            STATE.error = None

        try:
            # ── List root folder (1 API call) ──
            with STATE.lock:
                STATE.scan_progress = "listing root folder..."
            items = list_folder(svc, root_id)

            prov_folders = {}
            for it in items:
                if it["mimeType"] == "application/vnd.google-apps.folder":
                    prov_folders[it["name"]] = it["id"]
            print(f"  [scan #{scan_count}] {len(prov_folders)} province folders on Drive", flush=True)

            # ── Update folder existence for all provinces ──
            with STATE.lock:
                for prov in RANKING_ORDER:
                    prev = STATE.provinces.get(prov, {})
                    prev["has_folder"] = prov in prov_folders
                    STATE.provinces[prov] = prev

            # ── Shallow-count a batch of provinces ──
            needs_deep = []
            for prov in RANKING_ORDER:
                if prov not in prov_folders:
                    continue
                p = STATE.provinces.get(prov, {})
                if p.get("complete"):
                    continue  # already verified complete
                needs_deep.append(prov)

            if needs_deep:
                start_idx = STATE.deep_scan_idx % len(needs_deep)
                batch = []
                for i in range(PROVS_PER_CYCLE):
                    idx = (start_idx + i) % len(needs_deep)
                    if needs_deep[idx] not in batch:
                        batch.append(needs_deep[idx])

                print(f"  [scan] counting {len(batch)} provinces: {', '.join(batch)}", flush=True)
                for prov in batch:
                    with STATE.lock:
                        STATE.scan_progress = f"counting {prov}..."
                    try:
                        fid = prov_folders[prov]
                        drive_count, calls = shallow_count_pdfs(svc, fid, MAX_API_PER_PROV)
                        with STATE.lock:
                            prev = STATE.provinces.get(prov, {})
                            prev_actual = prev.get("actual", 0)
                            exp = prev.get("expected")
                            # Keep the higher count (progress file is authoritative,
                            # Drive shallow is partial due to depth limits)
                            actual = max(prev_actual, drive_count)
                            pct = round(actual / exp * 100, 1) if exp and exp > 0 else None
                            comp = (actual >= exp) if exp and actual > 0 else None
                            STATE.provinces[prov] = {
                                "actual": actual, "expected": exp,
                                "pct": pct, "complete": comp,
                                "source": "drive", "api_calls": calls,
                                "drive_count": drive_count,
                                "has_folder": True,
                            }
                        icon = "✅" if comp else "📂"
                        print(f"  {icon} {prov}: {actual}" + (f"/{exp}" if exp else "") + f" (drive:{drive_count}, {calls} calls)", flush=True)
                    except Exception as e:
                        print(f"  ⚠️ {prov}: {e}", flush=True)
                    time.sleep(0.5)

                with STATE.lock:
                    STATE.deep_scan_idx = (start_idx + PROVS_PER_CYCLE) % max(len(needs_deep), 1)
            else:
                print(f"  [scan] all provinces verified ✅", flush=True)

            dur = time.time() - t0
            with STATE.lock:
                STATE.last_scan_ts = time.time()
                STATE.scan_duration = dur
                STATE.save_cache()
            n_data = sum(1 for p in STATE.provinces.values() if p.get("actual", 0) > 0)
            n_comp = sum(1 for p in STATE.provinces.values() if p.get("complete"))
            n_drive = sum(1 for p in STATE.provinces.values() if p.get("source") == "drive")
            print(f"✅ Scan #{scan_count}: {n_data} with data, {n_comp} complete, {n_drive} verified ({dur:.0f}s)", flush=True)

        except Exception as e:
            with STATE.lock:
                STATE.error = str(e)[:100]
            print(f"⚠️ Scan error: {e}", flush=True)
        finally:
            with STATE.lock:
                STATE.scanning = False
                STATE.scan_progress = ""

        time.sleep(SCAN_INTERVAL)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ECT Backup Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap');
  body { font-family: 'Noto Sans Thai', sans-serif; }
  .bar-anim { transition: width 0.6s ease; }
  @keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:.3} }
  .pulse-dot { animation: pulse-dot 1.5s infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin { animation: spin 1s linear infinite; }
  tr:nth-child(even) { background-color: #f8fafc; }
</style>
</head>
<body class="bg-slate-50 text-gray-900 min-h-screen">
<div class="max-w-6xl mx-auto px-4 py-6">

  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold">&#128202; ECT Backup Dashboard</h1>
      <p class="text-gray-500 text-sm mt-1">&#x1F4C1; Hybrid: backup_progress + Drive scan caches + shallow count</p>
    </div>
    <div class="text-right space-y-1">
      <div id="scan-status" class="text-xs text-gray-400"></div>
      <div id="last-scan" class="text-xs text-gray-400"></div>
      <div class="text-xs text-blue-500">&#x1F504; Auto-refresh 10s</div>
    </div>
  </div>

  <!-- Error banner -->
  <div id="error-banner" class="hidden bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm"></div>

  <!-- Summary Cards -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
    <div class="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
      <div class="text-xs text-gray-500 uppercase tracking-wide font-semibold">&#x1F4C2; มีข้อมูล</div>
      <div class="text-3xl font-bold mt-1" id="has-data">-</div>
      <div class="text-xs text-gray-400 mt-1" id="has-data-sub">/ 77</div>
    </div>
    <div class="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
      <div class="text-xs text-gray-500 uppercase tracking-wide font-semibold">&#x2705; ครบ 100%</div>
      <div class="text-3xl font-bold text-emerald-600 mt-1" id="complete-count">-</div>
      <div class="text-xs text-gray-400 mt-1">verified complete</div>
    </div>
    <div class="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
      <div class="text-xs text-gray-500 uppercase tracking-wide font-semibold">&#x1F4C4; PDF ทั้งหมด</div>
      <div class="text-3xl font-bold mt-1" id="total-actual">-</div>
      <div class="text-xs text-gray-400 mt-1" id="total-expected-sub"></div>
    </div>
    <div class="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
      <div class="text-xs text-gray-500 uppercase tracking-wide font-semibold">&#x1F50D; Scan</div>
      <div class="text-3xl font-bold mt-1" id="scan-dur">-</div>
      <div class="text-xs text-gray-400 mt-1" id="scan-dur-sub"></div>
    </div>
  </div>

  <!-- Overall Progress -->
  <div class="bg-white rounded-xl p-4 border border-gray-200 shadow-sm mb-6">
    <div class="flex justify-between items-center mb-2">
      <span class="text-sm font-semibold text-gray-700">&#x1F4CA; ความคืบหน้ารวม (จากไฟล์จริงบน Drive)</span>
      <span class="text-sm text-gray-500 font-mono" id="pct-text">-</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-3">
      <div id="pct-bar" class="bar-anim bg-gradient-to-r from-blue-500 to-emerald-500 h-3 rounded-full" style="width:0%"></div>
    </div>
  </div>

  <!-- Province Table -->
  <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
    <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
      <h2 class="font-semibold text-gray-800">&#x1F3DB; รายจังหวัด (เรียงตามลำดับ anomaly)</h2>
      <div class="flex gap-2 text-xs flex-wrap">
        <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">&#x2705; ครบ</span>
        <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-700">&#x1F4C2; มีข้อมูล</span>
        <span class="px-2 py-0.5 rounded bg-gray-100 text-gray-500">&#x23F3; รอ</span>
      </div>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-xs text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
            <th class="px-4 py-2 text-left w-10">#</th>
            <th class="px-4 py-2 text-left">จังหวัด</th>
            <th class="px-4 py-2 text-center">สถานะ</th>
            <th class="px-4 py-2 text-right">PDF บน Drive</th>
            <th class="px-4 py-2 text-right">คาดหวัง</th>
            <th class="px-4 py-2 text-center w-56">ความคืบหน้า</th>
          </tr>
        </thead>
        <tbody id="tbl"></tbody>
      </table>
    </div>
  </div>

  <div class="text-center text-xs text-gray-400 mt-4 py-4">
    Election Verification System &mdash; Backup Monitor (Hybrid)
  </div>
</div>

<script>
function fmt(n) { return n == null ? '—' : n.toLocaleString(); }
function ago(ts) {
  if (!ts) return '';
  const s = Math.round(Date.now()/1000 - ts);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm ago';
}

function render(d) {
  const s = d.summary || {};
  const provs = d.provinces || [];

  // Error
  const eb = document.getElementById('error-banner');
  if (d.error) { eb.textContent = '&#x26A0; ' + d.error; eb.classList.remove('hidden'); }
  else { eb.classList.add('hidden'); }

  // Scan status
  const ss = document.getElementById('scan-status');
  if (d.scanning) {
    ss.innerHTML = '<span class="inline-flex items-center gap-1"><svg class="w-3 h-3 spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/></svg> ' + (d.scan_progress || 'scanning...') + '</span>';
    ss.className = 'text-xs text-blue-600 font-medium';
  } else {
    ss.textContent = 'idle';
    ss.className = 'text-xs text-gray-400';
  }
  document.getElementById('last-scan').textContent = d.last_scan_ts ? 'Last scan: ' + ago(d.last_scan_ts) : '';

  // Cards
  document.getElementById('has-data').textContent = s.has_data || 0;
  document.getElementById('has-data-sub').textContent = '/ ' + (s.total || 77) + ' provinces';
  document.getElementById('complete-count').textContent = s.complete || 0;
  document.getElementById('total-actual').textContent = fmt(s.total_actual);
  document.getElementById('total-expected-sub').textContent = s.total_expected ? ('/ ' + fmt(s.total_expected) + ' expected') : '';
  document.getElementById('scan-dur').textContent = d.scan_duration ? Math.round(d.scan_duration) + 's' : '-';
  document.getElementById('scan-dur-sub').textContent = d.scanning ? 'scanning now...' : 'last scan duration';

  // Progress bar
  const pct = s.pct || 0;
  document.getElementById('pct-text').textContent = s.total_expected ? (pct + '%') : (s.has_data + '/' + (s.total||77) + ' provinces');
  document.getElementById('pct-bar').style.width = (s.total_expected ? pct : Math.round(s.has_data/(s.total||77)*100)) + '%';

  // Table
  const tbl = document.getElementById('tbl');
  let html = '';
  provs.forEach((p, i) => {
    const rank = i + 1;
    const actual = p.actual || 0;
    const exp = p.expected;
    const pctP = p.pct;
    const comp = p.complete;

    let badge, rowCls = '';
    if (comp) {
      badge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">&#x2705; ครบ</span>';
    } else if (actual > 0) {
      badge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">&#x1F4C2; มีข้อมูล</span>';
    } else {
      badge = '<span class="text-gray-400 text-xs">&#x23F3; รอ</span>';
      rowCls = 'opacity-40';
    }

    let progHtml = '<span class="text-gray-300">—</span>';
    if (actual > 0 && exp) {
      const pw = Math.min(pctP || 0, 100);
      const color = comp ? 'emerald' : 'blue';
      progHtml = '<div class="flex items-center gap-2 justify-center">' +
        '<div class="w-24 bg-gray-200 rounded-full h-2"><div class="bar-anim bg-' + color + '-500 h-2 rounded-full" style="width:' + pw + '%"></div></div>' +
        '<span class="text-' + color + '-700 text-xs font-mono font-semibold">' + fmt(actual) + '/' + fmt(exp) + ' (' + (pctP||0) + '%)</span>' +
        '</div>';
    } else if (actual > 0) {
      progHtml = '<span class="text-gray-600 text-xs font-mono">' + fmt(actual) + ' PDFs</span>';
    }

    html += '<tr class="' + rowCls + ' border-b border-gray-100 hover:bg-gray-50">' +
      '<td class="px-4 py-2 text-gray-400 font-mono text-xs">' + rank + '</td>' +
      '<td class="px-4 py-2 font-semibold ' + (actual > 0 ? 'text-gray-900' : 'text-gray-400') + '">' + p.name + '</td>' +
      '<td class="px-4 py-2 text-center">' + badge + '</td>' +
      '<td class="px-4 py-2 text-right font-mono text-xs ' + (actual > 0 ? 'text-gray-700' : 'text-gray-300') + '">' + (actual > 0 ? fmt(actual) : '—') + '</td>' +
      '<td class="px-4 py-2 text-right font-mono text-xs text-gray-400">' + (exp ? fmt(exp) : '—') + '</td>' +
      '<td class="px-4 py-2 text-center">' + progHtml + '</td>' +
      '</tr>';
  });
  tbl.innerHTML = html;
}

async function fetchData() {
  try {
    const r = await fetch('/api/status?t=' + Date.now());
    render(await r.json());
  } catch(e) { console.error(e); }
}
fetchData();
setInterval(fetchData, 10000);
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/api/status":
            body = STATE.api_response().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
        elif p in ("/", "/index.html"):
            html = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass


def main():
    port = 8899
    # Start background scanner
    t = threading.Thread(target=scanner_thread, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n{'='*50}", flush=True)
    print(f"  ECT Backup Dashboard", flush=True)
    print(f"  http://localhost:{port}", flush=True)
    print(f"  Hybrid: progress file + scan caches + shallow Drive ({PROVS_PER_CYCLE} provs/cycle)", flush=True)
    print(f"  สแกนทุก {SCAN_INTERVAL}s", flush=True)
    print(f"{'='*50}\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")
        server.server_close()


if __name__ == "__main__":
    main()
