"""
Deterministic OpenCV CCTV Video Frame Enhancement
Applies strictly reproducible, non-generative enhancements:
- Gamma correction
- CLAHE (Contrast Limited Adaptive Histogram Equalization) on luminance
- Mild bilateral denoising
- Mild unsharp masking
- Watermarking/labeling with mandatory digital-forensics banner
"""

from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np

from src.common.config import FORENSIC_CONFIG


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """Apply deterministic gamma correction using a 256-entry lookup table."""
    if abs(gamma - 1.0) < 1e-3:
        return image
    inv_gamma = 1.0 / max(gamma, 1e-4)
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """Apply CLAHE to the L (luminance) channel in LAB color space to preserve color balance."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_enhanced = clahe.apply(l)
    lab_enhanced = cv2.merge((l_enhanced, a, b))
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)


def apply_mild_denoise(image: np.ndarray, d: int = 5, sigma_color: float = 25.0, sigma_space: float = 25.0) -> np.ndarray:
    """Apply deterministic edge-preserving bilateral filtering to suppress sensor noise."""
    return cv2.bilateralFilter(image, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)


def apply_unsharp_mask(image: np.ndarray, sigma: float = 1.0, strength: float = 0.5) -> np.ndarray:
    """Apply deterministic unsharp masking to enhance edge clarity."""
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def add_forensic_banner(image: np.ndarray, label_text: Optional[str] = None) -> np.ndarray:
    """
    Overlays mandatory banner stating that the frame is a derived working image
    and that original footage remains unchanged.
    """
    text = label_text or FORENSIC_CONFIG.DERIVED_FRAME_LABEL
    h, w = image.shape[:2]
    banner_height = max(24, int(h * 0.05))
    banner = np.zeros((banner_height, w, 3), dtype=np.uint8)
    # Dark charcoal background
    banner[:] = (30, 30, 30)

    font_scale = max(0.3, min(0.55, w / 1100.0))
    cv2.putText(
        banner,
        text,
        (10, int(banner_height * 0.68)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    return np.vstack([image, banner])


def enhance_frame(
    frame: np.ndarray,
    gamma: float = 1.0,
    enable_clahe: bool = True,
    enable_denoise: bool = True,
    enable_sharpen: bool = True,
    add_banner: bool = True,
    target_size: Optional[Tuple[int, int]] = None,
) -> np.ndarray:
    """
    Full deterministic frame enhancement pipeline.
    Zero generative AI or hallucinated pixels.
    """
    out = frame.copy()

    # 1. Resize if requested (width, height)
    if target_size:
        out = cv2.resize(out, target_size, interpolation=cv2.INTER_AREA)

    # 2. Gamma correction
    if abs(gamma - 1.0) > 1e-3:
        out = apply_gamma_correction(out, gamma=gamma)

    # 3. CLAHE contrast enhancement
    if enable_clahe:
        out = apply_clahe(out)

    # 4. Bilateral edge-preserving denoise
    if enable_denoise:
        out = apply_mild_denoise(out)

    # 5. Mild unsharp sharpening
    if enable_sharpen:
        out = apply_unsharp_mask(out)

    # 6. Watermark banner
    if add_banner:
        out = add_forensic_banner(out)

    return out
