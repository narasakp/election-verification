# ไฟล์: scripts/fetch_vote62_data.py
import requests
import json

def fetch_vote62_data():
    """ดึงข้อมูลจาก Vote62.com"""
    
    # ตรวจสอบว่า Vote62 มี API หรือไม่
    # ถ้าไม่มี อาจต้อง scrape จากเว็บ
    
    # ตัวอย่าง (ถ้ามี API)
    vote62_url = "https://vote62.com/api/units"  # สมมติ
    
    try:
        response = requests.get(vote62_url)
        data = response.json()
        
        with open('../data/vote62_raw_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ ดึงข้อมูล Vote62 สำเร็จ")
        return data
        
    except Exception as e:
        print(f"⚠️  Vote62 API ไม่สามารถเข้าถึงได้: {e}")
        print("💡 แนะนำ: ติดต่อทีม Vote62 เพื่อขอ API access")
        return None

if __name__ == "__main__":
    fetch_vote62_data()