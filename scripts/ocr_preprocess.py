# -*- coding: utf-8 -*-
"""Image preprocessing for OCR accuracy improvement.

Techniques:
  1. DPI boost (200 → 300)
  2. Grayscale conversion
  3. Adaptive binarization (handles uneven lighting from scanner)
  4. Deskew (straighten rotated scans)
  5. Denoise (remove scanner artifacts)
  6. Contrast enhancement (CLAHE)

Usage:
  from ocr_preprocess import preprocess_png
  enhanced_png = preprocess_png(raw_png_bytes, dpi_boost=True)
"""
import io
import math

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def preprocess_png(png_bytes, deskew=True, denoise=True, binarize=False,
                   enhance_contrast=True, sharpen=True):
    """Apply preprocessing pipeline to PNG image bytes.
    
    Args:
        png_bytes: Raw PNG image bytes
        deskew: Correct rotation (requires OpenCV)
        denoise: Remove noise (requires OpenCV)
        binarize: Convert to binary (black/white) — aggressive, use for fallback
        enhance_contrast: Apply CLAHE contrast enhancement
        sharpen: Apply sharpening filter
    
    Returns:
        Processed PNG bytes
    """
    if HAS_CV2 and HAS_NUMPY:
        return _preprocess_cv2(png_bytes, deskew, denoise, binarize, enhance_contrast, sharpen)
    elif HAS_PIL:
        return _preprocess_pil(png_bytes, enhance_contrast, sharpen)
    else:
        # No image processing libraries available
        return png_bytes


def _preprocess_cv2(png_bytes, deskew, denoise, binarize, enhance_contrast, sharpen):
    """OpenCV-based preprocessing pipeline."""
    # Decode
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return png_bytes
    
    # 1. Convert to grayscale for processing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Deskew
    if deskew:
        gray = _deskew_cv2(gray)
    
    # 3. Denoise
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # 4. Contrast enhancement (CLAHE)
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    
    # 5. Sharpen
    if sharpen:
        kernel = np.array([[-0.5, -0.5, -0.5],
                           [-0.5,  5.0, -0.5],
                           [-0.5, -0.5, -0.5]])
        gray = cv2.filter2D(gray, -1, kernel)
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    
    # 6. Binarize (optional — aggressive)
    if binarize:
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=15, C=8
        )
    
    # Convert back to 3-channel for LLM (some models expect color)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    # Encode back to PNG
    success, encoded = cv2.imencode('.png', result)
    if success:
        return encoded.tobytes()
    return png_bytes


def _deskew_cv2(gray):
    """Detect and correct skew using Hough line detection."""
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, threshold=100,
                            minLineLength=gray.shape[1] // 4,
                            maxLineGap=10)
    
    if lines is None or len(lines) < 3:
        return gray
    
    # Calculate angles of detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x2 - x1) < 1:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Only consider near-horizontal lines (within ±15°)
        if abs(angle) < 15:
            angles.append(angle)
    
    if not angles:
        return gray
    
    # Median angle (robust to outliers)
    median_angle = sorted(angles)[len(angles) // 2]
    
    # Only correct if skew is significant (>0.3°) but not too large (>5°)
    if abs(median_angle) < 0.3 or abs(median_angle) > 5.0:
        return gray
    
    # Rotate to correct
    h, w = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def _preprocess_pil(png_bytes, enhance_contrast, sharpen):
    """PIL/Pillow-based fallback preprocessing."""
    img = Image.open(io.BytesIO(png_bytes))
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Contrast enhancement
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
    
    # Sharpen
    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)
    
    # Convert back to RGB
    img = img.convert('RGB')
    
    # Encode
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def check_dependencies():
    """Check which preprocessing dependencies are available."""
    status = {
        'numpy': HAS_NUMPY,
        'opencv': HAS_CV2,
        'pillow': HAS_PIL,
    }
    level = 'full' if all(status.values()) else ('basic' if HAS_PIL else 'none')
    return status, level


# ─── CLI test ───────────────────────────────────────────────────────

if __name__ == '__main__':
    status, level = check_dependencies()
    print(f"Preprocessing dependencies: {level}")
    for lib, available in status.items():
        print(f"  {lib}: {'✅' if available else '❌'}")
    
    if level == 'none':
        print("\nInstall: pip install numpy opencv-python-headless Pillow")
