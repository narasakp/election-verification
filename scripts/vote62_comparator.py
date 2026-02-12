#!/usr/bin/env python3
"""
โมดูลเปรียบเทียบข้อมูล กกต. vs Vote62.com
Cross-verification between Official ECT Data and Citizen-sourced Vote62 Data
"""

import requests
import json
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import hashlib
from dataclasses import dataclass
from enum import Enum


class DiscrepancyLevel(Enum):
    """ระดับความร้ายแรงของความแตกต่าง"""
    IDENTICAL = "เหมือนกันเป๊ะ ✅"
    MINOR = "แตกต่างเล็กน้อย ⚠️"
    SIGNIFICANT = "แตกต่างมาก 🚨"
    CRITICAL = "แตกต่างร้ายแรง 🔴"


@dataclass
class VerificationResult:
    """ผลการตรวจสอบ"""
    unit_id: str
    constituency: str
    ect_total: int
    vote62_total: int
    difference: int
    discrepancy_level: DiscrepancyLevel
    details: Dict
    timestamp: str


class Vote62Comparator:
    """คลาสหลักสำหรับเปรียบเทียบข้อมูล"""
    
    def __init__(self):
        self.ect_base_url = "https://static-ectreport69.ect.go.th/data/data"
        self.vote62_base_url = "https://vote62.com/api"  # สมมติ API endpoint
        self.discrepancies = []
        self.stats = {
            'total_units_compared': 0,
            'identical': 0,
            'minor_diff': 0,
            'significant_diff': 0,
            'critical_diff': 0
        }
    
    def fetch_ect_unit_data(self, unit_id: str) -> Optional[Dict]:
        """
        ดึงข้อมูลจาก กกต. ระดับหน่วยเลือกตั้ง
        
        Args:
            unit_id: รหัสหน่วยเลือกตั้ง
        """
        try:
            # ตัวอย่าง URL structure (ปรับตามจริง)
            url = f"{self.ect_base_url}/results/unit/{unit_id}.json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  ไม่พบข้อมูล กกต. สำหรับหน่วย {unit_id}")
                return None
        except Exception as e:
            print(f"❌ Error fetching ECT data: {str(e)}")
            return None
    
    def fetch_vote62_unit_data(self, unit_id: str) -> Optional[Dict]:
        """
        ดึงข้อมูลจาก Vote62.com ระดับหน่วยเลือกตั้ง
        
        Args:
            unit_id: รหัสหน่วยเลือกตั้ง
        """
        try:
            # ตัวอย่าง API call (ปรับตาม Vote62 API จริง)
            url = f"{self.vote62_base_url}/units/{unit_id}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  ไม่พบข้อมูล Vote62 สำหรับหน่วย {unit_id}")
                return None
        except Exception as e:
            print(f"❌ Error fetching Vote62 data: {str(e)}")
            return None
    
    def compare_unit_results(self, unit_id: str, constituency: str) -> VerificationResult:
        """
        เปรียบเทียบผลคะแนนระดับหน่วยเลือกตั้ง
        
        Args:
            unit_id: รหัสหน่วยเลือกตั้ง
            constituency: ชื่อเขตเลือกตั้ง
        """
        print(f"\n🔍 กำลังตรวจสอบหน่วย {unit_id} ({constituency})...")
        
        # ดึงข้อมูลจากทั้งสองแหล่ง
        ect_data = self.fetch_ect_unit_data(unit_id)
        vote62_data = self.fetch_vote62_unit_data(unit_id)
        
        if not ect_data or not vote62_data:
            return None
        
        # เปรียบเทียบคะแนนรวม
        ect_total = self._calculate_total_votes(ect_data)
        vote62_total = self._calculate_total_votes(vote62_data)
        difference = abs(ect_total - vote62_total)
        
        # วิเคราะห์รายละเอียด
        details = self._detailed_comparison(ect_data, vote62_data)
        
        # ประเมินระดับความร้ายแรง
        discrepancy_level = self._assess_discrepancy(difference, ect_total, details)
        
        result = VerificationResult(
            unit_id=unit_id,
            constituency=constituency,
            ect_total=ect_total,
            vote62_total=vote62_total,
            difference=difference,
            discrepancy_level=discrepancy_level,
            details=details,
            timestamp=datetime.now().isoformat()
        )
        
        # บันทึกผล
        self._record_result(result)
        self._print_result(result)
        
        return result
    
    def _calculate_total_votes(self, data: Dict) -> int:
        """คำนวณคะแนนรวม"""
        total = 0
        
        # ปรับตามโครงสร้างข้อมูลจริง
        if 'candidates' in data:
            for candidate in data['candidates']:
                total += candidate.get('votes', 0)
        elif 'parties' in data:
            for party in data['parties']:
                total += party.get('votes', 0)
        
        return total
    
    def _detailed_comparison(self, ect_data: Dict, vote62_data: Dict) -> Dict:
        """
        เปรียบเทียบรายละเอียดทุกพรรค/ผู้สมัคร
        
        Returns:
            Dict containing detailed discrepancies
        """
        details = {
            'matching_candidates': [],
            'discrepant_candidates': [],
            'missing_in_ect': [],
            'missing_in_vote62': []
        }
        
        # สร้าง mapping ของผู้สมัคร/พรรค
        ect_votes = self._create_vote_mapping(ect_data)
        vote62_votes = self._create_vote_mapping(vote62_data)
        
        # เปรียบเทียบแต่ละรายการ
        all_keys = set(ect_votes.keys()) | set(vote62_votes.keys())
        
        for key in all_keys:
            ect_val = ect_votes.get(key, 0)
            vote62_val = vote62_votes.get(key, 0)
            
            if ect_val == vote62_val and ect_val > 0:
                details['matching_candidates'].append({
                    'name': key,
                    'votes': ect_val
                })
            elif ect_val != vote62_val:
                details['discrepant_candidates'].append({
                    'name': key,
                    'ect_votes': ect_val,
                    'vote62_votes': vote62_val,
                    'difference': abs(ect_val - vote62_val)
                })
            
            if ect_val == 0 and vote62_val > 0:
                details['missing_in_ect'].append(key)
            elif vote62_val == 0 and ect_val > 0:
                details['missing_in_vote62'].append(key)
        
        return details
    
    def _create_vote_mapping(self, data: Dict) -> Dict[str, int]:
        """สร้าง mapping ชื่อ -> คะแนน"""
        mapping = {}
        
        if 'candidates' in data:
            for candidate in data['candidates']:
                name = candidate.get('name', 'unknown')
                votes = candidate.get('votes', 0)
                mapping[name] = votes
        elif 'parties' in data:
            for party in data['parties']:
                name = party.get('name', 'unknown')
                votes = party.get('votes', 0)
                mapping[name] = votes
        
        return mapping
    
    def _assess_discrepancy(self, difference: int, total: int, details: Dict) -> DiscrepancyLevel:
        """
        ประเมินระดับความร้ายแรงของความแตกต่าง
        
        เกณฑ์:
        - 0 คะแนน: IDENTICAL
        - 1-10 คะแนน หรือ <0.5%: MINOR
        - 11-50 คะแนน หรือ 0.5-2%: SIGNIFICANT
        - >50 คะแนน หรือ >2%: CRITICAL
        """
        if difference == 0:
            return DiscrepancyLevel.IDENTICAL
        
        percentage = (difference / total * 100) if total > 0 else 0
        
        # ตรวจสอบรายละเอียด
        critical_issues = len(details.get('missing_in_ect', [])) > 0 or \
                         len(details.get('missing_in_vote62', [])) > 0
        
        if critical_issues or difference > 50 or percentage > 2:
            return DiscrepancyLevel.CRITICAL
        elif difference > 10 or percentage > 0.5:
            return DiscrepancyLevel.SIGNIFICANT
        else:
            return DiscrepancyLevel.MINOR
    
    def _record_result(self, result: VerificationResult):
        """บันทึกผลการตรวจสอบ"""
        self.discrepancies.append(result)
        self.stats['total_units_compared'] += 1
        
        if result.discrepancy_level == DiscrepancyLevel.IDENTICAL:
            self.stats['identical'] += 1
        elif result.discrepancy_level == DiscrepancyLevel.MINOR:
            self.stats['minor_diff'] += 1
        elif result.discrepancy_level == DiscrepancyLevel.SIGNIFICANT:
            self.stats['significant_diff'] += 1
        else:
            self.stats['critical_diff'] += 1
    
    def _print_result(self, result: VerificationResult):
        """แสดงผลการตรวจสอบ"""
        print(f"\n{'='*60}")
        print(f"หน่วย: {result.unit_id} - {result.constituency}")
        print(f"{'='*60}")
        print(f"คะแนนรวม กกต.:    {result.ect_total:,} คะแนน")
        print(f"คะแนนรวม Vote62:  {result.vote62_total:,} คะแนน")
        print(f"ส่วนต่าง:         {result.difference:,} คะแนน")
        print(f"ระดับ:            {result.discrepancy_level.value}")
        
        if result.details['discrepant_candidates']:
            print(f"\n⚠️  พบความแตกต่างในรายการต่อไปนี้:")
            for disc in result.details['discrepant_candidates']:
                print(f"  - {disc['name']}: กกต.={disc['ect_votes']:,}, "
                      f"Vote62={disc['vote62_votes']:,}, "
                      f"ต่าง={disc['difference']:,}")
        
        if result.details['missing_in_ect']:
            print(f"\n🚨 พบใน Vote62 แต่ไม่มีใน กกต.:")
            for name in result.details['missing_in_ect']:
                print(f"  - {name}")
        
        if result.details['missing_in_vote62']:
            print(f"\n🚨 พบใน กกต. แต่ไม่มีในVote62:")
            for name in result.details['missing_in_vote62']:
                print(f"  - {name}")
    
    def batch_compare(self, unit_ids: List[str], constituencies: Dict[str, str]) -> pd.DataFrame:
        """
        เปรียบเทียบหลายหน่วยพร้อมกัน
        
        Args:
            unit_ids: รายการรหัสหน่วยเลือกตั้ง
            constituencies: mapping unit_id -> constituency name
        """
        results = []
        
        print(f"\n🚀 เริ่มเปรียบเทียบ {len(unit_ids)} หน่วย...")
        
        for i, unit_id in enumerate(unit_ids, 1):
            print(f"\nProgress: {i}/{len(unit_ids)}")
            constituency = constituencies.get(unit_id, "ไม่ระบุ")
            result = self.compare_unit_results(unit_id, constituency)
            
            if result:
                results.append({
                    'unit_id': result.unit_id,
                    'constituency': result.constituency,
                    'ect_total': result.ect_total,
                    'vote62_total': result.vote62_total,
                    'difference': result.difference,
                    'discrepancy_level': result.discrepancy_level.value,
                    'timestamp': result.timestamp
                })
        
        df = pd.DataFrame(results)
        return df
    
    def generate_summary_report(self) -> Dict:
        """สร้างรายงานสรุป"""
        total = self.stats['total_units_compared']
        
        if total == 0:
            return {'error': 'ยังไม่มีข้อมูลการเปรียบเทียบ'}
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_units_compared': total,
                'identical_units': self.stats['identical'],
                'minor_discrepancies': self.stats['minor_diff'],
                'significant_discrepancies': self.stats['significant_diff'],
                'critical_discrepancies': self.stats['critical_diff']
            },
            'percentages': {
                'identical': (self.stats['identical'] / total) * 100,
                'minor': (self.stats['minor_diff'] / total) * 100,
                'significant': (self.stats['significant_diff'] / total) * 100,
                'critical': (self.stats['critical_diff'] / total) * 100
            },
            'critical_units': [
                {
                    'unit_id': r.unit_id,
                    'constituency': r.constituency,
                    'difference': r.difference
                }
                for r in self.discrepancies
                if r.discrepancy_level == DiscrepancyLevel.CRITICAL
            ]
        }
        
        return report
    
    def print_summary(self):
        """แสดงสรุปผลการตรวจสอบ"""
        report = self.generate_summary_report()
        
        if 'error' in report:
            print(report['error'])
            return
        
        print("\n" + "="*80)
        print("📊 สรุปผลการเปรียบเทียบข้อมูล กกต. vs Vote62.com")
        print("="*80)
        print(f"\nจำนวนหน่วยที่เปรียบเทียบ: {report['summary']['total_units_compared']:,} หน่วย")
        print(f"\n✅ เหมือนกันเป๊ะ:        {report['summary']['identical_units']:,} หน่วย ({report['percentages']['identical']:.1f}%)")
        print(f"⚠️  แตกต่างเล็กน้อย:     {report['summary']['minor_discrepancies']:,} หน่วย ({report['percentages']['minor']:.1f}%)")
        print(f"🚨 แตกต่างมาก:          {report['summary']['significant_discrepancies']:,} หน่วย ({report['percentages']['significant']:.1f}%)")
        print(f"🔴 แตกต่างร้ายแรง:      {report['summary']['critical_discrepancies']:,} หน่วย ({report['percentages']['critical']:.1f}%)")
        
        if report['critical_units']:
            print(f"\n🔴 รายการหน่วยที่ต้องตรวจสอบด่วน:")
            for unit in report['critical_units'][:10]:  # แสดงแค่ 10 อันดับแรก
                print(f"  - {unit['unit_id']} ({unit['constituency']}): ต่าง {unit['difference']:,} คะแนน")
        
        print("\n" + "="*80)
    
    def export_to_csv(self, filename: str = "verification_results.csv"):
        """Export ผลการเปรียบเทียบเป็น CSV"""
        if not self.discrepancies:
            print("ไม่มีข้อมูลให้ export")
            return
        
        data = []
        for r in self.discrepancies:
            data.append({
                'unit_id': r.unit_id,
                'constituency': r.constituency,
                'ect_total': r.ect_total,
                'vote62_total': r.vote62_total,
                'difference': r.difference,
                'discrepancy_level': r.discrepancy_level.value,
                'timestamp': r.timestamp
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ Export สำเร็จ: {filename}")
    
    def create_visualization_data(self) -> Dict:
        """สร้างข้อมูลสำหรับ visualization"""
        if not self.discrepancies:
            return {'error': 'ไม่มีข้อมูล'}
        
        # จัดกลุ่มตามระดับความร้ายแรง
        grouped = {
            'identical': [],
            'minor': [],
            'significant': [],
            'critical': []
        }
        
        for r in self.discrepancies:
            key = r.discrepancy_level.name.lower()
            grouped[key].append({
                'unit_id': r.unit_id,
                'constituency': r.constituency,
                'difference': r.difference
            })
        
        return grouped


def demo():
    """ตัวอย่างการใช้งาน"""
    print("="*80)
    print("ระบบเปรียบเทียบข้อมูล กกต. vs Vote62.com")
    print("="*80)
    
    comparator = Vote62Comparator()
    
    # ตัวอย่างการเปรียบเทียบหน่วยเดียว
    print("\n📍 ตัวอย่าง: เปรียบเทียบหน่วยเลือกตั้งเดี่ยว")
    # result = comparator.compare_unit_results("001001", "กรุงเทพมหานคร เขต 1")
    
    # ตัวอย่างการเปรียบเทียบหลายหน่วย
    print("\n📍 ตัวอย่าง: เปรียบเทียบหลายหน่วยพร้อมกัน")
    sample_units = ["001001", "001002", "001003"]
    sample_constituencies = {
        "001001": "กรุงเทพมหานคร เขต 1",
        "001002": "กรุงเทพมหานคร เขต 1", 
        "001003": "กรุงเทพมหานคร เขต 1"
    }
    
    # df = comparator.batch_compare(sample_units, sample_constituencies)
    # print(df)
    
    # แสดงสรุป
    # comparator.print_summary()
    
    # Export ผล
    # comparator.export_to_csv("ect_vs_vote62_comparison.csv")
    
    print("\n" + "="*80)
    print("💡 วิธีใช้งานจริง:")
    print("1. เตรียมรายการ unit_id ทั้งหมดที่ต้องการเปรียบเทียบ")
    print("2. รัน batch_compare() เพื่อเปรียบเทียบทีละมากๆ")
    print("3. ตรวจสอบหน่วยที่มี CRITICAL discrepancy ก่อน")
    print("4. Export ผลเป็น CSV เพื่อวิเคราะห์ต่อ")
    print("="*80)


if __name__ == "__main__":
    demo()
