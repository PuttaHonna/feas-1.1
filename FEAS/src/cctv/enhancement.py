"""
Deterministic CCTV Frame Enhancement Module.
Uses conventional, reproducible OpenCV algorithms only.
Never invents synthetic details and clearly identifies derived representations.
"""

from __future__ import annotations
from enum import Enum
import cv2
import numpy as np

DERIVED_FRAME_LABEL: str = (
    "Enhanced frame generated for visualization and automated analysis. "
    "Original footage remains unchanged."
)


class EnhancementMode(str, Enum):
    """Supported deterministic enhancement modes."""
    NONE = "none"
    BASIC = "basic"
    LOW_LIGHT = "low_light"


def apply_gamma_correction(image_bgr: np.ndarray, gamma: float = 1.3) -> np.ndarray:
    """Apply deterministic power-law gamma correction to brighten shadows."""
    inv_gamma = 1.0 / max(0.1, gamma)
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image_bgr, table)


def apply_clahe(image_bgr: np.ndarray, clip_limit: float = 2.0, tile_grid_size: int = 8) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) on the LAB Luminance channel."""
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    l_enhanced = clahe.apply(l)
    lab_enhanced = cv2.merge((l_enhanced, a, b))
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def apply_unsharp_mask(image_bgr: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Apply gentle deterministic unsharp mask to clarify edges without haloing."""
    blurred = cv2.GaussianBlur(image_bgr, (0, 0), sigmaX=1.5)
    sharpened = cv2.addWeighted(image_bgr, 1.0 + strength, blurred, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def enhance_frame(
    frame_bgr: np.ndarray,
    mode: EnhancementMode | str = EnhancementMode.BASIC
) -> np.ndarray:
    """Apply deterministic enhancement to a derived working frame.

    Args:
        frame_bgr: Input BGR video frame from working copy.
        mode: 'none', 'basic', or 'low_light'.

    Returns:
        Enhanced BGR frame. Original pixels remain unmodified in storage.
    """
    mode_str = str(mode).lower()
    if mode_str == EnhancementMode.NONE or mode_str == "none":
        return frame_bgr.copy()

    # Base copy
    derived = frame_bgr.copy()

    if mode_str == "low_light" or mode_str == EnhancementMode.LOW_LIGHT:
        # 1. Gentle gamma lift
        derived = apply_gamma_correction(derived, gamma=1.4)
        # 2. CLAHE with higher clip limit
        derived = apply_clahe(derived, clip_limit=3.0, tile_grid_size=8)
        # 3. Mild bilateral denoising to suppress sensor noise from dark scenes
        derived = cv2.bilateralFilter(derived, d=5, sigmaColor=35, sigmaSpace=35)
        # 4. Subtle unsharp mask
        derived = apply_unsharp_mask(derived, strength=0.3)

    elif mode_str == "basic" or mode_str == EnhancementMode.BASIC:
        # 1. Standard CLAHE
        derived = apply_clahe(derived, clip_limit=2.0, tile_grid_size=8)
        # 2. Very mild Gaussian blur to control high frequency artifacts
        blurred = cv2.GaussianBlur(derived, (3, 3), 0.5)
        derived = cv2.addWeighted(derived, 0.8, blurred, 0.2, 0)
        # 3. Subtle edge contrast
        derived = apply_unsharp_mask(derived, strength=0.25)

    return derived
