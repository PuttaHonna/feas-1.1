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

# Strict list of permitted COCO object classes
ALLOWED_CLASSES: Set[str] = {
    "person",
    "car",
    "motorcycle",
    "bicycle",
    "bus",
    "truck",
    "backpack",
    "handbag",
    "suitcase",
    "cell phone"
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


class CCTVDetector:
    """Singleton-style wrapper for YOLOv8 model inference."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.40,
        device: Optional[str] = None
    ):
        """Initialize the YOLOv8 detector once.

        Args:
            model_name: Model weights filename or path (default 'yolov8n.pt').
            confidence_threshold: Minimum detection confidence score (0.0 - 1.0).
            device: 'cuda', 'cpu', or None for automatic device detection.
        """
        self.confidence_threshold = confidence_threshold

        # Automatic device assignment
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load weights once
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
        evidence_id: str = "EV-01"
    ) -> List[Detection]:
        """Run object detection on an enhanced frame.

        Args:
            frame_bgr: Derived working frame image.
            frame_number: Sequential index of frame in video.
            timestamp_seconds: Calculated frame timestamp in seconds.
            timestamp_hms: Formatted HH:MM:SS.mmm string.
            camera_id: Camera identifier for chain of custody.
            evidence_id: Evidence tracking identifier.

        Returns:
            List of Detection objects restricted to permitted classes.
        """
        results = self.model(
            frame_bgr,
            conf=self.confidence_threshold,
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

            det = Detection(
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
                timestamp_hms=timestamp_hms,
                class_name=class_name,
                class_id=cls_id,
                confidence=round(conf, 4),
                x1=round(x1, 2),
                y1=round(y1, 2),
                x2=round(y2, 2),
                y2=round(y2, 2),
                width=round(w, 2),
                height=round(h, 2),
                centroid_x=round(cx, 2),
                centroid_y=round(cy, 2),
                camera_id=camera_id,
                evidence_id=evidence_id
            )
            detections.append(det)

        return detections
