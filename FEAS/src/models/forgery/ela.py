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

    # Threshold for high error ratio
    high_error_pixels = np.sum(gray_diff > 15)
    total_pixels = gray_diff.shape[0] * gray_diff.shape[1]
    tamper_ratio = float(high_error_pixels / max(1, total_pixels))

    # Create colorful heatmap (OpenCV COLORMAP_JET)
    norm_diff = cv2.normalize(gray_diff.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)

    metrics = {
        "mean_error": round(mean_err, 4),
        "max_error": round(max_err, 4),
        "std_error": round(std_err, 4),
        "tamper_ratio": round(tamper_ratio, 4)
    }

    return heatmap_bgr, metrics
