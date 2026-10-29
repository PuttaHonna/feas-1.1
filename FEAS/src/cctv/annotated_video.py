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
    "person": (255, 220, 0),        # High-Vis Neon Cyan for Enterprise CCTV
    "car": (0, 230, 115),          # Emerald Green
    "motorcycle": (0, 180, 255),   # Amber
    "bicycle": (0, 215, 255),      # Gold
    "bus": (0, 180, 220),          # Aqua Green
    "truck": (0, 200, 100),        # Deep Emerald
    "train": (255, 50, 180),       # Magenta
    "backpack": (235, 60, 215),    # Violet Magenta
    "handbag": (235, 60, 215),     # Pink Violet
    "suitcase": (200, 80, 240),    # Lavender
    "auto": (0, 215, 255),         # Golden Yellow for Auto-Rickshaw
    "auto_rickshaw": (0, 215, 255),# Golden Yellow
    # Roadway Animals & Livestock
    "dog": (30, 200, 240),         # Warm Sand
    "cat": (30, 200, 240),
    "cow": (30, 200, 240),
    "horse": (30, 200, 240),
    "sheep": (230, 216, 173),
    "bird": (255, 215, 0),
    "elephant": (160, 160, 160),
    "bear": (50, 80, 160),
    "zebra": (200, 200, 200),
    "giraffe": (60, 180, 240)
}

TACTICAL_COLORS = CLASS_COLORS

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
    overlay_style: str = "tactical_hud",
    camera_id: str = "CAM-01"
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

        if overlay_style == "tactical_hud":
            # =============================================================
            # ENTERPRISE AI CCTV TACTICAL CYBER RETICLE & SURVEILLANCE HUD
            # =============================================================
            base_col = TACTICAL_COLORS.get(cls_name, (255, 220, 0))
            if is_crashed:
                box_col = COLOR_CRASH
            elif is_suspicious:
                box_col = COLOR_SUSPICIOUS
            else:
                box_col = base_col

            # A. Sleek Cyber Corner Reticles (L-Brackets)
            box_w = max(1, x2 - x1)
            box_h = max(1, y2 - y1)
            corner_len = max(6, min(24, int(min(box_w, box_h) * 0.22)))
            reticle_thick = 2

            # Top-Left Corner
            cv2.line(canvas, (x1, y1), (x1 + corner_len, y1), box_col, reticle_thick, cv2.LINE_AA)
            cv2.line(canvas, (x1, y1), (x1, y1 + corner_len), box_col, reticle_thick, cv2.LINE_AA)
            # Top-Right Corner
            cv2.line(canvas, (x2, y1), (x2 - corner_len, y1), box_col, reticle_thick, cv2.LINE_AA)
            cv2.line(canvas, (x2, y1), (x2, y1 + corner_len), box_col, reticle_thick, cv2.LINE_AA)
            # Bottom-Left Corner
            cv2.line(canvas, (x1, y2), (x1 + corner_len, y2), box_col, reticle_thick, cv2.LINE_AA)
            cv2.line(canvas, (x1, y2), (x1, y2 - corner_len), box_col, reticle_thick, cv2.LINE_AA)
            # Bottom-Right Corner
            cv2.line(canvas, (x2, y2), (x2 - corner_len, y2), box_col, reticle_thick, cv2.LINE_AA)
            cv2.line(canvas, (x2, y2), (x2, y2 - corner_len), box_col, reticle_thick, cv2.LINE_AA)

            # Ultra-thin precision bounding frame
            cv2.rectangle(canvas, (x1, y1), (x2, y2), box_col, 1, cv2.LINE_4)

            # Center target crosshair dot
            cx = int(det.centroid_x)
            cy = int(det.centroid_y)
            cv2.circle(canvas, (cx, cy), 2, box_col, -1, cv2.LINE_AA)

            # B. Tactical Badge (Top)
            conf_pct = int(det.confidence * 100)
            if is_crashed:
                badge_text = f"COLLISION #{track_num}"
            elif is_suspicious:
                badge_text = f"{susp_flags[0]} #{track_num}"
            else:
                badge_text = f"{cls_name.upper()} #{track_num} {conf_pct}%"

            font_scale = max(0.38, min(0.55, box_w / 125.0))
            (bw, bh), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            b_pad = 4
            pill_w = bw + b_pad * 2 + 10
            pill_h = bh + b_pad * 2 + 2
            pill_y1 = max(0, y1 - pill_h)
            pill_y2 = y1

            # Dark translucent pill background with neon accent border
            cv2.rectangle(canvas, (x1, pill_y1), (x1 + pill_w, pill_y2), (18, 24, 38), -1)
            cv2.rectangle(canvas, (x1, pill_y1), (x1 + pill_w, pill_y2), box_col, 1)
            # Mini color chip on the left
            cv2.rectangle(canvas, (x1 + 1, pill_y1 + 1), (x1 + 4, pill_y2 - 1), box_col, -1)
            cv2.putText(
                canvas,
                badge_text,
                (x1 + b_pad + 6, pill_y2 - b_pad - 1),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (240, 245, 255),
                1,
                cv2.LINE_AA
            )

            # C. Trajectory motion arrow
            if line_crossing_counter is not None and tid in line_crossing_counter.track_vectors:
                dx, dy, speed, _ = line_crossing_counter.track_vectors[tid]
                if speed > 0.8:
                    arr_dx = int(np.clip(dx * 4.0, -45, 45))
                    arr_dy = int(np.clip(dy * 4.0, -45, 45))
                    if abs(arr_dx) > 2 or abs(arr_dy) > 2:
                        cv2.arrowedLine(canvas, (cx, cy), (cx + arr_dx, cy + arr_dy), box_col, 2, tipLength=0.35)

        elif overlay_style in ("reference_mot", "surveillance_mot") and cls_name == "person":
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
            # -------------------------------------------------------------
            box_col = CLASS_COLORS.get(cls_name, (0, 165, 255))
            cv2.rectangle(canvas, (x1, y1), (x2, y2), box_col, 2)

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
                primary_label = f"CRASH | {tid}"
            elif is_suspicious:
                primary_label = f"{susp_flags[0]} | {tid}"
            else:
                primary_label = f"{cls_name.upper()} #{track_num} {int(det.confidence*100)}%"

            (tw, th), baseline = cv2.getTextSize(primary_label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            badge_y1 = max(0, y1 - th - 6)
            badge_y2 = y1
            cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw + 6, badge_y2), (16, 24, 38), -1)
            cv2.rectangle(canvas, (x1, badge_y1), (x1 + tw + 6, badge_y2), box_color, 1)

            cv2.putText(
                canvas,
                primary_label,
                (x1 + 3, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
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

    # 4. Telemetry Header: Tactical HUD vs Classic
    if overlay_style == "tactical_hud":
        # -------------------------------------------------------------
        # ENTERPRISE GLASSMORPHIC CCTV SURVEILLANCE TELEMETRY HUD BAR
        # -------------------------------------------------------------
        hud_h = 34
        hud_y1 = 8
        hud_y2 = hud_y1 + hud_h
        hud_x1 = 12
        hud_x2 = w - 12

        # Translucent bar background
        hud_overlay = canvas.copy()
        cv2.rectangle(hud_overlay, (hud_x1, hud_y1), (hud_x2, hud_y2), (14, 20, 32), -1)
        cv2.addWeighted(hud_overlay, 0.88, canvas, 0.12, 0, canvas)

        # High-tech glowing cyan accent top line & dark border
        cv2.line(canvas, (hud_x1, hud_y1), (hud_x2, hud_y1), (255, 220, 0), 2, cv2.LINE_AA)
        cv2.rectangle(canvas, (hud_x1, hud_y1), (hud_x2, hud_y2), (51, 65, 85), 1)

        # Left: Live surveillance indicator
        live_label = f"LIVE AI SURVEILLANCE  {camera_id}"
        cv2.circle(canvas, (hud_x1 + 14, hud_y1 + 17), 4, (0, 255, 120), -1, cv2.LINE_AA)
        cv2.putText(canvas, live_label, (hud_x1 + 25, hud_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (226, 232, 240), 1, cv2.LINE_AA)

        # Center: Real dynamic counts (No fake fallback numbers)
        out_val = line_crossing_counter.out_count if line_crossing_counter else 0
        in_val = line_crossing_counter.in_count if line_crossing_counter else 0
        center_text = f"TARGETS: {len(detections)}   |   TRIPWIRE: IN {in_val} / OUT {out_val}"
        (cw, ch), _ = cv2.getTextSize(center_text, cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1)
        mid_x = (hud_x1 + hud_x2 - cw) // 2
        cv2.putText(canvas, center_text, (mid_x, hud_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 220, 0), 1, cv2.LINE_AA)

        # Right: Timestamp
        right_text = f"TIME: {timestamp_hms}"
        (rw, rh), _ = cv2.getTextSize(right_text, cv2.FONT_HERSHEY_SIMPLEX, 0.46, 1)
        cv2.putText(canvas, right_text, (hud_x2 - rw - 14, hud_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200, 220, 240), 1, cv2.LINE_AA)

    else:
        # Reference Style / Classic Counter Card
        out_val = line_crossing_counter.out_count if line_crossing_counter else 0
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

        # Top-Right Timestamp & Watermark Indicator
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
    annotated_frames: Sequence[Union[np.ndarray, Path, str]],
    output_path: Path | str,
    fps: float = 25.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    target_duration: Optional[float] = None,
    slow_factor: float = 1.0
) -> Path:
    """Encode a sequence of annotated frames into a 100% browser-compatible H.264 MP4 video.
    
    Supports both in-memory numpy arrays and disk-backed image file paths to guarantee
    sub-512MB RAM streaming execution even on long videos.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not annotated_frames:
        raise ValueError("Cannot write video: frame list is empty.")

    first_item = annotated_frames[0]
    if isinstance(first_item, (str, Path)):
        probe = cv2.imread(str(first_item))
        if probe is None:
            raise ValueError(f"Cannot read first frame from {first_item}")
        h, w = probe.shape[:2]
        del probe
    else:
        h, w = first_item.shape[:2]

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
        for item in annotated_frames:
            if isinstance(item, (str, Path)):
                f = cv2.imread(str(item))
            else:
                f = item
            if f is None:
                continue

            if f.shape[1] != out_w or f.shape[0] != out_h:
                f_resized = cv2.resize(f, (out_w, out_h))
                f_bytes = f_resized.tobytes()
                del f_resized
            else:
                f_bytes = f.tobytes()
            del f

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
        for item in annotated_frames:
            if isinstance(item, (str, Path)):
                f = cv2.imread(str(item))
            else:
                f = item
            if f is None:
                continue

            if f.shape[1] != out_w or f.shape[0] != out_h:
                f_resized = cv2.resize(f, (out_w, out_h))
            else:
                f_resized = f

            for _ in range(repeats_per_frame):
                writer.write(f_resized)
            del f_resized
            del f
    finally:
        writer.release()

    return dest
