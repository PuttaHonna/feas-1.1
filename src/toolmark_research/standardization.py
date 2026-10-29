"""
Working-Copy Image Standardization for Controlled Toolmark Imagery
Standardizes lighting, center cropping, and scale strictly on working copies.
Original source evidence remains untouched.
"""

from pathlib import Path
from typing import Tuple, Optional
import cv2
import numpy as np

from src.common.hashing import calculate_sha256


def standardize_toolmark_working_copy(
    working_copy_path: Path,
    output_standardized_path: Path,
    target_dim: int = 256,
    normalize_lighting: bool = True,
) -> Tuple[Path, str]:
    """
    Standardizes crop, scale, and illumination on derived working copies only.
    
    Returns:
        Tuple of (standardized_path, sha256_hash)
    """
    in_p = Path(working_copy_path)
    if not in_p.exists():
        raise FileNotFoundError(f"Working copy not found: {in_p}")

    img = cv2.imread(str(in_p))
    if img is None:
        raise ValueError(f"Failed to decode working copy image: {in_p}")

    h, w = img.shape[:2]

    # 1. Square center crop
    crop_size = min(h, w)
    start_y = (h - crop_size) // 2
    start_x = (w - crop_size) // 2
    cropped = img[start_y:start_y + crop_size, start_x:start_x + crop_size]

    # 2. Rescale to target dimension
    resized = cv2.resize(cropped, (target_dim, target_dim), interpolation=cv2.INTER_AREA)

    # 3. Standardize lighting via CLAHE on L channel
    if normalize_lighting:
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_norm = clahe.apply(l)
        lab_norm = cv2.merge((l_norm, a, b))
        out_img = cv2.cvtColor(lab_norm, cv2.COLOR_LAB2BGR)
    else:
        out_img = resized

    out_p = Path(output_standardized_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_p), out_img)

    sha256_hash = calculate_sha256(out_p)
    return out_p, sha256_hash
