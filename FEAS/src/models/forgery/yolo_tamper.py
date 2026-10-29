"""
Forensic Evidence Analysis System (FEAS) - Digital Manipulation Region Localizer
Detects and localizes spliced, inpainted, copy-move, and generative AI regions
using multi-scale gradient anomaly, patch noise variance, and high-frequency boundary analysis.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from src.config import DEVICE, SEED


class TamperBoundingBox:
    def __init__(self, x1: int, y1: int, x2: int, y2: int, label: str, confidence: float):
        self.x1 = int(x1)
        self.y1 = int(y1)
        self.x2 = int(x2)
        self.y2 = int(y2)
        self.label = label
        self.confidence = round(float(confidence), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.x2 - self.x1,
            "height": self.y2 - self.y1,
            "label": self.label,
            "confidence": self.confidence,
        }


class YOLOTamperDetector:
    """Forensic localizer for identifying digital image manipulation boundaries."""

    def __init__(self):
        self.device = DEVICE
        self.classes = ["splicing", "inpainting", "copy-move", "ai_synthesis", "compression_anomaly", "deep_learning_anomaly"]

    def detect(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        conf_threshold: float = 0.40,
        ela_guide: Optional[np.ndarray] = None,
        gradcam_guide: Optional[np.ndarray] = None,
        sensitivity: int = 75,
    ) -> List[Dict[str, Any]]:
        """
        Scan image and identify anomalous manipulation regions.
        Combines deep learning Grad-CAM class activation, spatial frequency analysis,
        Laplacian boundary variance, patch-level noise residuals, and adaptive ELA guidance.
        """
        if isinstance(image_input, (str, Path)):
            img_bgr = cv2.imread(str(image_input))
        elif isinstance(image_input, np.ndarray):
            img_bgr = image_input.copy()
        elif isinstance(image_input, Image.Image):
            img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        if img_bgr is None:
            return []

        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        sens = max(30, min(95, sensitivity))

        # Dynamic sensitivity scaling: higher sensitivity lowers threshold to catch subtle forgeries
        effective_conf = max(0.20, conf_threshold - (sens - 50) * 0.004)

        # 1. High-pass Laplacian edge gradient filter
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = cv2.blur(np.abs(lap), (17, 17))
        mean_lap = float(np.mean(lap_var))
        std_lap = float(np.std(lap_var))
        lap_mult = max(1.1, 2.1 - (sens / 100.0) * 1.0)
        lap_thresh = mean_lap + lap_mult * std_lap
        lap_mask = (lap_var > lap_thresh).astype(np.uint8) * 255

        # 2. Patch-level noise residual anomaly
        patch_size = 24
        rows, cols = h // patch_size, w // patch_size
        noise_mask = np.zeros((h, w), dtype=np.uint8)

        if rows > 0 and cols > 0:
            for r in range(rows):
                for c in range(cols):
                    patch = gray[r * patch_size : (r + 1) * patch_size, c * patch_size : (c + 1) * patch_size]
                    denoised = cv2.medianBlur(patch, 3)
                    diff = np.abs(patch.astype(np.float32) - denoised.astype(np.float32))
                    noise_limit = max(4.5, 8.5 - (sens / 100.0) * 4.0)
                    if np.mean(diff) > noise_limit:
                        noise_mask[r * patch_size : (r + 1) * patch_size, c * patch_size : (c + 1) * patch_size] = 255

        # 3. Adaptive ELA guidance
        ela_mask = np.zeros((h, w), dtype=np.uint8)
        if ela_guide is not None:
            ela_gray = cv2.cvtColor(ela_guide, cv2.COLOR_BGR2GRAY) if len(ela_guide.shape) == 3 else ela_guide
            ela_m = float(np.mean(ela_gray))
            ela_s = float(np.std(ela_gray))
            ela_cutoff = max(20.0, ela_m + 1.15 * ela_s)
            ela_mask = (ela_gray > ela_cutoff).astype(np.uint8) * 255

        # 4. Grad-CAM deep learning activation guidance
        cam_mask = np.zeros((h, w), dtype=np.uint8)
        has_cam = gradcam_guide is not None and np.max(gradcam_guide) > 0.25
        if has_cam:
            cam_cutoff = max(0.28, 0.68 - (sens / 100.0) * 0.40)
            cam_mask = (gradcam_guide > cam_cutoff).astype(np.uint8) * 255

        # Multi-modal fusion
        combined = cv2.bitwise_or(lap_mask, cv2.bitwise_or(noise_mask, cv2.bitwise_or(ela_mask, cam_mask)))

        # Morphological grouping
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Anomaly window: 0.15% to 80% of canvas
        min_area = (h * w) * 0.0015
        max_area = (h * w) * 0.80

        boxes: List[Dict[str, Any]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(w, x + bw), min(h, y + bh)

                # Regional anomaly confidence
                region_lap = float(np.mean(lap_var[y1:y2, x1:x2]))
                lap_score = (region_lap - mean_lap) / (std_lap + 1e-5)
                base_conf = min(0.96, max(0.40, float(lap_score / 3.2)))

                # Boost if Grad-CAM or ELA confirms
                if has_cam:
                    region_cam = float(np.mean(gradcam_guide[y1:y2, x1:x2]))
                    base_conf = max(base_conf, region_cam * 0.95)

                if base_conf >= effective_conf:
                    # Determine label
                    if has_cam and float(np.mean(gradcam_guide[y1:y2, x1:x2])) > 0.50:
                        label = "deep_learning_anomaly"
                    elif float(np.mean(ela_mask[y1:y2, x1:x2])) > 50:
                        label = "compression_anomaly"
                    elif area > (h * w * 0.05):
                        label = "splicing"
                    elif np.mean(noise_mask[y1:y2, x1:x2]) > 80:
                        label = "ai_inpaint"
                    else:
                        label = "copy-move"

                    box = TamperBoundingBox(x1, y1, x2, y2, label, base_conf)
                    boxes.append(box.to_dict())

        # Fallback Peak Localization:
        # If Grad-CAM or ELA strongly indicates tampering but no contour met the filters,
        # extract the highest activation cluster so the tampering region is NEVER missed!
        if len(boxes) == 0 and has_cam:
            peak_mask = (gradcam_guide > 0.40).astype(np.uint8) * 255
            p_contours, _ = cv2.findContours(peak_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for pc in p_contours:
                p_area = cv2.contourArea(pc)
                if p_area >= min_area:
                    px, py, pbw, pbh = cv2.boundingRect(pc)
                    p_conf = round(float(np.max(gradcam_guide[py : py + pbh, px : px + pbw])), 4)
                    boxes.append(TamperBoundingBox(px, py, px + pbw, py + pbh, "deep_learning_anomaly", p_conf).to_dict())

        # If still empty but ELA has high variance, extract highest ELA cluster
        if len(boxes) == 0 and ela_guide is not None and np.max(ela_mask) > 0:
            e_contours, _ = cv2.findContours(ela_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for ec in e_contours:
                if cv2.contourArea(ec) >= min_area:
                    ex, ey, ebw, ebh = cv2.boundingRect(ec)
                    boxes.append(TamperBoundingBox(ex, ey, ex + ebw, ey + ebh, "compression_anomaly", 0.76).to_dict())

        # Sort by confidence descending, cap at 8 most prominent regions
        boxes.sort(key=lambda b: b["confidence"], reverse=True)
        return boxes[:8]


# Global singleton
_yolo_detector = None


def get_yolo_tamper_detector() -> YOLOTamperDetector:
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLOTamperDetector()
    return _yolo_detector
