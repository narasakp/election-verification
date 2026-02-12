# ไฟล์: scripts/fetch_ect_data.py
import requests
import json

def fetch_ect_data():
    """ดึงข้อมูลจาก กกต."""
    
    # API ของ กกต.
    base_url = "https://static-ectreport69.ect.go.th/data/data"
    
    # ตัวอย่าง: ดึงข้อมูลเขตเลือกตั้ง
    constituencies_url = f"{base_url}/refs/info_constituency.json"
    
    try:
        response = requests.get(constituencies_url)
        data = response.json()
        
        # บันทึกลงไฟล์
        with open('../data/ect_raw_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ดึงข้อมูล กกต. สำเร็จ: {len(data)} รายการ")
        return data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    fetch_ect_data()