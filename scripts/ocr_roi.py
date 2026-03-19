# -*- coding: utf-8 -*-
"""Region-of-Interest (ROI) cropping for สส.5/18 forms.

Since all forms share the same layout, we can crop specific regions
and OCR them separately for higher accuracy:
  - Header region: province, constituency, district, station info
  - Candidate table: candidate names, numbers, parties, votes
  - Ballot stats: received, valid, invalid, no_vote, remaining

This focuses the LLM's attention on smaller, specific areas.
"""
import io

try:
    import numpy as np
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ─── ROI definitions (relative to page height/width) ────────────────
# These are approximate regions for สส.5/18 forms based on typical layout.
# Format: (top_ratio, bottom_ratio, left_ratio, right_ratio)

ROI_HEADER = (0.0, 0.15, 0.0, 1.0)       # Top 15%: province, constituency, station
ROI_CANDIDATES = (0.12, 0.72, 0.0, 1.0)   # Middle: candidate table
ROI_BALLOT_STATS = (0.68, 1.0, 0.0, 1.0)  # Bottom 32%: ballot statistics


def crop_roi(png_bytes, roi, padding=10):
    """Crop a region of interest from PNG bytes.
    
    Args:
        png_bytes: PNG image bytes
        roi: tuple (top_ratio, bottom_ratio, left_ratio, right_ratio)
        padding: extra pixels to include around the crop
    
    Returns:
        Cropped PNG bytes
    """
    if HAS_CV2:
        return _crop_cv2(png_bytes, roi, padding)
    elif HAS_PIL:
        return _crop_pil(png_bytes, roi, padding)
    else:
        return png_bytes


def _crop_cv2(png_bytes, roi, padding):
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return png_bytes
    
    h, w = img.shape[:2]
    top = max(0, int(h * roi[0]) - padding)
    bottom = min(h, int(h * roi[1]) + padding)
    left = max(0, int(w * roi[2]) - padding)
    right = min(w, int(w * roi[3]) + padding)
    
    cropped = img[top:bottom, left:right]
    success, encoded = cv2.imencode('.png', cropped)
    return encoded.tobytes() if success else png_bytes


def _crop_pil(png_bytes, roi, padding):
    img = Image.open(io.BytesIO(png_bytes))
    w, h = img.size
    
    left = max(0, int(w * roi[2]) - padding)
    top = max(0, int(h * roi[0]) - padding)
    right = min(w, int(w * roi[3]) + padding)
    bottom = min(h, int(h * roi[1]) + padding)
    
    cropped = img.crop((left, top, right, bottom))
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def get_all_rois(png_bytes):
    """Get all three ROI crops from a full page image.
    
    Returns:
        dict with keys 'header', 'candidates', 'ballot_stats' → PNG bytes
    """
    return {
        'header': crop_roi(png_bytes, ROI_HEADER),
        'candidates': crop_roi(png_bytes, ROI_CANDIDATES),
        'ballot_stats': crop_roi(png_bytes, ROI_BALLOT_STATS),
    }


# ─── ROI-specific prompts ───────────────────────────────────────────

HEADER_PROMPT = """อ่านข้อมูล header จากฟอร์ม สส.5/18 นี้ ตอบเป็น JSON:
{
  "vote_type": "แบ่งเขต หรือ บัญชีรายชื่อ",
  "province": "ชื่อจังหวัด",
  "constituency": เลขเขต,
  "district": "ชื่ออำเภอ",
  "sub_district": "ชื่อตำบล หรือ null",
  "station_no": เลขหน่วยเลือกตั้ง,
  "registered_voters": จำนวนผู้มีสิทธิ
}"""

BALLOT_STATS_PROMPT = """อ่านข้อมูลบัตรเลือกตั้งจากส่วนล่างของฟอร์ม สส.5/18 นี้

สำคัญ: 
- ตัวเลขอาจเขียนด้วยมือ ดูทั้งตัวเลขอาราบิกและตัวหนังสือไทย
- ถ้ามีทั้งสองแบบ ใช้ค่าที่ใหญ่กว่า
- ตรวจสอบ: ballots_received = valid + invalid + no_vote + remaining

ตอบเป็น JSON:
{
  "turnout": จำนวนผู้มาใช้สิทธิ,
  "ballots_received": จำนวนบัตรที่ได้รับ,
  "valid_ballots": จำนวนบัตรดี,
  "invalid_ballots": จำนวนบัตรเสีย,
  "no_vote_ballots": จำนวนบัตรไม่ประสงค์เลือก,
  "remaining_ballots": จำนวนบัตรเหลือ
}"""

CANDIDATES_PROMPT = """อ่านตารางผู้สมัคร/พรรคจากฟอร์ม สส.5/18 นี้

สำคัญ:
- อ่านทุกแถว อย่าข้ามแถวที่คะแนนเป็น 0
- "number" คือเลขหมายที่อยู่คอลัมน์แรก
- "votes" คือตัวเลขคะแนนในคอลัมน์สุดท้าย
- ถ้าเป็นบัญชีรายชื่อ: name มักเป็น null, party คือชื่อพรรค

ตอบเป็น JSON:
{
  "candidates": [
    {"number": เลขที่, "name": "ชื่อ-นามสกุล หรือ null", "party": "ชื่อพรรค", "votes": คะแนน}
  ],
  "total_votes": รวมคะแนนทั้งหมด
}"""


if __name__ == '__main__':
    status = {'cv2': HAS_CV2, 'pil': HAS_PIL}
    print(f"ROI dependencies: {status}")
    print(f"ROI regions defined: header={ROI_HEADER}, candidates={ROI_CANDIDATES}, ballot={ROI_BALLOT_STATS}")
