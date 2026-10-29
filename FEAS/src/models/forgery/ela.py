"""
Forensic Evidence Analysis System (FEAS) - Error Level Analysis (ELA)
Computes compression artifact discrepancies by resaving at 95% JPEG quality and calculating pixel deltas.
"""

import io
from pathlib import Path
from typing import Any, Dict, Tuple, Union
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from src.config import ELA_QUALITY, ELA_SCALE, TEMP_DIR


def perform_ela(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    quality: int = ELA_QUALITY,
    scale: float = ELA_SCALE
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Perform Error Level Analysis (ELA) on an image.
    
    1. Convert input to RGB PIL Image.
    2. Save image to in-memory JPEG buffer with specified quality (e.g. 95%).
    3. Re-open compressed image and compute absolute pixel difference.
    4. Amplify difference to make compression error visually prominent.
    5. Convert delta into RGB heatmap and compute statistical metrics.
    
    Returns:
        (ela_visual_bgr: np.ndarray, metrics: Dict[str, float])
    """
    if isinstance(image_input, (str, Path)):
        orig_img = Image.open(str(image_input)).convert("RGB")
    elif isinstance(image_input, np.ndarray):
        # OpenCV BGR -> RGB
        if len(image_input.shape) == 2:
            rgb_arr = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
        else:
            rgb_arr = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
        orig_img = Image.fromarray(rgb_arr)
    elif isinstance(image_input, Image.Image):
        orig_img = image_input.convert("RGB")
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    # Resave to in-memory buffer at specified JPEG quality
    buffer = io.BytesIO()
    orig_img.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    resaved_img = Image.open(buffer).convert("RGB")

    # Compute difference
    diff = ImageChops.difference(orig_img, resaved_img)
    
    # Calculate extrema
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema]) if extrema else 0
    if max_diff == 0:
        max_diff = 1

    # Enhance difference
    scale_factor = min(scale, 255.0 / max_diff)
    enhancer = ImageEnhance.Brightness(diff)
    diff_enhanced = enhancer.enhance(scale_factor)

    # Convert to numpy array (RGB -> BGR for OpenCV consistency)
    diff_arr = np.array(diff)
    diff_enhanced_arr = np.array(diff_enhanced)
    
    # Gray representation for statistics
    gray_diff = cv2.cvtColor(diff_arr, cv2.COLOR_RGB2GRAY)
    mean_err = float(np.mean(gray_diff))
    max_err = float(np.max(gray_diff))
    std_err = float(np.std(gray_diff))

    # Adaptive statistical outlier threshold for non-uniform compression blocks
    adaptive_thresh = max(1.5, mean_err + 1.20 * std_err)
    high_error_pixels = int(np.sum(gray_diff > adaptive_thresh))
    total_pixels = max(1, gray_diff.shape[0] * gray_diff.shape[1])
    raw_ratio = float(high_error_pixels / total_pixels)

    # Calibrated tamper ratio reflecting compression matrix inconsistency
    if max_err >= 4.0 and std_err >= 0.20:
        tamper_ratio = min(0.92, max(0.05, round(raw_ratio * 1.45, 4)))
    elif max_err > 1.0:
        tamper_ratio = min(0.50, round(raw_ratio, 4))
    else:
        tamper_ratio = 0.0

    # Percentile-based contrast stretch for vivid thermal FLIR visualization
    p99 = float(np.percentile(gray_diff, 99.2))
    if p99 > 0:
        norm_diff = np.clip((gray_diff.astype(np.float32) / p99) * 255.0, 0, 255).astype(np.uint8)
    else:
        norm_diff = cv2.normalize(gray_diff.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Apply CLAHE to highlight localized compression anomalies
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    enhanced_diff = clahe.apply(norm_diff)
    heatmap_bgr = cv2.applyColorMap(enhanced_diff, cv2.COLORMAP_JET)

    metrics = {
        "mean_error": round(mean_err, 4),
        "max_error": round(max_err, 4),
        "std_error": round(std_err, 4),
        "tamper_ratio": round(tamper_ratio, 4),
        "mean_diff": round(mean_err, 4),
        "max_diff": round(max_err, 4),
        "anomaly_threshold": round(adaptive_thresh, 4),
    }

    return heatmap_bgr, metrics
