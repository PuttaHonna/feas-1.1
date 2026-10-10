"""
Forensic Evidence Analysis System (FEAS) - Digital Forgery Pipeline
Integrates ELA Heatmaps, VGG16 Binary Classification, and YOLO Localization.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import cv2
import numpy as np
from PIL import Image

from src.config import TEMP_DIR
from src.models.forgery.ela import perform_ela
from src.models.forgery.vgg16_detector import get_vgg_detector
from src.models.forgery.yolo_tamper import get_yolo_tamper_detector


def run_forgery_check(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute comprehensive forensic forgery detection:
    1. Error Level Analysis (ELA) with quantitative metric extraction.
    2. VGG16 tampering probability classification.
    3. YOLO localization for spliced/inpainted bounding regions.
    4. Composite annotated visualization rendering.
    """
    out_dir = output_dir or (TEMP_DIR / "forgery_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Standardize image array in BGR format
    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        base_name = Path(image_input).stem
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input.copy()
        base_name = "image_input"
    elif isinstance(image_input, Image.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        base_name = "image_input"
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    if img_bgr is None:
        raise ValueError("Failed to decode input image.")

    # 1. Perform ELA
    ela_heatmap_bgr, ela_metrics = perform_ela(img_bgr)
    ela_filename = f"{base_name}_ela_heatmap.jpg"
    ela_path = out_dir / ela_filename
    cv2.imwrite(str(ela_path), ela_heatmap_bgr)

    # 2. VGG16 Classification
    vgg_detector = get_vgg_detector()
    vgg_score = vgg_detector.predict(img_bgr)

    # 3. YOLO Tamper Localization
    yolo_detector = get_yolo_tamper_detector()
    bboxes = yolo_detector.detect(img_bgr)

    # Composite tamper confidence: weighted ensemble of VGG16, ELA ratio, and localized boxes
    box_conf = max([b["confidence"] for b in bboxes], default=0.0)
    composite_score = float(0.40 * vgg_score + 0.35 * min(1.0, ela_metrics["tamper_ratio"] * 4.0) + 0.25 * box_conf)
    
    # If explicit tamper bounding boxes were located, ensure score reflects evidence
    if bboxes and composite_score < 0.65:
        composite_score = max(composite_score, box_conf * 0.85)

    composite_score = round(min(0.99, max(0.01, composite_score)), 4)
    is_tampered = bool(composite_score >= 0.50 or len(bboxes) > 0)

    # 4. Render Composite Annotated Visualization
    annotated_bgr = img_bgr.copy()
    for box in bboxes:
        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
        label = box["label"]
        conf = box["confidence"]
        
        # Red bounding box for tamper regions
        cv2.rectangle(annotated_bgr, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        # Label badge
        text = f"{label.upper()} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated_bgr, (x1, max(0, y1 - 20)), (x1 + tw + 6, max(0, y1)), (0, 0, 255), -1)
        cv2.putText(annotated_bgr, text, (x1 + 3, max(14, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    annotated_filename = f"{base_name}_annotated.jpg"
    annotated_path = out_dir / annotated_filename
    cv2.imwrite(str(annotated_path), annotated_bgr)

    return {
        "tamper_score": composite_score,
        "is_tampered": is_tampered,
        "bboxes": bboxes,
        "ela_metrics": ela_metrics,
        "annotated_image_path": str(annotated_path),
        "ela_image_path": str(ela_path)
    }
