#!/usr/bin/env python3
"""
โมดูลการวิเคราะห์ทางสถิติขั้นสูง
Advanced Statistical Analysis for Election Data
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from collections import Counter
import math


class AdvancedElectionAnalytics:
    """คลาสสำหรับการวิเคราะห์ขั้นสูง"""
    
    def __init__(self):
        self.benford_expected = self._calculate_benford_distribution()
    
    def _calculate_benford_distribution(self) -> Dict[int, float]:
        """คำนวณการกระจายตัวตาม Benford's Law"""
        return {d: math.log10(1 + 1/d) for d in range(1, 10)}
    
    def benford_law_test(self, data: List[int]) -> Dict:
        """
        ทดสอบข้อมูลด้วย Benford's Law
        
        Benford's Law: ในชุดข้อมูลจำนวนมาก เลขหลักหน้าควรกระจายตัวตาม
        P(d) = log10(1 + 1/d)
        
        หากข้อมูลถูกปลอมแปลง มักจะไม่เป็นไปตามกฎนี้
        """
        # แยกเลขหลักหน้า
        first_digits = [int(str(abs(x))[0]) for x in data if x > 0]
        
        if len(first_digits) < 30:
            return {
                'valid': False,
                'reason': 'ข้อมูลน้อยเกินไป (ต้อง >= 30 รายการ)',
                'sample_size': len(first_digits)
            }
        
        # นับความถี่
        observed_freq = Counter(first_digits)
        total = len(first_digits)
        
        # คำนวณ Chi-Square
        chi_square = 0
        details = {}
        
        for digit in range(1, 10):
            observed = observed_freq.get(digit, 0)
            expected = self.benford_expected[digit] * total
            
            if expected > 0:
                chi_square += ((observed - expected) ** 2) / expected
            
            details[digit] = {
                'observed': observed,
                'observed_pct': (observed / total) * 100,
                'expected': expected,
                'expected_pct': self.benford_expected[digit] * 100
            }
        
        # ทดสอบที่ df = 8 (9 digits - 1)
        p_value = 1 - stats.chi2.cdf(chi_square, df=8)
        
        return {
            'valid': True,
            'chi_square': chi_square,
            'p_value': p_value,
            'conforms_to_benford': p_value > 0.05,  # ถ้า > 0.05 แสดงว่าเป็นไปตามกฎ
            'details': details,
            'interpretation': self._interpret_benford_result(p_value)
        }
    
    def _interpret_benford_result(self, p_value: float) -> str:
        """แปลความหมายผลทดสอบ"""
        if p_value > 0.05:
            return "✅ ข้อมูลเป็นไปตาม Benford's Law (ไม่น่าจะถูกปลอมแปลง)"
        elif p_value > 0.01:
            return "⚠️  ควรตรวจสอบเพิ่มเติม"
        else:
            return "🚨 ข้อมูลไม่เป็นไปตาม Benford's Law (น่าสงสัยว่าถูกปลอมแปลง)"
    
    def detect_vote_stuffing_patterns(self, df: pd.DataFrame) -> Dict:
        """
        ตรวจหาร pattern ของการยัดบัตร
        
        สัญญาณ:
        1. คะแนนจำนวนกลมๆ (round numbers) มากเกินไป
        2. ความแปรปรวนต่ำผิดปกติ
        3. คะแนนเพิ่มขึ้นแบบ linear มากเกินไป
        """
        results = {
            'round_numbers': self._check_round_numbers(df),
            'variance_analysis': self._analyze_variance(df),
            'linear_patterns': self._check_linear_patterns(df)
        }
        
        return results
    
    def _check_round_numbers(self, df: pd.DataFrame) -> Dict:
        """ตรวจสอบตัวเลขกลมๆ"""
        if 'votes' not in df.columns:
            return {'valid': False}
        
        votes = df['votes'].values
        round_nums = sum(1 for v in votes if v % 100 == 0 or v % 50 == 0)
        total = len(votes)
        
        round_pct = (round_nums / total) * 100
        
        return {
            'round_numbers_count': round_nums,
            'total_count': total,
            'percentage': round_pct,
            'suspicious': round_pct > 20,  # ถ้า > 20% น่าสงสัย
            'interpretation': f"{'🚨 น่าสงสัย' if round_pct > 20 else '✅ ปกติ'}: {round_pct:.1f}% เป็นเลขกลมๆ"
        }
    
    def _analyze_variance(self, df: pd.DataFrame) -> Dict:
        """วิเคราะห์ความแปรปรวน"""
        if 'votes' not in df.columns:
            return {'valid': False}
        
        votes = df['votes'].values
        variance = np.var(votes)
        std_dev = np.std(votes)
        cv = (std_dev / np.mean(votes)) * 100  # Coefficient of Variation
        
        return {
            'variance': variance,
            'std_dev': std_dev,
            'coefficient_of_variation': cv,
            'suspicious': cv < 10,  # CV ต่ำมาก อาจหมายถึงข้อมูลถูกปรับแต่ง
            'interpretation': f"{'🚨 ความแปรปรวนต่ำผิดปกติ' if cv < 10 else '✅ ปกติ'}: CV = {cv:.1f}%"
        }
    
    def _check_linear_patterns(self, df: pd.DataFrame) -> Dict:
        """ตรวจหา linear patterns"""
        if 'votes' not in df.columns or len(df) < 10:
            return {'valid': False}
        
        votes = df['votes'].values
        x = np.arange(len(votes))
        
        # คำนวณ correlation
        correlation = np.corrcoef(x, votes)[0, 1]
        
        return {
            'correlation': correlation,
            'highly_linear': abs(correlation) > 0.95,
            'suspicious': abs(correlation) > 0.95,
            'interpretation': f"{'🚨 เป็น linear มากผิดปกติ' if abs(correlation) > 0.95 else '✅ ปกติ'}: r = {correlation:.3f}"
        }
    
    def compare_with_historical_data(self, current: pd.DataFrame, 
                                     historical: pd.DataFrame) -> Dict:
        """
        เปรียบเทียบกับข้อมูลการเลือกตั้งครั้งก่อน
        
        หา swing ที่ผิดปกติ
        """
        if 'constituency_id' not in current.columns:
            return {'valid': False}
        
        merged = pd.merge(current, historical, 
                         on='constituency_id', 
                         suffixes=('_current', '_historical'))
        
        if 'votes_current' in merged.columns and 'votes_historical' in merged.columns:
            merged['swing'] = ((merged['votes_current'] - merged['votes_historical']) / 
                              merged['votes_historical']) * 100
            
            # หา outliers
            Q1 = merged['swing'].quantile(0.25)
            Q3 = merged['swing'].quantile(0.75)
            IQR = Q3 - Q1
            
            outliers = merged[
                (merged['swing'] < Q1 - 1.5 * IQR) | 
                (merged['swing'] > Q3 + 1.5 * IQR)
            ]
            
            return {
                'valid': True,
                'mean_swing': merged['swing'].mean(),
                'median_swing': merged['swing'].median(),
                'outliers_count': len(outliers),
                'outliers': outliers[['constituency_id', 'swing']].to_dict('records'),
                'interpretation': f"พบ {len(outliers)} เขตที่มี swing ผิดปกติ"
            }
        
        return {'valid': False}
    
    def spatial_autocorrelation(self, df: pd.DataFrame) -> Dict:
        """
        ทดสอบ Spatial Autocorrelation (Moran's I)
        
        ตรวจสอบว่าเขตใกล้เคียงกันมีแนวโน้มคะแนนใกล้เคียงกันหรือไม่
        หากผิดปกติ อาจบ่งบอกถึงการโกงที่เป็นระบบ
        """
        # Placeholder - ต้องมีข้อมูล geospatial จริง
        return {
            'valid': False,
            'reason': 'ต้องการข้อมูล latitude, longitude',
            'note': 'ใช้ pysal หรือ geopandas สำหรับการวิเคราะห์เต็มรูปแบบ'
        }
    
    def generate_full_report(self, df: pd.DataFrame) -> Dict:
        """สร้างรายงานวิเคราะห์ครบชุด"""
        report = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_constituencies': len(df),
            'analyses': {}
        }
        
        # Benford's Law
        if 'votes' in df.columns:
            votes_list = df['votes'].dropna().astype(int).tolist()
            if len(votes_list) >= 30:
                report['analyses']['benford_law'] = self.benford_law_test(votes_list)
        
        # Vote Stuffing Patterns
        report['analyses']['vote_stuffing'] = self.detect_vote_stuffing_patterns(df)
        
        # Overall Assessment
        suspicious_flags = 0
        
        if 'benford_law' in report['analyses']:
            if not report['analyses']['benford_law'].get('conforms_to_benford', True):
                suspicious_flags += 1
        
        if report['analyses']['vote_stuffing']['round_numbers'].get('suspicious', False):
            suspicious_flags += 1
        
        if report['analyses']['vote_stuffing']['variance_analysis'].get('suspicious', False):
            suspicious_flags += 1
        
        report['risk_level'] = self._calculate_risk_level(suspicious_flags)
        
        return report
    
    def _calculate_risk_level(self, flags: int) -> str:
        """คำนวณระดับความเสี่ยง"""
        if flags == 0:
            return "🟢 LOW - ไม่พบสัญญาณน่าสงสัย"
        elif flags == 1:
            return "🟡 MEDIUM - พบสัญญาณน่าสงสัย 1 รายการ ควรตรวจสอบเพิ่มเติม"
        elif flags == 2:
            return "🟠 HIGH - พบสัญญาณน่าสงสัยหลายรายการ ต้องตรวจสอบโดยด่วน"
        else:
            return "🔴 CRITICAL - พบสัญญาณน่าสงสัยหลายรายการ ต้องสอบสวนทันที"


def demo_analysis():
    """ตัวอย่างการใช้งาน"""
    print("=== ตัวอย่างการวิเคราะห์ทางสถิติ ===\n")
    
    analytics = AdvancedElectionAnalytics()
    
    # สร้างข้อมูลตัวอย่าง
    np.random.seed(42)
    
    # ชุดข้อมูลปกติ (เป็นไปตาม Benford)
    normal_data = np.random.lognormal(mean=8, sigma=2, size=200).astype(int)
    
    # ชุดข้อมูลปลอม (uniform distribution - ไม่เป็นไปตาม Benford)
    fake_data = np.random.randint(1000, 9999, size=200)
    
    print("1. ทดสอบข้อมูลปกติ:")
    result1 = analytics.benford_law_test(normal_data.tolist())
    print(f"   Chi-square: {result1['chi_square']:.3f}")
    print(f"   P-value: {result1['p_value']:.3f}")
    print(f"   {result1['interpretation']}\n")
    
    print("2. ทดสอบข้อมูลปลอม:")
    result2 = analytics.benford_law_test(fake_data.tolist())
    print(f"   Chi-square: {result2['chi_square']:.3f}")
    print(f"   P-value: {result2['p_value']:.3f}")
    print(f"   {result2['interpretation']}\n")
    
    # ตัวอย่าง DataFrame
    df = pd.DataFrame({
        'constituency_id': range(100),
        'votes': normal_data[:100]
    })
    
    print("3. ตรวจหารูปแบบการยัดบัตร:")
    stuffing_result = analytics.detect_vote_stuffing_patterns(df)
    print(f"   {stuffing_result['round_numbers']['interpretation']}")
    print(f"   {stuffing_result['variance_analysis']['interpretation']}")
    print(f"   {stuffing_result['linear_patterns']['interpretation']}\n")
    
    print("4. รายงานภาพรวม:")
    full_report = analytics.generate_full_report(df)
    print(f"   Risk Level: {full_report['risk_level']}")


if __name__ == "__main__":
    demo_analysis()
