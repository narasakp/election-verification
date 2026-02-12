# คู่มือการ Deploy ระบบบน GitHub Pages

## 📋 ภาพรวม

ระบบนี้ออกแบบให้รองรับการ deploy บน **GitHub Pages** อย่างเต็มรูปแบบ โดยใช้เทคโนโลยีที่ทำงานฝั่ง Client-side ทั้งหมด ไม่ต้องการ backend server

## ✅ Tech Stack ที่ใช้ (รองรับ GitHub Pages 100%)

### 1. HTML5 + CSS3 + JavaScript (Vanilla)
- ✅ รองรับเต็มรูปแบบ
- ไม่ต้อง build process
- ทำงานบนเบราว์เซอร์โดยตรง

### 2. Chart.js (Data Visualization)
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```
- ✅ รองรับเต็มรูปแบบ
- โหลดจาก CDN
- สร้างกราฟได้หลากหลาย: Bar, Line, Pie, Doughnut, Scatter

### 3. Leaflet.js (Interactive Maps)
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```
- ✅ รองรับเต็มรูปแบบ
- แสดงแผนที่โต้ตอบได้
- ใช้ OpenStreetMap (ฟรี)

### 4. D3.js (Advanced Visualizations)
```html
<script src="https://d3js.org/d3.v7.min.js"></script>
```
- ✅ รองรับเต็มรูปแบบ
- สำหรับ visualization ขั้นสูง
- Network graphs, Force-directed layouts

### 5. JSON Files (Data Storage)
```
data/
├── election_data.json
├── constituency_info.json
└── comparison_results.json
```
- ✅ รองรับเต็มรูปแบบ
- GitHub Pages สามารถ serve ไฟล์ JSON ได้
- อัพเดทข้อมูลด้วยการ push ไฟล์ใหม่

---

## 🚀 ขั้นตอนการ Deploy

### Step 1: สร้าง Repository

```bash
# สร้าง repo ใหม่บน GitHub
# ชื่อ repo: election-verification

# Clone มาที่เครื่อง
git clone https://github.com/YOUR_USERNAME/election-verification.git
cd election-verification
```

### Step 2: จัดเตรียมโครงสร้างไฟล์

```
election-verification/
├── index.html                      # หน้าหลัก (ใช้ github_pages_dashboard.html)
├── README.md                       # คำอธิบายโปรเจค
├── data/
│   ├── election_data.json         # ข้อมูลการเปรียบเทียบ
│   ├── sample_data.json           # ข้อมูลตัวอย่าง
│   └── metadata.json              # Metadata
├── docs/
│   ├── VOTE62_COMPARISON_GUIDE.md
│   └── API_DOCUMENTATION.md
├── scripts/
│   ├── vote62_comparator.py       # สำหรับสร้างข้อมูล
│   └── update_data.py             # สคริปต์อัพเดทข้อมูล
└── assets/
    ├── images/
    └── icons/
```

### Step 3: Copy ไฟล์

```bash
# Copy dashboard เป็นหน้าหลัก
cp github_pages_dashboard.html index.html

# สร้างโฟลเดอร์
mkdir -p data docs scripts assets

# Copy ไฟล์อื่นๆ
cp VOTE62_COMPARISON_GUIDE.md docs/
cp vote62_comparator.py scripts/
```

### Step 4: สร้างไฟล์ข้อมูลตัวอย่าง

สร้างไฟล์ `data/election_data.json`:

```json
{
  "metadata": {
    "last_update": "2026-02-12T15:30:00",
    "total_units": 95000,
    "compared_units": 31200,
    "version": "1.0"
  },
  "statistics": {
    "identical": 28000,
    "minor": 2500,
    "significant": 600,
    "critical": 100
  },
  "units": [
    {
      "unit_id": "001001",
      "constituency": "กรุงเทพมหานคร เขต 1",
      "province": "bangkok",
      "ect_total": 3550,
      "vote62_total": 3550,
      "difference": 0,
      "level": "identical",
      "lat": 13.7563,
      "lng": 100.5018,
      "timestamp": "2026-02-12T20:00:00",
      "parties": [
        {
          "name": "พรรค A",
          "ect": 1500,
          "vote62": 1500,
          "difference": 0
        },
        {
          "name": "พรรค B",
          "ect": 1200,
          "vote62": 1200,
          "difference": 0
        },
        {
          "name": "พรรค C",
          "ect": 800,
          "vote62": 800,
          "difference": 0
        },
        {
          "name": "บัตรเสีย",
          "ect": 50,
          "vote62": 50,
          "difference": 0
        }
      ]
    },
    {
      "unit_id": "001002",
      "constituency": "กรุงเทพมหานคร เขต 1",
      "province": "bangkok",
      "ect_total": 3680,
      "vote62_total": 3550,
      "difference": 130,
      "level": "critical",
      "lat": 13.7600,
      "lng": 100.5100,
      "timestamp": "2026-02-12T20:05:00",
      "parties": [
        {
          "name": "พรรค A",
          "ect": 1630,
          "vote62": 1500,
          "difference": 130
        },
        {
          "name": "พรรค B",
          "ect": 1200,
          "vote62": 1200,
          "difference": 0
        },
        {
          "name": "พรรค C",
          "ect": 850,
          "vote62": 850,
          "difference": 0
        }
      ]
    }
  ]
}
```

### Step 5: แก้ไข index.html ให้โหลดข้อมูลจาก JSON

ในไฟล์ `index.html` แก้ฟังก์ชัน `loadData()`:

```javascript
// Load data from JSON file
async function loadData() {
    try {
        const response = await fetch('data/election_data.json');
        data = await response.json();
        updateUI();
    } catch (error) {
        console.error('Error loading data:', error);
        // Fallback to sample data
        data = sampleData;
        updateUI();
    }
}
```

### Step 6: Commit และ Push

```bash
# Add ไฟล์ทั้งหมด
git add .

# Commit
git commit -m "Initial commit: Election verification dashboard"

# Push
git push origin main
```

### Step 7: เปิดใช้งาน GitHub Pages

1. ไปที่ Repository Settings
2. เลื่อนไปที่ **Pages** (ในเมนูซ้าย)
3. เลือก Source: **Deploy from a branch**
4. เลือก Branch: **main** 
5. เลือก Folder: **/ (root)**
6. กด **Save**

### Step 8: รอสักครู่และเข้าดู

URL จะเป็น: `https://YOUR_USERNAME.github.io/election-verification/`

---

## 🔄 การอัพเดทข้อมูล

### วิธีที่ 1: Manual Update

```bash
# แก้ไขไฟล์ data/election_data.json
# จากนั้น push

git add data/election_data.json
git commit -m "Update election data"
git push origin main

# GitHub Pages จะอัพเดทอัตโนมัติภายใน 1-2 นาที
```

### วิธีที่ 2: ใช้ Python Script

สร้างไฟล์ `scripts/update_data.py`:

```python
#!/usr/bin/env python3
"""
สคริปต์สำหรับดึงข้อมูลล่าสุดและอัพเดทไฟล์ JSON
"""

import json
from datetime import datetime
from vote62_comparator import Vote62Comparator

def update_election_data():
    comparator = Vote62Comparator()
    
    # ดึงข้อมูลทั้งหมด
    # ... (ใช้ code จาก vote62_comparator.py)
    
    # สร้าง JSON
    output_data = {
        "metadata": {
            "last_update": datetime.now().isoformat(),
            "total_units": 95000,
            "compared_units": len(results)
        },
        "statistics": comparator.stats,
        "units": [
            {
                "unit_id": r.unit_id,
                "constituency": r.constituency,
                # ... fields อื่นๆ
            }
            for r in comparator.discrepancies
        ]
    }
    
    # บันทึกไฟล์
    with open('../data/election_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print("✅ อัพเดทข้อมูลเรียบร้อย")

if __name__ == "__main__":
    update_election_data()
```

จากนั้นรัน:

```bash
cd scripts
python update_data.py

cd ..
git add data/election_data.json
git commit -m "Auto-update: $(date)"
git push origin main
```

### วิธีที่ 3: GitHub Actions (อัตโนมัติ)

สร้างไฟล์ `.github/workflows/update-data.yml`:

```yaml
name: Update Election Data

on:
  schedule:
    # รันทุก 1 ชั่วโมง
    - cron: '0 * * * *'
  workflow_dispatch:  # สามารถรัน manual ได้

jobs:
  update:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install requests pandas numpy
    
    - name: Update data
      run: |
        cd scripts
        python update_data.py
    
    - name: Commit and push if changed
      run: |
        git config --global user.name 'GitHub Actions'
        git config --global user.email 'actions@github.com'
        git add data/election_data.json
        git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update: $(date)" && git push)
```

---

## 🎨 การปรับแต่ง

### เปลี่ยนสีธีม

แก้ไขตัวแปร CSS ใน `index.html`:

```css
:root {
    --primary: #667eea;      /* สีหลัก */
    --secondary: #764ba2;    /* สีรอง */
    --danger: #f5576c;       /* สีแดง (critical) */
    --warning: #ffc107;      /* สีเหลือง (warning) */
    --success: #28a745;      /* สีเขียว (success) */
}
```

### เพิ่ม Google Analytics

เพิ่มใน `<head>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### เพิ่ม Custom Domain

1. สร้างไฟล์ `CNAME` ใน root:
   ```
   election.yourdomain.com
   ```

2. ตั้งค่า DNS:
   ```
   Type: CNAME
   Name: election
   Value: YOUR_USERNAME.github.io
   ```

---

## ⚡ การเพิ่มประสิทธิภาพ

### 1. Lazy Loading สำหรับข้อมูลขนาดใหญ่

```javascript
// แทนที่จะโหลดข้อมูลทั้งหมด
// ให้โหลดทีละส่วน

async function loadDataPaginated(page = 1, limit = 100) {
    const response = await fetch(`data/units_page_${page}.json`);
    return await response.json();
}
```

### 2. ใช้ Service Worker สำหรับ Offline

สร้างไฟล์ `sw.js`:

```javascript
const CACHE_NAME = 'election-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/data/election_data.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

ใน `index.html`:

```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

### 3. Compression

GitHub Pages รองรับ gzip อัตโนมัติ แต่สามารถ pre-compress ไฟล์ได้:

```bash
# สำหรับไฟล์ JSON ขนาดใหญ่
gzip -k data/election_data.json
# จะได้ election_data.json.gz
```

---

## 🔒 Security Considerations

### 1. ไม่ควรเก็บข้อมูลละเอียดอ่อน

- ❌ API keys
- ❌ รหัสผ่าน
- ❌ ข้อมูลส่วนบุคคล
- ✅ ข้อมูลสาธารณะเท่านั้น

### 2. CORS Headers

GitHub Pages มี CORS headers ที่เหมาะสม สามารถ fetch ข้อมูลข้าม domain ได้

### 3. HTTPS

GitHub Pages บังคับใช้ HTTPS อัตโนมัติ ✅

---

## 📊 ตัวอย่าง URL Structure

```
https://YOUR_USERNAME.github.io/election-verification/
├── index.html                          # Dashboard หลัก
├── data/election_data.json            # API endpoint สำหรับข้อมูล
├── data/constituency_info.json        # ข้อมูลเขตเลือกตั้ง
└── docs/VOTE62_COMPARISON_GUIDE.html  # คู่มือ
```

---

## 🐛 Troubleshooting

### ปัญหา: หน้าเว็บไม่แสดง

```bash
# ตรวจสอบ GitHub Pages status
# Repository → Settings → Pages

# ดู error logs ใน Actions tab
```

### ปัญหา: ไฟล์ JSON โหลดไม่ได้

```javascript
// ตรวจสอบ path
// ถ้า index.html อยู่ที่ root
// ใช้: fetch('data/election_data.json')

// ถ้า index.html อยู่ใน subdirectory
// ใช้: fetch('../data/election_data.json')
```

### ปัญหา: 404 Not Found

```bash
# ตรวจสอบว่า branch ถูกต้อง
# ตรวจสอบว่า GitHub Pages enabled
# รอ 1-2 นาทีหลัง push
```

---

## ✅ Checklist ก่อน Deploy

- [ ] ทดสอบบนเครื่อง local (เปิด index.html ใน browser)
- [ ] ตรวจสอบ path ของไฟล์ JSON
- [ ] ตรวจสอบ console errors
- [ ] ทดสอบบน mobile
- [ ] เพิ่ม README.md ที่อธิบายโปรเจค
- [ ] ตรวจสอบ license
- [ ] เพิ่ม .gitignore (ถ้าจำเป็น)

---

## 📚 Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [Leaflet Documentation](https://leafletjs.com/)
- [D3.js Examples](https://d3-graph-gallery.com/)

---

## 🎉 สรุป

✅ **ทุกอย่างใน tech stack รองรับ GitHub Pages ได้ 100%**

- HTML/CSS/JavaScript → ✅
- Chart.js → ✅ (CDN)
- Leaflet → ✅ (CDN)
- D3.js → ✅ (CDN)
- JSON Files → ✅ (Static files)

**ไม่ต้องการ:**
- ❌ Backend server
- ❌ Database
- ❌ Build process (ถ้าใช้ vanilla JS)
- ❌ Hosting costs (GitHub Pages ฟรี)

**Deploy ได้ภายใน 5 นาที!** 🚀
