"""
CCTV Video Analysis Module for Deep Learning Forensic Investigator.
Educational & Research Prototype for derived CCTV analysis, object tracking, and event extraction.
"""

from src.cctv.integrity import calculate_file_sha256, verify_sha256
from src.cctv.video_validator import validate_cctv_video
from src.cctv.video_metadata import extract_technical_metadata
from src.cctv.working_copy import create_verified_working_copy
from src.cctv.frame_extractor import extract_cctv_frames
from src.cctv.enhancement import enhance_frame, EnhancementMode
from src.cctv.detector import CCTVDetector, ALLOWED_CLASSES
from src.cctv.tracker import CCTVTracker
from src.cctv.event_extractor import CCTVEventExtractor
from src.cctv.annotated_video import generate_annotated_video
from src.cctv.audit_logger import CCTVAuditLogger
from src.cctv.export_results import export_cctv_artifacts

__all__ = [
    "calculate_file_sha256",
    "verify_sha256",
    "validate_cctv_video",
    "extract_technical_metadata",
    "create_verified_working_copy",
    "extract_cctv_frames",
    "enhance_frame",
    "EnhancementMode",
    "CCTVDetector",
    "ALLOWED_CLASSES",
    "CCTVTracker",
    "CCTVEventExtractor",
    "generate_annotated_video",
    "CCTVAuditLogger",
    "export_cctv_artifacts",
]
