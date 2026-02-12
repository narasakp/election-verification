#!/usr/bin/env python3
"""
ระบบตรวจสอบข้อมูลการเลือกตั้ง (Election Data Verification System)
สำหรับวิเคราะห์ข้อมูลจาก กกต. API
"""

import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

class ElectionDataVerifier:
    """คลาสหลักสำหรับตรวจสอบข้อมูลการเลือกตั้ง"""
    
    def __init__(self, base_url: str = "https://static-ectreport69.ect.go.th/data/data"):
        self.base_url = base_url
        self.constituency_data = None
        self.results_data = None
        self.audit_trail = []
        
    def fetch_constituency_info(self) -> Dict:
        """ดึงข้อมูลโครงสร้างเขตเลือกตั้ง"""
        try:
            url = f"{self.base_url}/refs/info_constituency.json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            self.constituency_data = response.json()
            print(f"✓ ดึงข้อมูลเขตเลือกตั้งสำเร็จ: {len(self.constituency_data)} รายการ")
            return self.constituency_data
        except Exception as e:
            print(f"✗ เกิดข้อผิดพลาด: {str(e)}")
            return None
    
    def analyze_constituency_structure(self) -> pd.DataFrame:
        """วิเคราะห์โครงสร้างเขตเลือกตั้ง"""
        if not self.constituency_data:
            print("กรุณาดึงข้อมูลเขตเลือกตั้งก่อน")
            return None
        
        # แปลงเป็น DataFrame
        df = pd.DataFrame(self.constituency_data)
        
        print("\n=== สรุปโครงสร้างเขตเลือกตั้ง ===")
        print(f"จำนวนเขตทั้งหมด: {len(df)}")
        
        if 'province' in df.columns:
            print(f"จำนวนจังหวัด: {df['province'].nunique()}")
            print(f"\nจำนวนเขตต่อจังหวัด:")
            print(df['province'].value_counts().head(10))
        
        return df
    
    def check_voter_turnout_anomalies(self, df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
        """
        ตรวจสอบความผิดปกติของการใช้สิทธิ์เลือกตั้ง
        threshold: เกณฑ์ผู้มาใช้สิทธิที่ผิดปกติ (>95% อาจต้องตรวจสอบ)
        """
        if 'eligible_voters' not in df.columns or 'votes_cast' not in df.columns:
            print("ข้อมูลไม่ครบสำหรับการวิเคราะห์")
            return None
        
        df['turnout_rate'] = (df['votes_cast'] / df['eligible_voters']) * 100
        anomalies = df[df['turnout_rate'] > threshold * 100]
        
        print(f"\n=== เขตที่มีการใช้สิทธิสูงผิดปกติ (>{threshold*100}%) ===")
        print(f"พบ {len(anomalies)} เขต")
        
        if len(anomalies) > 0:
            print(anomalies[['constituency_name', 'turnout_rate', 'eligible_voters', 'votes_cast']].to_string())
        
        return anomalies
    
    def detect_statistical_anomalies(self, df: pd.DataFrame) -> Dict:
        """
        ตรวจหาความผิดปกติทางสถิติ
        - Benford's Law สำหรับตัวเลขหลักหน้า
        - ค่าเบี่ยงเบนมาตรฐาน
        """
        anomalies = {
            'high_variance': [],
            'benford_violations': [],
            'outliers': []
        }
        
        if 'votes_cast' in df.columns:
            # หาค่า Outliers ด้วย IQR
            Q1 = df['votes_cast'].quantile(0.25)
            Q3 = df['votes_cast'].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df[(df['votes_cast'] < Q1 - 1.5 * IQR) | 
                         (df['votes_cast'] > Q3 + 1.5 * IQR)]
            
            if len(outliers) > 0:
                anomalies['outliers'] = outliers.to_dict('records')
                print(f"\n=== พบ Outliers จำนวน {len(outliers)} เขต ===")
        
        return anomalies
    
    def verify_data_consistency(self, step1_data: Dict, step2_data: Dict) -> List[Dict]:
        """
        เปรียบเทียบข้อมูลระหว่างขั้นตอนต่างๆ
        เพื่อหาจุดที่ข้อมูลอาจถูกเปลี่ยนแปลง
        """
        inconsistencies = []
        
        for key in step1_data.keys():
            if key in step2_data:
                if step1_data[key] != step2_data[key]:
                    inconsistencies.append({
                        'field': key,
                        'step1_value': step1_data[key],
                        'step2_value': step2_data[key],
                        'difference': abs(step1_data[key] - step2_data[key]) if isinstance(step1_data[key], (int, float)) else None
                    })
        
        if inconsistencies:
            print(f"\n=== พบความไม่สอดคล้องของข้อมูล {len(inconsistencies)} รายการ ===")
            for item in inconsistencies:
                print(f"Field: {item['field']}")
                print(f"  Step 1: {item['step1_value']}")
                print(f"  Step 2: {item['step2_value']}")
        
        return inconsistencies
    
    def analyze_timing_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        วิเคราะห์ความผิดปกติของเวลาในการส่งข้อมูล
        เช่น หน่วยห่างไกลส่งข้อมูลเร็วกว่าในเมือง
        """
        if 'submission_time' not in df.columns or 'distance_from_center' not in df.columns:
            print("ไม่มีข้อมูลเวลาหรือระยะทางสำหรับวิเคราะห์")
            return None
        
        # หาความสัมพันธ์ระหว่างระยะทางและเวลา
        correlation = df['distance_from_center'].corr(df['submission_time'])
        
        print(f"\n=== การวิเคราะห์เวลาในการส่งข้อมูล ===")
        print(f"Correlation ระหว่างระยะทางและเวลา: {correlation:.3f}")
        
        if correlation < 0:
            print("⚠️  พบความผิดปกติ: หน่วยห่างไกลส่งข้อมูลเร็วกว่าหน่วยใกล้!")
        
        return df
    
    def generate_audit_report(self, output_file: str = "audit_report.json"):
        """สร้างรายงานการตรวจสอบ"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'audit_trail': self.audit_trail,
            'summary': {
                'total_constituencies': len(self.constituency_data) if self.constituency_data else 0,
                'checks_performed': len(self.audit_trail)
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ บันทึกรายงานไปยัง {output_file}")
        return report
    
    def compare_with_photos(self, photo_data: Dict, digital_data: Dict) -> List[Dict]:
        """
        เปรียบเทียบภาพถ่ายใบรายงานกับข้อมูลดิจิทัล
        (ต้องใช้ OCR หรือ manual verification)
        """
        print("\n=== การเปรียบเทียบภาพถ่ายกับข้อมูลดิจิทัล ===")
        print("คุณสมบัติ:")
        print("1. ตรวจสอบตัวเลขในภาพ ส.ส. 5/18 กับข้อมูลใน API")
        print("2. ตรวจสอบลายเซ็นและตราประทับ")
        print("3. ตรวจสอบเวลาและวันที่")
        
        # Placeholder สำหรับการเปรียบเทียบจริง
        return []


def main():
    """ฟังก์ชันหลักสำหรับรันระบบ"""
    print("=" * 60)
    print("ระบบตรวจสอบข้อมูลการเลือกตั้ง กกต.")
    print("=" * 60)
    
    # สร้าง instance
    verifier = ElectionDataVerifier()
    
    # 1. ดึงข้อมูลเขตเลือกตั้ง
    print("\n[1] กำลังดึงข้อมูลเขตเลือกตั้ง...")
    data = verifier.fetch_constituency_info()
    
    if data:
        # 2. วิเคราะห์โครงสร้าง
        print("\n[2] วิเคราะห์โครงสร้างเขตเลือกตั้ง...")
        df = verifier.analyze_constituency_structure()
        
        # 3. ตรวจสอบความผิดปกติ
        # (ต้องมีข้อมูลจริงจาก API ก่อน)
        
        # 4. สร้างรายงาน
        print("\n[4] สร้างรายงานการตรวจสอบ...")
        verifier.generate_audit_report()
    
    print("\n" + "=" * 60)
    print("คำแนะนำการใช้งานต่อ:")
    print("1. ตรวจสอบไฟล์ audit_report.json")
    print("2. เพิ่มข้อมูลจากแหล่งอื่นเพื่อเปรียบเทียบ")
    print("3. ใช้ AI วิเคราะห์รูปแบบที่ซับซ้อน")
    print("=" * 60)


if __name__ == "__main__":
    main()
