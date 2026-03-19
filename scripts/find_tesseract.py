# -*- coding: utf-8 -*-
import os

candidates = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'D:\Program Files\Tesseract-OCR\tesseract.exe',
    r'D:\Tesseract-OCR\tesseract.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe'),
    os.path.expandvars(r'%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe'),
    os.path.expandvars(r'%USERPROFILE%\AppData\Local\Tesseract-OCR\tesseract.exe'),
    os.path.expandvars(r'%PROGRAMFILES%\Tesseract-OCR\tesseract.exe'),
]

# Also search PATH
import shutil
path_result = shutil.which('tesseract')
if path_result:
    print(f"FOUND in PATH: {path_result}")

found = False
for p in candidates:
    exists = os.path.exists(p)
    if exists:
        print(f"  FOUND: {p}")
        found = True
    else:
        print(f"  not found: {p}")

if not found and not path_result:
    print("\nTesseract not found in any standard location.")
    print("Please tell me the path where you installed Tesseract.")
    # Try searching common drives
    for drive in ['C:', 'D:', 'E:']:
        tess_dir = os.path.join(drive, os.sep, 'Tesseract-OCR')
        if os.path.isdir(tess_dir):
            print(f"  Found directory: {tess_dir}")
            for f in os.listdir(tess_dir):
                print(f"    {f}")
