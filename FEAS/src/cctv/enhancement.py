"""
Deterministic & Deep Learning CCTV Video & Frame Enhancement Module.
=====================================================================
Supports:
1. Conventional deterministic OpenCV enhancement (reproducible, non-generative):
   - Power-law gamma correction
   - LAB-space CLAHE
   - Bilateral denoising & unsharp masking
2. Deep Learning Paired Enhancement:
   - LOL-v2: Single-frame illumination enhancement (SNR-Aware Low-Light Enhance).
   - SDSD: Multi-frame dynamic video enhancement with temporal anti-flicker consistency.
   - REDS: Video super-resolution reconstruction experiment (RealBasicVSR).

FORENSIC INTEGRITY RULE:
All enhanced frames are derived working copies. Original footage is immutable.
Generated fine textures from Super-Resolution (REDS/RealBasicVSR) are investigative
hypotheses and must NOT be introduced as authenticated evidence in legal proceedings.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union
import cv2
import numpy as np

DERIVED_FRAME_LABEL: str = (
    "Enhanced frame generated for visualization and automated analysis. "
    "Original footage remains unchanged."
)

SR_DISCLAIMER_LABEL: str = (
    "EXPERIMENTAL ARTIFACT: Generated textures are reconstructed via statistical prior "
    "inference (REDS/RealBasicVSR) and must NOT be presented as authenticated evidence in court."
)


class EnhancementMode(str, Enum):
    """Supported deterministic and deep learning enhancement modes."""
    NONE = "none"
    BASIC = "basic"
    LOW_LIGHT = "low_light"
    DEEP_LEARNING = "deep_learning"
    LOL_V2 = "lol_v2"
    SDSD_TEMPORAL = "sdsd_temporal"
    REDS_SR = "reds_sr"
    ADAPTIVE_SMART = "adaptive_smart"


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
    """Apply deterministic or deep learning enhancement to a derived working frame.

    Args:
        frame_bgr: Input BGR video frame from working copy.
        mode: 'none', 'basic', 'low_light', 'deep_learning', 'lol_v2', 'sdsd_temporal', or 'reds_sr'.

    Returns:
        Enhanced BGR frame. Original pixels remain unmodified in storage.
    """
    mode_str = str(mode).lower().replace("-", "_")
    if mode_str == EnhancementMode.NONE or mode_str == "none":
        return frame_bgr.copy()

    # Base copy
    derived = frame_bgr.copy()

    # 0. Adaptive Degradation-Aware Smart Mode with Automated Fallback
    if mode_str in ("adaptive_smart", "adaptive", "smart", str(EnhancementMode.ADAPTIVE_SMART)):
        try:
            from src.cctv.adaptive_enhancer import enhance_frame_with_audit_and_fallback
            enh, _ = enhance_frame_with_audit_and_fallback(derived, frame_index=0, allow_fallback=True)
            return enh
        except Exception:
            mode_str = "lol_v2"

    # 1. Deep Learning Enhancement Paths
    if mode_str in (
        "deep_learning", "deep", "ai", "neural", str(EnhancementMode.DEEP_LEARNING),
        "lol_v2", str(EnhancementMode.LOL_V2),
        "sdsd_temporal", str(EnhancementMode.SDSD_TEMPORAL),
        "reds_sr", str(EnhancementMode.REDS_SR)
    ):
        try:
            from src.models.cctv_enhancement_model import get_cctv_enhancer
            enhancer = get_cctv_enhancer()
            return enhancer.enhance_frame(derived, mode=mode_str, scale=1, denoise_level=75, low_light_boost=True)
        except Exception:
            # Graceful fallback to low_light deterministic filtering
            mode_str = "low_light"

    # 2. Deterministic Low Light Mode
    if mode_str == "low_light" or mode_str == EnhancementMode.LOW_LIGHT:
        # 1. Gentle gamma lift
        derived = apply_gamma_correction(derived, gamma=1.4)
        # 2. CLAHE with higher clip limit
        derived = apply_clahe(derived, clip_limit=3.0, tile_grid_size=8)
        # 3. Mild bilateral denoising to suppress sensor noise from dark scenes
        derived = cv2.bilateralFilter(derived, d=5, sigmaColor=35, sigmaSpace=35)
        # 4. Subtle unsharp mask
        derived = apply_unsharp_mask(derived, strength=0.3)

    # 3. Deterministic Basic Mode
    elif mode_str == "basic" or mode_str == EnhancementMode.BASIC:
        # 1. Standard CLAHE
        derived = apply_clahe(derived, clip_limit=2.0, tile_grid_size=8)
        # 2. Very mild Gaussian blur to control high frequency artifacts
        blurred = cv2.GaussianBlur(derived, (3, 3), 0.5)
        derived = cv2.addWeighted(derived, 0.8, blurred, 0.2, 0)
        # 3. Subtle edge contrast
        derived = apply_unsharp_mask(derived, strength=0.25)

    return derived


def enhance_video_frames(
    frames_bgr: List[np.ndarray],
    mode: EnhancementMode | str = EnhancementMode.BASIC
) -> List[np.ndarray]:
    """
    Enhance an entire sequence of CCTV frames.
    When mode='sdsd_temporal', performs dynamic multi-frame temporal alignment
    and anti-flicker filtering to ensure temporal consistency across video frames.
    """
    mode_str = str(mode).lower().replace("-", "_")
    if not frames_bgr:
        return []

    if mode_str == "none" or mode_str == EnhancementMode.NONE:
        return [f.copy() for f in frames_bgr]

    # For SDSD temporal video mode, invoke sequence processor
    if "sdsd" in mode_str:
        try:
            from src.models.cctv_enhancement_model import get_cctv_enhancer
            return get_cctv_enhancer().enhance_video_sequence(frames_bgr, mode="sdsd_temporal", temporal_smoothing=0.85)
        except Exception:
            pass

    # For other modes, process frames sequentially
    return [enhance_frame(f, mode=mode) for f in frames_bgr]
