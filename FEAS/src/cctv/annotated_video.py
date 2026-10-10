"""
CCTV Annotated Video Generator.
Overlays bounding boxes, stable track identifiers, vehicle forensic attributes,
crash warnings, suspicious behavior alerts, timestamps,
and prominent derived-evidence advisory watermarks.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import cv2
import numpy as np

from src.cctv.detector import Detection

DERIVED_WATERMARK: str = "DERIVED ANALYSIS COPY — HUMAN REVIEW REQUIRED"

# Distinct color palette per class for visual clarity
CLASS_COLORS = {
    "person": (0, 240, 255),      # Bright Cyan
    "car": (80, 220, 100),        # Green
    "motorcycle": (255, 180, 0),  # Amber
    "bicycle": (200, 255, 100),   # Lime
    "bus": (255, 120, 50),        # Orange
    "truck": (255, 80, 80),       # Coral
    "backpack": (220, 100, 255),  # Violet
    "handbag": (255, 100, 200),   # Pink
    "suitcase": (150, 150, 255),  # Lavender
    "cell phone": (255, 255, 100) # Yellow
}

COLOR_CRASH = (0, 0, 255)        # Pure Red for Crash / Collision
COLOR_SUSPICIOUS = (0, 140, 255)  # Orange for Suspicious / Kinematic Anomaly


def draw_detection_overlay(
    frame_bgr: np.ndarray,
    detections: List[Detection],
    timestamp_hms: str,
    roi_polygon: Optional[List[Tuple[float, float]]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
    crashed_track_ids: Optional[Set[str]] = None,
    suspicious_track_ids: Optional[Dict[str, List[str]]] = None
) -> np.ndarray:
    """Draw bounding boxes, track labels, vehicle metadata, and advisory watermarks on a frame."""
    canvas = frame_bgr.copy()
    h, w = canvas.shape[:2]

    crashed_set = crashed_track_ids or set()
    suspicious_map = suspicious_track_ids or {}
    profiles = vehicle_profiles or {}

    # 1. Draw ROI polygon if specified
    if roi_polygon and len(roi_polygon) >= 3:
        pts = np.array(roi_polygon, np.int32).reshape((-1, 1, 2))
        cv2.polylines(canvas, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
        # Semi-transparent overlay on ROI
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], color=(0, 255, 255))
        cv2.addWeighted(overlay, 0.15, canvas, 0.85, 0, canvas)

    # 2. Draw detections & tracks
    for det in detections:
        tid = det.track_id or "unassigned"
        base_color = CLASS_COLORS.get(det.class_name, (0, 240, 255))

        is_crashed = tid in crashed_set
        susp_flags = suspicious_map.get(tid, [])
        is_suspicious = len(susp_flags) > 0

        # Prioritize alert color
        if is_crashed:
            box_color = COLOR_CRASH
            thickness = 3
        elif is_suspicious:
            box_color = COLOR_SUSPICIOUS
            thickness = 2
        else:
            box_color = base_color
            thickness = 2

        x1, y1 = int(det.x1), int(det.y1)
        x2, y2 = int(det.x2), int(det.y2)

        # Bounding box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), box_color, thickness)

        # Primary label tag
        if is_crashed:
            primary_label = f"💥 CRASH | {tid}"
        elif is_suspicious:
            primary_label = f"⚠️ {susp_flags[0]} | {tid}"
        else:
            primary_label = f"{tid} | {det.confidence:.2f}"

        (tw, th), baseline = cv2.getTextSize(primary_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

        # Background badge for text
        badge_y1 = max(0, y1 - th - 6)
        badge_y2 = y1
        cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw + 6, badge_y2), (16, 24, 38), -1)
        cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw + 6, badge_y2), box_color, 1)

        cv2.putText(
            canvas,
            primary_label,
            (x1 + 3, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # Vehicle Attribute subtitle under the bounding box if available
        v_prof = profiles.get(tid)
        if v_prof is not None:
            # Build vehicle attribute tag
            color_str = getattr(v_prof, "dominant_color", None) or v_prof.get("dominant_color", "")
            body_str = getattr(v_prof, "estimated_body_type", None) or v_prof.get("estimated_body_type", "")
            plate_str = getattr(v_prof, "license_plate_number", None) or v_prof.get("license_plate_number", "")

            plate_display = plate_str if plate_str else "No Plate Rec."
            attr_text = f"Plate: {plate_display} | {color_str} {body_str}"

            (aw, ah), _ = cv2.getTextSize(attr_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            b_bot_y1 = y2
            b_bot_y2 = min(h, y2 + ah + 6)
            cv2.rectangle(canvas, (x1, b_bot_y1), (x1 + aw + 6, b_bot_y2), (16, 24, 38), -1)
            cv2.rectangle(canvas, (x1, b_bot_y1), (x1 + aw + 6, b_bot_y2), box_color, 1)
            cv2.putText(
                canvas,
                attr_text,
                (x1 + 3, b_bot_y2 - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (230, 240, 255),
                1,
                cv2.LINE_AA
            )

    # 3. Top-left mandatory banner: "DERIVED ANALYSIS COPY — HUMAN REVIEW REQUIRED"
    banner_h = 32
    cv2.rectangle(canvas, (0, 0), (w, banner_h), (8, 14, 24), -1)
    cv2.putText(
        canvas,
        DERIVED_WATERMARK,
        (12, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 240, 255),
        2,
        cv2.LINE_AA
    )

    # 4. Top-right timestamp indicator
    ts_text = f"TIMESTAMP: {timestamp_hms}"
    (tw, th), _ = cv2.getTextSize(ts_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(
        canvas,
        ts_text,
        (w - tw - 12, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (220, 230, 245),
        1,
        cv2.LINE_AA
    )

    return canvas


def generate_annotated_video(
    annotated_frames: List[np.ndarray],
    output_path: Path | str,
    fps: float = 25.0,
    width: Optional[int] = None,
    height: Optional[int] = None
) -> Path:
    """Encode a sequence of annotated frames into an MP4 video.

    Args:
        annotated_frames: Ordered list of annotated BGR numpy frames.
        output_path: Destination file path for generated video.
        fps: Playback frame rate.
        width: Frame width (inferred from first frame if None).
        height: Frame height (inferred from first frame if None).

    Returns:
        Path to completed MP4 video.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not annotated_frames:
        raise ValueError("Cannot write video: frame list is empty.")

    h, w = annotated_frames[0].shape[:2]
    out_w = width or w
    out_h = height or h

    # Try MP4V codec first, fall back to MJPG or XVID
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(dest), fourcc, max(1.0, float(fps)), (out_w, out_h))

    if not writer.isOpened():
        # Fallback codec
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(dest), fourcc, max(1.0, float(fps)), (out_w, out_h))

    try:
        for f in annotated_frames:
            if f.shape[1] != out_w or f.shape[0] != out_h:
                f_resized = cv2.resize(f, (out_w, out_h))
                writer.write(f_resized)
            else:
                writer.write(f)
    finally:
        writer.release()

    return dest
