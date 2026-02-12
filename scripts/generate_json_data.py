#!/usr/bin/env python3
"""
Generate JSON Data for GitHub Pages
สคริปต์สำหรับสร้างไฟล์ JSON จากผลการเปรียบเทียบ
"""

import json
from datetime import datetime
from typing import List, Dict
import sys
import os

# Import comparator
try:
    from vote62_comparator import Vote62Comparator, DiscrepancyLevel
except ImportError:
    print("⚠️  ไม่พบ vote62_comparator.py")
    print("กรุณาตรวจสอบว่าไฟล์อยู่ใน directory เดียวกัน")
    sys.exit(1)


class JSONDataGenerator:
    """สร้างไฟล์ JSON สำหรับ GitHub Pages"""
    
    def __init__(self, comparator: Vote62Comparator):
        self.comparator = comparator
        self.output_dir = "../data"
        
    def generate_main_data(self) -> Dict:
        """สร้างไฟล์ข้อมูลหลัก"""
        
        # สร้าง metadata
        metadata = {
            "last_update": datetime.now().isoformat(),
            "total_units": 95000,
            "compared_units": len(self.comparator.discrepancies),
            "version": "1.0",
            "data_source": {
                "ect": "https://www.ect.go.th",
                "vote62": "https://vote62.com"
            }
        }
        
        # สร้าง statistics
        stats = self.comparator.stats
        total = stats['total_units_compared']
        
        statistics = {
            "identical": stats['identical'],
            "minor": stats['minor_diff'],
            "significant": stats['significant_diff'],
            "critical": stats['critical_diff'],
            "percentage": {
                "identical": (stats['identical'] / total * 100) if total > 0 else 0,
                "minor": (stats['minor_diff'] / total * 100) if total > 0 else 0,
                "significant": (stats['significant_diff'] / total * 100) if total > 0 else 0,
                "critical": (stats['critical_diff'] / total * 100) if total > 0 else 0
            }
        }
        
        # สร้างข้อมูลหน่วย
        units = []
        for result in self.comparator.discrepancies:
            unit_data = {
                "unit_id": result.unit_id,
                "constituency": result.constituency,
                "ect_total": result.ect_total,
                "vote62_total": result.vote62_total,
                "difference": result.difference,
                "level": result.discrepancy_level.name.lower(),
                "timestamp": result.timestamp,
                "has_discrepancy": result.difference > 0
            }
            
            # เพิ่มรายละเอียดพรรค
            if result.details and 'discrepant_candidates' in result.details:
                parties = []
                for candidate in result.details['discrepant_candidates']:
                    parties.append({
                        "name": candidate['name'],
                        "ect": candidate['ect_votes'],
                        "vote62": candidate['vote62_votes'],
                        "difference": candidate['difference'],
                        "suspicious": candidate['difference'] > 10
                    })
                unit_data['parties'] = parties
            
            # เพิ่ม notes ถ้ามีความผิดปกติ
            if result.difference > 0:
                if result.discrepancy_level == DiscrepancyLevel.CRITICAL:
                    unit_data['discrepancy_notes'] = f"แตกต่างร้ายแรง {result.difference} คะแนน - ต้องตรวจสอบด่วน"
                elif result.discrepancy_level == DiscrepancyLevel.SIGNIFICANT:
                    unit_data['discrepancy_notes'] = f"แตกต่างมาก {result.difference} คะแนน - ควรตรวจสอบ"
                else:
                    unit_data['discrepancy_notes'] = f"แตกต่างเล็กน้อย {result.difference} คะแนน"
            
            units.append(unit_data)
        
        # หาหน่วย critical
        critical_units = [
            {
                "unit_id": r.unit_id,
                "constituency": r.constituency,
                "difference": r.difference,
                "priority": "high"
            }
            for r in self.comparator.discrepancies
            if r.discrepancy_level == DiscrepancyLevel.CRITICAL
        ]
        
        # รวมทั้งหมด
        data = {
            "metadata": metadata,
            "statistics": statistics,
            "units": units,
            "critical_units": critical_units,
            "notes": [
                "ข้อมูลจากการเปรียบเทียบระหว่าง กกต. และ Vote62.com",
                f"อัพเดทล่าสุด: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "หน่วยที่มีความแตกต่างควรได้รับการตรวจสอบเพิ่มเติม"
            ]
        }
        
        return data
    
    def save_json(self, data: Dict, filename: str):
        """บันทึกไฟล์ JSON"""
        
        # สร้าง directory ถ้ายังไม่มี
        os.makedirs(self.output_dir, exist_ok=True)
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ บันทึกไฟล์: {filepath}")
        
        # แสดงขนาดไฟล์
        file_size = os.path.getsize(filepath)
        print(f"   ขนาดไฟล์: {file_size:,} bytes ({file_size/1024:.2f} KB)")
    
    def generate_province_data(self) -> Dict[str, Dict]:
        """สร้างข้อมูลแยกตามจังหวัด"""
        
        provinces = {}
        
        for result in self.comparator.discrepancies:
            # Extract province from constituency (simplified)
            # ในการใช้งานจริง ควรมี mapping ที่ชัดเจน
            province = "unknown"
            
            if province not in provinces:
                provinces[province] = {
                    "name": province,
                    "units": [],
                    "statistics": {
                        "total": 0,
                        "identical": 0,
                        "minor": 0,
                        "significant": 0,
                        "critical": 0
                    }
                }
            
            provinces[province]["units"].append(result.unit_id)
            provinces[province]["statistics"]["total"] += 1
            
            level = result.discrepancy_level.name.lower()
            if level in provinces[province]["statistics"]:
                provinces[province]["statistics"][level] += 1
        
        return provinces
    
    def generate_timeline_data(self) -> List[Dict]:
        """สร้างข้อมูล timeline"""
        
        # Group by timestamp
        timeline = {}
        
        for result in self.comparator.discrepancies:
            timestamp = result.timestamp.split('T')[0]  # Get date only
            
            if timestamp not in timeline:
                timeline[timestamp] = {
                    "timestamp": timestamp,
                    "units_compared": 0,
                    "critical_found": 0
                }
            
            timeline[timestamp]["units_compared"] += 1
            
            if result.discrepancy_level == DiscrepancyLevel.CRITICAL:
                timeline[timestamp]["critical_found"] += 1
        
        return sorted(timeline.values(), key=lambda x: x["timestamp"])
    
    def generate_all(self):
        """สร้างไฟล์ทั้งหมด"""
        
        print("\n" + "="*60)
        print("🔧 กำลังสร้างไฟล์ JSON สำหรับ GitHub Pages")
        print("="*60)
        
        # 1. Main data
        print("\n[1/3] สร้างไฟล์ข้อมูลหลัก...")
        main_data = self.generate_main_data()
        self.save_json(main_data, "election_data.json")
        
        # 2. Province data
        print("\n[2/3] สร้างไฟล์ข้อมูลรายจังหวัด...")
        province_data = self.generate_province_data()
        self.save_json(province_data, "province_data.json")
        
        # 3. Timeline data
        print("\n[3/3] สร้างไฟล์ timeline...")
        timeline_data = self.generate_timeline_data()
        self.save_json({"timeline": timeline_data}, "timeline_data.json")
        
        print("\n" + "="*60)
        print("✅ สร้างไฟล์เสร็จสมบูรณ์!")
        print("="*60)
        print(f"\nไฟล์ทั้งหมดอยู่ใน: {self.output_dir}/")
        print("\nขั้นตอนต่อไป:")
        print("1. ตรวจสอบไฟล์ JSON ที่สร้าง")
        print("2. Copy ไปยัง GitHub repository")
        print("3. git add, commit, push")
        print("4. GitHub Pages จะอัพเดทอัตโนมัติ")


def main():
    """ฟังก์ชันหลัก"""
    
    print("="*60)
    print("JSON Data Generator for GitHub Pages")
    print("="*60)
    
    # ตัวเลือก
    print("\nเลือกแหล่งข้อมูล:")
    print("1. ใช้ข้อมูลจากการเปรียบเทียบจริง (ต้องมี API access)")
    print("2. ใช้ข้อมูลตัวอย่าง (สำหรับทดสอบ)")
    
    choice = input("\nกรุณาเลือก (1-2): ").strip()
    
    if choice == "1":
        print("\n⚠️  ฟีเจอร์นี้ต้องการ API access จริง")
        print("กรุณาตรวจสอบว่าคุณมี:")
        print("  - API endpoint ของ กกต.")
        print("  - API endpoint ของ Vote62")
        
        proceed = input("\nดำเนินการต่อ? (y/n): ").strip().lower()
        
        if proceed == 'y':
            comparator = Vote62Comparator()
            
            # ดึงข้อมูลจริง (ต้องเพิ่ม logic)
            print("\n🔍 กำลังดึงข้อมูล...")
            # comparator.fetch_and_compare_all()
            
            generator = JSONDataGenerator(comparator)
            generator.generate_all()
        else:
            print("\nยกเลิกการทำงาน")
    
    elif choice == "2":
        print("\n📝 ใช้ข้อมูลตัวอย่าง")
        print("กำลังสร้างไฟล์ตัวอย่าง...")
        
        # สร้างข้อมูลตัวอย่าง
        sample_data = {
            "metadata": {
                "last_update": datetime.now().isoformat(),
                "total_units": 95000,
                "compared_units": 5,
                "version": "1.0-sample"
            },
            "statistics": {
                "identical": 2,
                "minor": 1,
                "significant": 1,
                "critical": 1
            },
            "units": [
                {
                    "unit_id": "001001",
                    "constituency": "กรุงเทพมหานคร เขต 1",
                    "ect_total": 3550,
                    "vote62_total": 3550,
                    "difference": 0,
                    "level": "identical"
                },
                {
                    "unit_id": "001002",
                    "constituency": "กรุงเทพมหานคร เขต 1",
                    "ect_total": 3680,
                    "vote62_total": 3550,
                    "difference": 130,
                    "level": "critical"
                }
            ]
        }
        
        # บันทึก
        os.makedirs("../data", exist_ok=True)
        with open("../data/election_data_sample.json", 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        
        print("✅ สร้างไฟล์ตัวอย่าง: ../data/election_data_sample.json")
    
    else:
        print("\n⚠️  ตัวเลือกไม่ถูกต้อง")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการทำงาน")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
