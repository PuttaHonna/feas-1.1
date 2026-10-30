"""
CCTV Object Detection Module.
Uses a single loaded instance of Ultralytics YOLOv8 restricted to 10 COCO classes.
Strictly avoids biometric identity inference, weapons, crime prediction, or intent classification.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
import numpy as np
import torch
from ultralytics import YOLO

# Strict list of permitted COCO object classes (including urban roadway animals)
ALLOWED_CLASSES: Set[str] = {
    # Pedestrians & Personal Items
    "person",
    "backpack",
    "handbag",
    "suitcase",
    "cell phone",
    # Vehicles & Transportation
    "car",
    "motorcycle",
    "bicycle",
    "bus",
    "truck",
    "train",
    "auto",
    "auto_rickshaw",
    # Roadway Animals & Livestock
    "dog",
    "cat",
    "cow",
    "horse",
    "sheep",
    "bird",
    "elephant",
    "bear",
    "zebra",
    "giraffe"
}


@dataclass
class Detection:
    """Represents a validated object detection in a specific frame."""
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    class_name: str
    class_id: int
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float
    centroid_x: float
    centroid_y: float
    camera_id: str = "CAM-01"
    evidence_id: str = "EV-01"
    keyframe_path: Optional[str] = None
    track_id: Optional[str] = None
    track_number: Optional[int] = None


class CCTVDetector:
    """Singleton-style wrapper for YOLOv8 model inference."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.25,
        device: Optional[str] = None
    ):
        """Initialize the YOLOv8 detector once.

        Args:
            model_name: Model weights filename or path (default 'yolov8n.pt').
            confidence_threshold: Minimum detection confidence score (0.0 - 1.0, default 0.25).
            device: 'cuda', 'cpu', or None for automatic device detection.
        """
        self.confidence_threshold = confidence_threshold

        # Automatic device assignment
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        base_dir = Path(__file__).resolve().parent.parent.parent
        if model_name in ("default", "yolov8n.pt"):
            model_name = "yolov8n.pt"

        # Load weights once
        model_path = Path(model_name)
        if not model_path.exists():
            # Check relative to current file or repo root
            feas_cand = base_dir / model_name
            dl_cand = base_dir.parent / "deep_learning_forensic_investigator" / model_name
            if feas_cand.exists():
                model_name = str(feas_cand)
            elif dl_cand.exists():
                model_name = str(dl_cand)

        self.model = YOLO(model_name)
        self.model_name = model_name

        # Cache COCO class name mapping
        self.names = self.model.names if hasattr(self.model, "names") else {}

    def detect_frame(
        self,
        frame_bgr: np.ndarray,
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str,
        camera_id: str = "CAM-01",
        evidence_id: str = "EV-01",
        confidence: Optional[float] = None,
        imgsz: Optional[int] = None
    ) -> List[Detection]:
        """Run object detection on an enhanced frame.

        Args:
            frame_bgr: Derived working frame image.
            frame_number: Sequential index of frame in video.
            timestamp_seconds: Calculated frame timestamp in seconds.
            timestamp_hms: Formatted HH:MM:SS.mmm string.
            camera_id: Camera identifier for chain of custody.
            evidence_id: Evidence tracking identifier.
            confidence: Optional override for detection confidence threshold.
            imgsz: Optional override for inference resolution.

        Returns:
            List of Detection objects restricted to permitted classes.
        """
        thresh = confidence if confidence is not None else self.confidence_threshold
        target_imgsz = imgsz or 640

        # Run inference with sensitive floor so subtle quadrupeds/animals are detected
        inference_thresh = min(thresh, 0.14)

        # Cap inference size on CPU to conserve RAM and run 3x faster
        if self.device == "cpu":
            target_imgsz = min(target_imgsz, 480)

        with torch.inference_mode():
            results = self.model(
                frame_bgr,
                conf=inference_thresh,
                imgsz=target_imgsz,
                device=self.device,
                verbose=False
            )

        detections: List[Detection] = []
        if not results or len(results) == 0:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        frame_h, frame_w = frame_bgr.shape[:2]

        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = self.names.get(cls_id, "unknown").lower()

            # Filter out non-allowed classes
            if class_name not in ALLOWED_CLASSES:
                continue

            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]

            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)
            cx = x1 + (w / 2.0)
            cy = y1 + (h / 2.0)
            ar = w / max(1.0, h)

            # Auto-Rickshaw / Three-Wheeler Reclassification:
            # Standard COCO YOLO models lack an auto-rickshaw class and commonly misclassify
            # Indian/Asian three-wheelers (Bajaj / TVS / Piaggio tuk-tuks) as 'truck' or 'car'
            # due to their upright boxy canvas/tailgate.
            if class_name == "truck" and 0.55 <= ar <= 1.08 and w < frame_w * 0.45 and h < frame_h * 0.65:
                class_name = "auto"
            elif class_name == "car" and 0.60 <= ar <= 0.96 and w < frame_w * 0.40 and h < frame_h * 0.60:
                class_name = "auto"

            # Quadruped Animal (Dog/Cat/Livestock) vs Upright Human Disambiguation:
            # Pre-trained COCO YOLO models lack overhead surveillance quadruped training and
            # frequently misclassify street animals (dogs, cats) walking on roadways as 'person'.
            # Biometric distinctions in elevated CCTV:
            # - Upright walking pedestrians are strictly vertical: aspect ratio (w/h) is typically 0.18 - 0.52.
            # - Quadruped animals on all fours have a horizontal spine: aspect ratio (w/h) >= 0.65 (often 0.80 - 1.40).
            # - Quadruped animals on the roadway have compact vertical height (h < frame_h * 0.28 or h < 125 px).
            if class_name == "person":
                is_quadruped = (0.65 <= ar <= 1.85 and h < frame_h * 0.28 and w < frame_w * 0.35)
                is_compact_animal = (ar >= 0.68 and h < 125 and w < 135)
                if is_quadruped or is_compact_animal:
                    class_name = "dog"

            # Effective confidence thresholding: allow animals adaptive sensitivity
            effective_thresh = max(0.14, thresh * 0.70) if class_name in ("dog", "cat", "cow", "horse", "sheep") else thresh
            if conf < effective_thresh:
                continue

            det = Detection(
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
                timestamp_hms=timestamp_hms,
                class_name=class_name,
                class_id=cls_id,
                confidence=round(conf, 4),
                x1=round(x1, 2),
                y1=round(y1, 2),
                x2=round(x2, 2),
                y2=round(y2, 2),
                width=round(w, 2),
                height=round(h, 2),
                centroid_x=round(cx, 2),
                centroid_y=round(cy, 2),
                camera_id=camera_id,
                evidence_id=evidence_id
            )
            detections.append(det)

        # Multi-class and Cross-class NMS: eliminate duplicate and conflicting overlapping boxes
        if len(detections) > 1:
            veh_classes = {"car", "truck", "bus", "motorcycle", "auto", "auto_rickshaw"}
            animal_classes = {"dog", "cat", "cow", "horse", "sheep", "bird", "elephant"}
            filtered: List[Detection] = []
            for d in sorted(detections, key=lambda x: x.confidence, reverse=True):
                keep = True
                for k in filtered:
                    xx1 = max(d.x1, k.x1)
                    yy1 = max(d.y1, k.y1)
                    xx2 = min(d.x2, k.x2)
                    yy2 = min(d.y2, k.y2)
                    inter_w = max(0.0, xx2 - xx1)
                    inter_h = max(0.0, yy2 - yy1)
                    inter_area = inter_w * inter_h
                    area_d = max(1.0, d.width * d.height)
                    area_k = max(1.0, k.width * k.height)
                    iou = inter_area / (area_d + area_k - inter_area)

                    if iou > 0.40:
                        # 1. Duplicate boxes of identical class
                        if d.class_name == k.class_name:
                            keep = False
                            break
                        # 2. Conflicting vehicle classes (e.g. truck vs car vs auto)
                        if d.class_name in veh_classes and k.class_name in veh_classes:
                            keep = False
                            break
                        # 3. Person vs Quadruped Animal Conflict:
                        if {d.class_name, k.class_name} == {"person", "dog"}:
                            d_ar = d.width / max(1.0, d.height)
                            if d_ar >= 0.65 and d.class_name == "dog":
                                # d is dog with animal aspect ratio; suppress false person box k
                                filtered.remove(k)
                                keep = True
                                break
                            else:
                                keep = False
                                break
                if keep:
                    filtered.append(d)
            detections = sorted(filtered, key=lambda d: (d.y1, d.x1))

        return detections
