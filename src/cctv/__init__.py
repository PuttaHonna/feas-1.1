"""
Forensic CCTV Video Module
Deterministic enhancement, restricted COCO object detection,
deterministic tracking, and objective surveillance event extraction.
"""

from src.cctv.enhancement import enhance_frame
from src.cctv.detector import ForensicObjectDetector, ALLOWED_COCO_CLASSES
from src.cctv.tracker import ForensicTracker
from src.cctv.events import ObjectiveEventExtractor
from src.cctv.pipeline import run_cctv_pipeline

__all__ = [
    "enhance_frame",
    "ForensicObjectDetector",
    "ALLOWED_COCO_CLASSES",
    "ForensicTracker",
    "ObjectiveEventExtractor",
    "run_cctv_pipeline",
]
