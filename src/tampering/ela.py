"""
Error Level Analysis (ELA) & Compression Inconsistency Detector
A deterministic, signal-level forensic tool that highlights compression discrepancies
caused by image splicing and copy-move alterations.
"""

import io
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

from src.common.config import FORENSIC_CONFIG


def compute_ela(
    image_path: Path,
    output_ela_path: Path,
    quality: int = 90,
    scale: int = 15,
) -> Dict[str, Any]:
    """
    Computes Error Level Analysis (ELA) for a target image.
    1. Re-compresses the image at a known JPEG quality.
    2. Measures absolute pixel difference between original and re-compressed image.
    3. Amplifies differences to visualize compression artifacts.
    4. Computes statistical metrics (mean error, max error, variance).
    """
    image_path = Path(image_path)
    output_ela_path = Path(output_ela_path)
    output_ela_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as orig_img:
        orig_rgb = orig_img.convert("RGB")

    # Save to in-memory buffer at known quality
    buffer = io.BytesIO()
    orig_rgb.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    recompressed = Image.open(buffer)

    # Compute difference
    diff = ImageChops.difference(orig_rgb, recompressed)

    # Calculate statistics on raw difference before scaling
    diff_arr = np.array(diff, dtype=np.float32)
    mean_error = float(np.mean(diff_arr))
    max_error = float(np.max(diff_arr))
    std_error = float(np.std(diff_arr))

    # Scale the difference for human & machine inspection
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    scale_factor = min(scale, 255.0 / max_diff)

    scaled_diff = ImageEnhance.Brightness(diff).enhance(scale_factor)
    scaled_diff.save(output_ela_path, format="JPEG", quality=95)

    # An elevated standard deviation and local variance indicates mixed compression levels (tampering)
    high_discrepancy = std_error > 8.5 or max_error > 65.0

    return {
        "mean_error": round(mean_error, 3),
        "max_error": round(max_error, 3),
        "std_error": round(std_error, 3),
        "high_discrepancy_detected": bool(high_discrepancy),
        "ela_image_path": str(output_ela_path),
        "quality_level_analyzed": quality,
    }
