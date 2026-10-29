"""
Forensic Object Detector (COCO Objects Only)
Restricted strictly to standard COCO objects for contextual surveillance analysis:
- person, bicycle, car, motorcycle, bus, truck, backpack, handbag, suitcase, cell phone.
Strictly prohibits face recognition, identity inference, weapons, crime detection, or intent prediction.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from ultralytics import YOLO

# Permitted COCO classes and their canonical IDs
ALLOWED_COCO_CLASSES: Dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    24: "backpack",
    26: "handbag",
    28: "suitcase",
    67: "cell phone",
}


class ForensicObjectDetector:
    """
    Standard COCO object detector using pretrained YOLO.
    Enforces class whitelisting and records exact confidence scores and coordinates.
    """

    def __init__(
        self,
        model_weights: Optional[str] = None,
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        # Look for local weights first
        default_local_weights = [
            Path("yolov8n.pt"),
            Path("deep_learning_forensic_investigator/yolov8n.pt"),
            Path("FEAS/yolov8n.pt"),
        ]

        resolved_weights = "yolov8n.pt"
        if model_weights and Path(model_weights).exists():
            resolved_weights = str(model_weights)
        else:
            for p in default_local_weights:
                if p.exists():
                    resolved_weights = str(p)
                    break

        self.model_path = str(resolved_weights)
        self.model = YOLO(self.model_path)

    def detect_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        timestamp_sec: float,
    ) -> List[Dict[str, Any]]:
        """
        Runs inference on a single frame and filters for allowed COCO classes.
        """
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=list(ALLOWED_COCO_CLASSES.keys()),
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None:
            return detections

        for box in boxes:
            cls_id = int(box.cls.item())
            if cls_id not in ALLOWED_COCO_CLASSES:
                continue

            conf = float(box.conf.item())
            xyxy = [round(float(coord), 2) for coord in box.xyxy[0].tolist()]

            detections.append({
                "frame_idx": frame_idx,
                "timestamp_sec": round(timestamp_sec, 3),
                "class_id": cls_id,
                "class_name": ALLOWED_COCO_CLASSES[cls_id],
                "confidence": round(conf, 4),
                "bbox": xyxy,  # [x1, y1, x2, y2]
            })

        return detections
