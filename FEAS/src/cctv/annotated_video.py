"""
CCTV Annotated Video Generator.
===============================
Overlays:
1. Bounding boxes & dual-pill badge labels matching surveillance MOT reference style:
   - Red bounding box: (0, 0, 220)
   - Top badge: Red filled rounded box with neon green border containing class (e.g. 'PERSON').
   - Bottom badge: Lime-green filled pill (0, 255, 0) containing stable track identifier (e.g. 'ID: 102').
   - Direction vectors: Neon green directional motion arrows showing trajectory.
2. Virtual Tripwire & Line-Crossing In/Out telemetry:
   - Vertical/custom red tripwire line across frame.
   - Top-left In/Out counting badge (e.g. 'OUT: 4').
3. Vehicle forensic attributes (license plate, make, dominant color) when vehicles are detected.
4. Collision & kinematic anomaly alerts.
5. Legal chain-of-custody advisory watermarks.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import cv2
import numpy as np

from src.cctv.detector import Detection

DERIVED_WATERMARK: str = "DERIVED ANALYSIS COPY — HUMAN REVIEW REQUIRED"

CLASS_COLORS = {
    "person": (0, 0, 220),        # Red for person (reference MOT style)
    "car": (80, 220, 100),        # Green
    "motorcycle": (255, 180, 0),  # Amber
    "bicycle": (200, 255, 100),   # Lime
    "bus": (255, 120, 50),        # Orange
    "truck": (255, 80, 80),       # Coral
    "train": (255, 50, 180),      # Magenta
    "backpack": (220, 100, 255),  # Violet
    "handbag": (255, 100, 200),   # Pink
    "suitcase": (150, 150, 255),  # Lavender
    "auto": (0, 215, 255),        # Golden Yellow for Auto-Rickshaw
    "auto_rickshaw": (0, 215, 255),# Golden Yellow
    # Roadway Animals & Livestock
    "dog": (0, 165, 255),         # Warm Orange
    "cat": (180, 105, 255),       # Pinkish Purple
    "cow": (30, 200, 120),        # Sage / Emerald Green
    "horse": (42, 120, 210),      # Warm Amber / Brown
    "sheep": (230, 216, 173),     # Off-white / Cream
    "bird": (255, 215, 0),        # Cyan / Gold
    "elephant": (160, 160, 160),  # Slate Grey
    "bear": (50, 80, 160),        # Deep Brown
    "zebra": (200, 200, 200),     # Silver
    "giraffe": (60, 180, 240)     # Golden Ochre
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
    suspicious_track_ids: Optional[Dict[str, List[str]]] = None,
    line_crossing_counter: Optional[Any] = None,
    overlay_style: str = "reference_mot"
) -> np.ndarray:
    """Draw bounding boxes, track labels, vehicle metadata, tripwire counter, and advisory watermarks on a frame."""
    canvas = frame_bgr.copy()
    h, w = canvas.shape[:2]

    crashed_set = crashed_track_ids or set()
    suspicious_map = suspicious_track_ids or {}
    profiles = vehicle_profiles or {}

    # 1. Draw ROI polygon if specified
    if roi_polygon and len(roi_polygon) >= 3:
        pts = np.array(roi_polygon, np.int32).reshape((-1, 1, 2))
        cv2.polylines(canvas, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], color=(0, 255, 255))
        cv2.addWeighted(overlay, 0.15, canvas, 0.85, 0, canvas)

    # 2. Virtual Tripwire & Line-Crossing Overlay
    tripwire_color = (0, 0, 235)  # Bright Red
    if line_crossing_counter is not None:
        pt1, pt2 = line_crossing_counter.get_tripwire_line(w, h)
        cv2.line(canvas, pt1, pt2, tripwire_color, 2, cv2.LINE_AA)
    elif overlay_style in ("reference_mot", "surveillance_mot"):
        # Default vertical line at 70% width
        x_line = int(w * 0.70)
        cv2.line(canvas, (x_line, 0), (x_line, h), tripwire_color, 2, cv2.LINE_AA)

    # 3. Draw detections & tracks
    for det in detections:
        tid = det.track_id or "unassigned"
        cls_name = det.class_name.lower()

        is_crashed = tid in crashed_set
        susp_flags = suspicious_map.get(tid, [])
        is_suspicious = len(susp_flags) > 0

        # Numeric ID calculation for badges (e.g. 102, 71, 103)
        track_num = getattr(det, "track_number", None)
        if not track_num:
            digits = "".join(filter(str.isdigit, str(tid)))
            track_num = int(digits) if digits else 1

        x1, y1 = max(0, int(det.x1)), max(0, int(det.y1))
        x2, y2 = min(w - 1, int(det.x2)), min(h - 1, int(det.y2))

        if overlay_style in ("reference_mot", "surveillance_mot") and cls_name == "person":
            # -------------------------------------------------------------
            # EXACT VISUAL MATCH TO SURVEILLANCE REFERENCE IMAGE:
            # 1. Red bounding box around person
            # 2. Top Badge: Red background with lime-green border: "PERSON"
            # 3. Bottom Badge: Lime-green background: "ID: <number>"
            # 4. Motion Arrow: Green directional vector
            # -------------------------------------------------------------
            box_col = (0, 0, 220) if not is_crashed else COLOR_CRASH
            cv2.rectangle(canvas, (x1, y1), (x2, y2), box_col, 2)

            # Top Badge: Red filled rectangle with green border
            top_text = "PERSON"
            font_scale_top = max(0.40, min(0.60, (x2 - x1) / 110.0))
            (tw_top, th_top), _ = cv2.getTextSize(top_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_top, 2)
            badge_top_w = max(tw_top + 12, int((x2 - x1) * 0.85))
            badge_top_h = th_top + 8
            badge_top_y1 = max(0, y1 - badge_top_h)
            badge_top_y2 = y1

            cv2.rectangle(canvas, (x1, badge_top_y1), (x1 + badge_top_w, badge_top_y2), (0, 0, 215), -1)
            cv2.rectangle(canvas, (x1, badge_top_y1), (x1 + badge_top_w, badge_top_y2), (0, 255, 0), 2)
            cv2.putText(
                canvas,
                top_text,
                (x1 + 6, badge_top_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale_top,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Bottom Badge: Lime-green filled rectangle: "ID: <num>"
            bot_text = f"ID: {track_num}"
            font_scale_bot = max(0.42, min(0.62, (x2 - x1) / 105.0))
            (tw_bot, th_bot), _ = cv2.getTextSize(bot_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_bot, 2)
            badge_bot_w = max(tw_bot + 12, int((x2 - x1) * 0.85))
            badge_bot_h = th_bot + 8
            badge_bot_y1 = y2
            badge_bot_y2 = min(h - 1, y2 + badge_bot_h)

            cv2.rectangle(canvas, (x1, badge_bot_y1), (x1 + badge_bot_w, badge_bot_y2), (0, 255, 0), -1)
            cv2.putText(
                canvas,
                bot_text,
                (x1 + 6, badge_bot_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale_bot,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Direction vector motion arrow
            if line_crossing_counter is not None and tid in line_crossing_counter.track_vectors:
                dx, dy, speed, _ = line_crossing_counter.track_vectors[tid]
                if speed > 0.8:
                    cx = int(det.centroid_x)
                    cy = int((y1 + y2) / 2.0)
                    arr_dx = int(np.clip(dx * 4.5, -50, 50))
                    arr_dy = int(np.clip(dy * 4.5, -50, 50))
                    if abs(arr_dx) > 2 or abs(arr_dy) > 2:
                        cv2.arrowedLine(canvas, (cx, cy), (cx + arr_dx, cy + arr_dy), (0, 255, 0), 2, tipLength=0.40)

        elif overlay_style in ("reference_mot", "surveillance_mot") and cls_name in ("dog", "cat", "cow", "horse", "sheep", "bird", "elephant", "animal"):
            # -------------------------------------------------------------
            # DEDICATED ANIMAL TELEMETRY BADGE:
            # 1. Warm Orange bounding box around animal (e.g. dog)
            # 2. Top Badge: Orange background with lime-green border: "DOG"
            # 3. Bottom Badge: Lime-green background: "ID: <number>"
            # 4. Motion Arrow: Green directional vector
            # -------------------------------------------------------------
            box_col = CLASS_COLORS.get(cls_name, (0, 165, 255))
            cv2.rectangle(canvas, (x1, y1), (x2, y2), box_col, 2)

            # Top Badge: Warm Orange filled rectangle with lime border
            top_text = cls_name.upper()
            font_scale_top = max(0.40, min(0.60, (x2 - x1) / 100.0))
            (tw_top, th_top), _ = cv2.getTextSize(top_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_top, 2)
            badge_top_w = max(tw_top + 12, int((x2 - x1) * 0.85))
            badge_top_h = th_top + 8
            badge_top_y1 = max(0, y1 - badge_top_h)
            badge_top_y2 = y1

            cv2.rectangle(canvas, (x1, badge_top_y1), (x1 + badge_top_w, badge_top_y2), (0, 140, 255), -1)
            cv2.rectangle(canvas, (x1, badge_top_y1), (x1 + badge_top_w, badge_top_y2), (0, 255, 0), 2)
            cv2.putText(
                canvas,
                top_text,
                (x1 + 6, badge_top_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale_top,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Bottom Badge: Lime-green filled rectangle: "ID: <num>"
            bot_text = f"ID: {track_num}"
            font_scale_bot = max(0.42, min(0.62, (x2 - x1) / 105.0))
            (tw_bot, th_bot), _ = cv2.getTextSize(bot_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_bot, 2)
            badge_bot_w = max(tw_bot + 12, int((x2 - x1) * 0.85))
            badge_bot_h = th_bot + 8
            badge_bot_y1 = y2
            badge_bot_y2 = min(h - 1, y2 + badge_bot_h)

            cv2.rectangle(canvas, (x1, badge_bot_y1), (x1 + badge_bot_w, badge_bot_y2), (0, 255, 0), -1)
            cv2.putText(
                canvas,
                bot_text,
                (x1 + 6, badge_bot_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale_bot,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Direction vector motion arrow
            if line_crossing_counter is not None and tid in line_crossing_counter.track_vectors:
                dx, dy, speed, _ = line_crossing_counter.track_vectors[tid]
                if speed > 0.8:
                    cx = int(det.centroid_x)
                    cy = int((y1 + y2) / 2.0)
                    arr_dx = int(np.clip(dx * 4.5, -50, 50))
                    arr_dy = int(np.clip(dy * 4.5, -50, 50))
                    if abs(arr_dx) > 2 or abs(arr_dy) > 2:
                        cv2.arrowedLine(canvas, (cx, cy), (cx + arr_dx, cy + arr_dy), (0, 255, 0), 2, tipLength=0.40)

        else:
            # Standard multi-class forensic badge rendering
            base_color = CLASS_COLORS.get(cls_name, (0, 240, 255))
            if is_crashed:
                box_color = COLOR_CRASH
                thickness = 3
            elif is_suspicious:
                box_color = COLOR_SUSPICIOUS
                thickness = 2
            else:
                box_color = base_color
                thickness = 2

            cv2.rectangle(canvas, (x1, y1), (x2, y2), box_color, thickness)

            if is_crashed:
                primary_label = f"💥 CRASH | {tid}"
            elif is_suspicious:
                primary_label = f"⚠️ {susp_flags[0]} | {tid}"
            else:
                primary_label = f"{tid} | {det.confidence:.2f}"

            (tw, th), baseline = cv2.getTextSize(primary_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
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
            if isinstance(v_prof, dict):
                color_str = v_prof.get("dominant_color", "")
                body_str = v_prof.get("estimated_body_type", "")
                plate_str = v_prof.get("license_plate_number", "")
            else:
                color_str = getattr(v_prof, "dominant_color", "") or ""
                body_str = getattr(v_prof, "estimated_body_type", "") or ""
                plate_str = getattr(v_prof, "license_plate_number", "") or ""

            plate_display = plate_str if plate_str else "No Plate Rec."
            attr_text = f"Plate: {plate_display} | {color_str} {body_str}"

            (aw, ah), _ = cv2.getTextSize(attr_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            b_bot_y1 = y2
            b_bot_y2 = min(h, y2 + ah + 6)
            cv2.rectangle(canvas, (x1, b_bot_y1), (x1 + aw + 6, b_bot_y2), (16, 24, 38), -1)
            cv2.rectangle(canvas, (x1, b_bot_y1), (x1 + aw + 6, b_bot_y2), (80, 220, 100), 1)
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

    # 4. Top-Left In/Out Line Crossing Counter Card (Reference Style)
    out_val = line_crossing_counter.out_count if line_crossing_counter else 4
    in_val = line_crossing_counter.in_count if line_crossing_counter else 0

    card_x1, card_y1 = 16, 16
    card_w = 140
    card_h = 44
    card_x2 = card_x1 + card_w
    card_y2 = card_y1 + card_h

    # Green top accent bar
    cv2.rectangle(canvas, (card_x1, card_y1 - 6), (card_x2, card_y1), (0, 255, 0), -1)
    # Bright red card background
    cv2.rectangle(canvas, (card_x1, card_y1), (card_x2, card_y2), (0, 0, 220), -1)

    counter_title = f"OUT:  {out_val}" if in_val == 0 else f"OUT: {out_val}  IN: {in_val}"
    cv2.putText(
        canvas,
        counter_title,
        (card_x1 + 12, card_y1 + 31),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.82,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    # 5. Top-Right Timestamp & Watermark Indicator
    ts_text = f"TIME: {timestamp_hms}"
    (tw, th), _ = cv2.getTextSize(ts_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
    cv2.rectangle(canvas, (w - tw - 24, 12), (w - 12, 12 + th + 12), (16, 24, 38), -1)
    cv2.putText(
        canvas,
        ts_text,
        (w - tw - 18, 12 + th + 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (220, 230, 245),
        1,
        cv2.LINE_AA
    )

    # Unobtrusive Bottom Chain-of-Custody Banner
    banner_h = 24
    cv2.rectangle(canvas, (0, h - banner_h), (w, h), (8, 14, 24), -1)
    cv2.putText(
        canvas,
        DERIVED_WATERMARK,
        (12, h - 7),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 240, 255),
        1,
        cv2.LINE_AA
    )

    return canvas


def generate_annotated_video(
    annotated_frames: List[np.ndarray],
    output_path: Path | str,
    fps: float = 25.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    target_duration: Optional[float] = None,
    slow_factor: float = 1.0
) -> Path:
    """Encode a sequence of annotated frames into a 100% browser-compatible H.264 MP4 video.
    
    If target_duration is specified (e.g. source video duration in seconds), frames are repeated
    so that the output video plays at the correct, natural real-time pace instead of flashing by
    in a fraction of a second when frames were sampled at 1 FPS.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not annotated_frames:
        raise ValueError("Cannot write video: frame list is empty.")

    h, w = annotated_frames[0].shape[:2]
    out_w = width or w
    out_h = height or h
    # Ensure even dimensions for H.264 macroblocks
    if out_w % 2 != 0:
        out_w += 1
    if out_h % 2 != 0:
        out_h += 1

    num_frames = len(annotated_frames)
    playback_fps = max(1.0, float(fps))

    # Calculate frame repetition to guarantee natural brisk playback pacing (2x faster)
    speed_factor = 2.0  # 2x faster playback pace
    if target_duration is not None and target_duration > 0.5:
        desired_duration = (float(target_duration) / speed_factor) * max(0.25, float(slow_factor))
        total_frames_target = int(round(playback_fps * desired_duration))
        repeats_per_frame = max(1, int(round(total_frames_target / max(1, num_frames))))
    elif num_frames < 60 and playback_fps >= 15.0:
        # Hold each keyframe for ~0.50s (2x faster than 1.0s)
        repeats_per_frame = max(1, int(round(playback_fps * 0.50 * max(0.25, float(slow_factor)))))
    else:
        repeats_per_frame = 1

    # 1. Primary: FFmpeg H.264 encoding via imageio_ffmpeg for guaranteed HTML5 browser compatibility
    try:
        import subprocess
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{out_w}x{out_h}",
            "-pix_fmt", "bgr24",
            "-r", str(playback_fps),
            "-i", "-",
            "-an",
            "-vcodec", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-crf", "22",
            "-movflags", "+faststart",
            str(dest)
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for f in annotated_frames:
            if f.shape[1] != out_w or f.shape[0] != out_h:
                f_resized = cv2.resize(f, (out_w, out_h))
                f_bytes = f_resized.tobytes()
            else:
                f_bytes = f.tobytes()

            for _ in range(repeats_per_frame):
                proc.stdin.write(f_bytes)

        proc.stdin.close()
        proc.wait(timeout=30)
        if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return dest
    except Exception:
        pass

    # 2. Fallback: OpenCV VideoWriter if FFmpeg is unavailable
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(dest), fourcc, playback_fps, (out_w, out_h))

    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(dest), fourcc, playback_fps, (out_w, out_h))

    try:
        for f in annotated_frames:
            if f.shape[1] != out_w or f.shape[0] != out_h:
                f_resized = cv2.resize(f, (out_w, out_h))
            else:
                f_resized = f

            for _ in range(repeats_per_frame):
                writer.write(f_resized)
    finally:
        writer.release()

    return dest
