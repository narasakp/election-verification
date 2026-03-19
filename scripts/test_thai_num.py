# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ocr_cloud_vision import thai_text_to_number

tests = [
    ('สี่ร้อยเก้าสิบหก', 496),
    ('สามร้อยสิบเจ็ด', 317),
    ('สามร้อยเก้า', 309),
    ('หนึ่งร้อยหกสิบสาม', 163),
    ('สี่ร้อยแปดสิบ', 480),
    ('สี่สิบ', 40),
    ('ยี่สิบ', 20),
    ('สิบสอง', 12),
    ('สิบเอ็ด', 11),
    ('หนึ่งพันสองร้อยสามสิบสี่', 1234),
    ('เจ็ด', 7),
    ('หนึ่ง', 1),
    # OCR garbled — should fail gracefully
    ('สร้อยแห่งสิบหก', None),
    ('สามสมเจต', None),
    # Real OCR text from the form (with parentheses/noise)
    ('สามร้อยเก้า', 309),
    ('ร้อยแปดสิบ', 180),
    ('หนึ่งร้อยห้าสิบแปด', 158),
    ('แปดสิบสอง', 82),
]

passed = 0
for text, expected in tests:
    got = thai_text_to_number(text)
    ok = "PASS" if got == expected else "FAIL"
    if ok == "PASS":
        passed += 1
    print(f"  {ok}: '{text}' -> {got} (expect {expected})")

print(f"\n{passed}/{len(tests)} passed")
