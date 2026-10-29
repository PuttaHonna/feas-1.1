"""
Pre-Inference Forensic Quality Gate
Evaluates resolution, blur (Laplacian variance), and illumination (underexposed/overexposed).
Fails safely with explicit reasons when an image cannot support reliable model inference.
"""

from pathlib import Path
from typing import Union, List
from pydantic import BaseModel, Field
import cv2
import numpy as np
from PIL import Image

from src.common.config import FORENSIC_CONFIG


class QualityAssessment(BaseModel):
    passed: bool
    blur_score: float
    mean_luminance: float
    width: int
    height: int
    reasons: List[str] = Field(default_factory=list)
    summary_message: str = ""


def evaluate_image_quality(
    image_input: Union[Path, str, np.ndarray, Image.Image],
    min_width: int = FORENSIC_CONFIG.MIN_IMAGE_WIDTH,
    min_height: int = FORENSIC_CONFIG.MIN_IMAGE_HEIGHT,
    min_blur: float = FORENSIC_CONFIG.BLUR_LAPLACIAN_VAR_MIN,
    min_lum: float = FORENSIC_CONFIG.LUMINANCE_MIN,
    max_lum: float = FORENSIC_CONFIG.LUMINANCE_MAX,
) -> QualityAssessment:
    """
    Evaluates whether an image meets minimum diagnostic quality thresholds.
    
    Returns:
        QualityAssessment with passed=False and actionable forensic reasons if disqualified.
    """
    # Convert input to cv2 BGR/grayscale
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            return QualityAssessment(
                passed=False,
                blur_score=0.0,
                mean_luminance=0.0,
                width=0,
                height=0,
                reasons=[f"File not found: {path}"],
                summary_message="Unable to provide a reliable experimental prediction for this input.",
            )
        img_bgr = cv2.imread(str(path))
        if img_bgr is None:
            return QualityAssessment(
                passed=False,
                blur_score=0.0,
                mean_luminance=0.0,
                width=0,
                height=0,
                reasons=["Image decode failed: unreadable or corrupt file."],
                summary_message="Unable to provide a reliable experimental prediction for this input.",
            )
    elif isinstance(image_input, Image.Image):
        img_rgb = np.array(image_input.convert("RGB"))
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    # Check dimensions
    if len(img_bgr.shape) == 2:
        height, width = img_bgr.shape
        gray = img_bgr
    else:
        height, width = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    reasons: List[str] = []

    if width < min_width or height < min_height:
        reasons.append(
            f"Resolution too low ({width}x{height} < minimum {min_width}x{min_height})."
        )

    # Blur score via Laplacian variance
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if laplacian_var < min_blur:
        reasons.append(
            f"Image too blurred (Laplacian variance {laplacian_var:.2f} < threshold {min_blur:.2f})."
        )

    # Illumination check
    mean_lum = float(gray.mean())
    if mean_lum < min_lum:
        reasons.append(
            f"Image severely underexposed / pitch black (mean luminance {mean_lum:.2f} < {min_lum:.2f})."
        )
    elif mean_lum > max_lum:
        reasons.append(
            f"Image severely overexposed / blown out (mean luminance {mean_lum:.2f} > {max_lum:.2f})."
        )

    passed = len(reasons) == 0
    summary = (
        "Image quality meets minimum experimental thresholds."
        if passed
        else "Unable to provide a reliable experimental prediction for this input."
    )

    return QualityAssessment(
        passed=passed,
        blur_score=round(laplacian_var, 2),
        mean_luminance=round(mean_lum, 2),
        width=width,
        height=height,
        reasons=reasons,
        summary_message=summary,
    )
