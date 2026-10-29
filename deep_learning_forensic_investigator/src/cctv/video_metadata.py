"""
CCTV Video Metadata Extraction Module.
Extracts technical container properties, temporal metrics, and investigative parameters.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import cv2

from src.cctv.integrity import calculate_file_sha256


def _decode_fourcc(fourcc_val: float) -> str:
    """Safely decode OpenCV fourcc float value into string representation."""
    try:
        val = int(fourcc_val)
        return "".join([chr((val >> 8 * i) & 0xFF) for i in range(4)]).strip()
    except Exception:
        return "UNKNOWN"


def extract_technical_metadata(
    video_path: Path | str,
    evidence_id: str = "EV-CCTV-01",
    case_id: str = "CASE-2026-001",
    user_metadata: Optional[Dict[str, Any]] = None,
    precomputed_sha256: Optional[str] = None
) -> Dict[str, Any]:
    """Extract exhaustive technical container metadata and user context for a CCTV video.

    Args:
        video_path: Path to the target video file.
        evidence_id: Identifier for evidence tracking.
        case_id: Associated investigative case ID.
        user_metadata: Optional dictionary containing user fields (camera_id, location, etc.).
        precomputed_sha256: Optional precomputed hash to avoid re-reading.

    Returns:
        Structured dictionary containing technical container and forensic audit metadata.
    """
    path = Path(video_path)
    file_size = path.stat().st_size
    sha256_hash = precomputed_sha256 or calculate_file_sha256(path)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video stream at {path}")

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_raw = cap.get(cv2.CAP_PROP_FOURCC)
        codec_name = _decode_fourcc(fourcc_raw)
    finally:
        cap.release()

    # Guard against invalid or 0 FPS
    if fps <= 0 or fps != fps:  # check zero or NaN
        fps = 25.0  # Common default CCTV FPS fallback

    duration_seconds = round(frame_count / fps, 3) if frame_count > 0 and fps > 0 else 0.0

    meta = user_metadata or {}

    metadata_dict: Dict[str, Any] = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "original_filename": path.name,
        "file_extension": path.suffix.lower(),
        "original_file_size_bytes": file_size,
        "original_file_size_mb": round(file_size / (1024 * 1024), 3),
        "original_sha256": sha256_hash,
        "upload_timestamp": meta.get("upload_timestamp", datetime.now(timezone.utc).isoformat()),
        "processing_start_time": meta.get("processing_start_time", datetime.now(timezone.utc).isoformat()),
        "processing_finish_time": None,
        "video_width": width,
        "video_height": height,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 3),
        "frame_count": frame_count,
        "duration_seconds": duration_seconds,
        "duration_formatted": f"{int(duration_seconds // 60):02d}:{int(duration_seconds % 60):02d}",
        "codec": codec_name if codec_name else "UNKNOWN",
        "audio_presence": "Not retained / Video stream only",
        "camera_id": meta.get("camera_id", "CAM-UNSPECIFIED"),
        "camera_location": meta.get("camera_location", "UNSPECIFIED_LOCATION"),
        "event_datetime": meta.get("event_datetime", None),
        "timezone": meta.get("timezone", "UTC"),
        "working_copy_sha256": None,
        "yolo_model": meta.get("yolo_model", "yolov8n.pt"),
        "confidence_threshold": meta.get("confidence_threshold", 0.40),
        "tracking_method": meta.get("tracking_method", "bytetrack"),
        "enhancement_settings": meta.get("enhancement_settings", "none")
    }

    return metadata_dict
