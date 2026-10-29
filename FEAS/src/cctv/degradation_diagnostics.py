"""
CCTV Surveillance Degradation Diagnostics & Forensic Quality Gate.
==================================================================
Identifies the actual degradation affecting surveillance footage:
1. Illumination / Underexposure (poor lux, clipped shadows)
2. Motion / Optical Blur (Laplacian variance, edge dispersion)
3. Compression Artifacts (H.264/DVR macroblock blockiness, DCT ringing)
4. Low Resolution (sub-standard pixel density, scale factor needed)

Enables degradation-targeted enhancement rather than blind filter stacking.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


@dataclass
class DegradationReport:
    """Quantitative breakdown of CCTV image/video degradations."""
    primary_degradation: str  # 'darkness' | 'blur' | 'compression' | 'low_res' | 'none'
    mean_luminance: float     # 0-255: < 60 = underexposed / low-lux
    shadow_ratio: float       # % of pixels with Y < 30
    blur_score: float         # Laplacian variance: < 100 = blurry
    blockiness_score: float   # 8x8 DCT grid boundary jump: > 0.15 = heavy compression
    width: int
    height: int
    megapixels: float
    recommended_strategy: str
    is_excessive_processing_risk: bool
    summary_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, any]:
        return {
            "primary_degradation": self.primary_degradation,
            "mean_luminance": round(self.mean_luminance, 2),
            "shadow_ratio_pct": round(self.shadow_ratio * 100.0, 1),
            "blur_laplacian_var": round(self.blur_score, 2),
            "compression_blockiness": round(self.blockiness_score, 4),
            "resolution": f"{self.width}x{self.height}",
            "megapixels": round(self.megapixels, 3),
            "recommended_strategy": self.recommended_strategy,
            "is_excessive_processing_risk": self.is_excessive_processing_risk,
            "summary_notes": self.summary_notes,
        }


def calculate_blockiness_metric(gray_img: np.ndarray) -> float:
    """
    Computes H.264 / JPEG 8x8 macroblock boundary discontinuity.
    Compares difference across 8-pixel block boundaries vs interior pixels.
    Higher value indicates severe DVR compression artifacts.
    """
    h, w = gray_img.shape
    if h < 16 or w < 16:
        return 0.0

    # Horizontal boundary difference across 8th columns
    diff_h = np.abs(gray_img[:, 7:-1:8].astype(np.float32) - gray_img[:, 8::8].astype(np.float32))
    # Interior difference
    diff_int_h = np.abs(gray_img[:, 6:-2:8].astype(np.float32) - gray_img[:, 7:-1:8].astype(np.float32))

    mean_boundary = float(np.mean(diff_h)) if diff_h.size > 0 else 0.0
    mean_interior = float(np.mean(diff_int_h)) if diff_int_h.size > 0 else 1.0

    ratio = (mean_boundary - mean_interior) / max(1.0, mean_interior)
    return float(max(0.0, ratio))


def diagnose_frame_degradation(frame_bgr: np.ndarray) -> DegradationReport:
    """
    Inspects a frame to isolate the dominant degradation type.
    Prevents blind stacking of filters that damage evidence.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return DegradationReport(
            primary_degradation="corrupt",
            mean_luminance=0.0,
            shadow_ratio=1.0,
            blur_score=0.0,
            blockiness_score=0.0,
            width=0,
            height=0,
            megapixels=0.0,
            recommended_strategy="reject",
            is_excessive_processing_risk=False,
            summary_notes=["Zero-byte or corrupted frame buffer."]
        )

    h, w = frame_bgr.shape[:2]
    mp = (h * w) / 1_000_000.0

    # 1. Luminance & Shadow inspection (LAB color space)
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    mean_lum = float(np.mean(l_channel))
    shadow_ratio = float(np.count_nonzero(l_channel < 40)) / float(l_channel.size)

    # 2. Blur / Frequency inspection (Laplacian variance on grayscale)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(lap.var())

    # 3. Compression blockiness
    blockiness = calculate_blockiness_metric(gray)

    # Evaluate conditions
    is_dark = mean_lum < 75.0 or shadow_ratio > 0.35
    is_blurry = blur_score < 110.0
    is_compressed = blockiness > 0.12
    is_low_res = (w < 480 or h < 360)

    notes = []
    # Rank dominant degradation
    if is_dark:
        primary = "darkness"
        strategy = "lol_v2_illumination"
        notes.append(f"Low-lux environment detected (Mean Lum: {mean_lum:.1f}/255, Shadows: {shadow_ratio*100:.1f}%).")
        notes.append("Targeted Illumination Expansion recommended (avoid excessive sharpening).")
    elif is_blurry:
        primary = "motion_blur"
        strategy = "edge_restoration"
        notes.append(f"Optical or vehicle motion blur detected (Laplacian Var: {blur_score:.1f}).")
        notes.append("Edge deconvolution recommended (do not over-amplify noise with high-pass gain).")
    elif is_compressed:
        primary = "compression"
        strategy = "deblocking_bilateral"
        notes.append(f"DVR compression macroblock noise detected (Blockiness: {blockiness:.3f}).")
        notes.append("Selective bilateral deblocking recommended (do NOT sharpen block boundaries).")
    elif is_low_res:
        primary = "low_resolution"
        strategy = "guided_super_res"
        notes.append(f"Sub-D1 CCTV resolution ({w}x{h}). High-resolution inference recommended with forensic notice.")
    else:
        primary = "none"
        strategy = "bypass_raw"
        notes.append("Frame quality is adequate for direct YOLOv8 detection. No invasive enhancement needed.")

    # Check excessive processing risk
    excessive_risk = is_dark and is_blurry and is_compressed
    if excessive_risk:
        notes.append("HIGH RISK: Multiple compound degradations. Aggressive stacked filters will introduce hallucinations.")

    return DegradationReport(
        primary_degradation=primary,
        mean_luminance=mean_lum,
        shadow_ratio=shadow_ratio,
        blur_score=blur_score,
        blockiness_score=blockiness,
        width=w,
        height=h,
        megapixels=mp,
        recommended_strategy=strategy,
        is_excessive_processing_risk=excessive_risk,
        summary_notes=notes
    )
