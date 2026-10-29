"""
Forensic CCTV Video Processing Pipeline
Integrates:
- Strict evidence preservation (vault read-only copy + derived working copy)
- Cryptographic hash verification (SHA-256 on all inputs and artifacts)
- SQLite WAL audit logging
- Deterministic OpenCV frame enhancement
- COCO-only object detection
- Multi-object tracking & objective event extraction
- Export of annotated derived video, detections CSV, tracks CSV, and events JSON
"""

import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256
from src.common.file_validation import validate_file_integrity
from src.common.audit_db import AuditDatabase
from src.common.utils import preserve_original_evidence, create_working_copy
from src.cctv.enhancement import enhance_frame
from src.cctv.detector import ForensicObjectDetector
from src.cctv.tracker import ForensicTracker
from src.cctv.events import ObjectiveEventExtractor


# Visual palette for distinct classes
CLASS_COLORS = {
    "person": (0, 200, 255),       # Orange/Yellow
    "car": (255, 100, 0),          # Blue
    "bicycle": (0, 255, 128),      # Green
    "motorcycle": (200, 200, 0),   # Cyan
    "bus": (255, 0, 150),          # Violet
    "truck": (180, 0, 255),        # Magenta
    "backpack": (0, 165, 255),     # Orange
    "handbag": (147, 20, 255),     # Pink
    "suitcase": (0, 255, 255),     # Yellow
    "cell phone": (50, 205, 50),   # Lime
}


def run_cctv_pipeline(
    video_path: Path,
    output_dir: Path,
    audit_db: Optional[AuditDatabase] = None,
    gamma: float = 1.0,
    enable_clahe: bool = True,
    enable_denoise: bool = True,
    enable_sharpen: bool = True,
    conf_threshold: float = 0.35,
    duration_threshold_sec: float = 5.0,
    roi_polygon: Optional[List[Tuple[int, int]]] = None,
    max_frames_to_process: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Executes end-to-end CCTV forensic analysis adhering to all evidentiary constraints.
    """
    src_path = Path(video_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    keyframes_dir = out_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    db = audit_db or AuditDatabase()

    # 1. File Validation
    val_res = validate_file_integrity(src_path)
    if not val_res.is_valid:
        raise ValueError(f"Evidence validation failed: {val_res.error_message}")
    if val_res.file_type != "video":
        raise ValueError(f"Input is not a video file: {src_path}")

    # 2. Evidence Registration & Vault Preservation
    orig_sha256 = val_res.sha256
    vault_path, vault_sha256 = preserve_original_evidence(
        source_path=src_path,
        evidence_id=f"cctv_{src_path.stem}",
    )

    # 3. Working Copy Creation
    working_path, working_sha256 = create_working_copy(
        vault_path=vault_path,
        evidence_id=f"cctv_{src_path.stem}",
    )

    # Register in Audit DB
    evidence_id = db.register_evidence(
        original_filename=src_path.name,
        original_sha256=orig_sha256,
        working_copy_sha256=working_sha256,
        file_type="video",
        file_size_bytes=val_res.file_size_bytes,
        original_path=str(vault_path),
        working_copy_path=str(working_path),
        metadata=val_res.metadata,
    )

    # 4. Start Processing Run
    run_id = db.start_processing_run(
        evidence_id=evidence_id,
        module_name="cctv_enhancement_detection_tracking",
        model_name="yolov8n_coco_filtered",
        config={
            "gamma": gamma,
            "enable_clahe": enable_clahe,
            "enable_denoise": enable_denoise,
            "enable_sharpen": enable_sharpen,
            "conf_threshold": conf_threshold,
            "duration_threshold_sec": duration_threshold_sec,
        },
        seed=FORENSIC_CONFIG.DEFAULT_RANDOM_SEED,
    )

    # 5. Open Working Copy Video
    cap = cv2.VideoCapture(str(working_path))
    if not cap.isOpened():
        db.fail_run(run_id, "Failed to open derived working copy video with OpenCV.")
        raise RuntimeError("Failed to open derived working copy video.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Initialize components
    detector = ForensicObjectDetector(conf_threshold=conf_threshold)
    tracker = ForensicTracker(iou_threshold=0.3, max_lost_frames=int(fps))
    event_extractor = ObjectiveEventExtractor(
        frame_width=width,
        frame_height=height,
        duration_threshold_sec=duration_threshold_sec,
        roi_polygon=roi_polygon,
    )

    # Prepare Video Writer
    # The enhanced frame has a bottom banner attached, so output height increases
    sample_banner = np.zeros((max(24, int(height * 0.05)), width, 3), dtype=np.uint8)
    out_height = height + sample_banner.shape[0]

    annotated_video_path = out_dir / "annotated_cctv.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(annotated_video_path), fourcc, fps, (width, out_height))

    frame_idx = 0
    all_detections: List[Dict[str, Any]] = []
    all_tracks: List[Dict[str, Any]] = []

    saved_keyframe_count = 0
    max_keyframes = 10

    while True:
        if max_frames_to_process and frame_idx >= max_frames_to_process:
            break

        ret, frame = cap.read()
        if not ret or frame is None:
            break

        timestamp_sec = round(frame_idx / fps, 3)

        # A. Deterministic Enhancement
        enhanced = enhance_frame(
            frame=frame,
            gamma=gamma,
            enable_clahe=enable_clahe,
            enable_denoise=enable_denoise,
            enable_sharpen=enable_sharpen,
            add_banner=True,
        )

        # B. Detection on the visual frame (crop out bottom banner for model inference)
        raw_enhanced = enhanced[:height, :width]
        detections = detector.detect_frame(
            frame=raw_enhanced,
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
        )
        all_detections.extend(detections)

        # C. Tracking
        active_records = tracker.update(
            detections=detections,
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
        )
        all_tracks.extend(active_records)

        # D. Objective Event Extraction
        event_extractor.process_frame(
            tracks=active_records,
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
            active_tracker_instances=tracker.active_tracks,
        )

        # E. Draw Annotations on enhanced frame
        # Draw ROI polygon if defined
        if roi_polygon and len(roi_polygon) >= 3:
            pts = np.array(roi_polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(enhanced, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
            cv2.putText(
                enhanced,
                "Configured ROI",
                (roi_polygon[0][0] + 5, roi_polygon[0][1] + 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),
                1,
            )

        for trk in active_records:
            tid = trk["track_id"]
            cls_name = trk["class_name"]
            x1, y1, x2, y2 = [int(c) for c in trk["bbox"]]
            color = CLASS_COLORS.get(cls_name, (0, 255, 0))

            # Bounding box
            cv2.rectangle(enhanced, (x1, y1), (x2, y2), color, 2)

            # Label badge
            label_str = f"ID:{tid} {cls_name} {trk['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(enhanced, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, max(0, y1)), color, -1)
            cv2.putText(
                enhanced,
                label_str,
                (x1 + 2, max(0, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # Header watermark: timestamp and frame counter
        header_text = f"Frame: {frame_idx:05d} | Time: {timestamp_sec:06.2f}s | Active Tracks: {len(active_records)}"
        cv2.putText(
            enhanced,
            header_text,
            (15, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        writer.write(enhanced)

        # Keyframe saving: save if detections exist and under cap
        if len(active_records) > 0 and saved_keyframe_count < max_keyframes:
            if frame_idx % max(1, int(fps)) == 0:
                kf_path = keyframes_dir / f"keyframe_{frame_idx:05d}_{timestamp_sec:.2f}s.png"
                cv2.imwrite(str(kf_path), enhanced)
                saved_keyframe_count += 1

        frame_idx += 1

    cap.release()
    writer.release()

    # Finalize tracker & exits
    track_summaries = tracker.finalize()
    event_extractor.finalize_exits(track_summaries)
    events = event_extractor.get_events()

    # 6. Export CSVs & JSON
    detections_csv_path = out_dir / "detections.csv"
    with open(detections_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["frame_idx", "timestamp_sec", "class_id", "class_name", "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]
        writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
        writer_csv.writeheader()
        for det in all_detections:
            writer_csv.writerow({
                "frame_idx": det["frame_idx"],
                "timestamp_sec": det["timestamp_sec"],
                "class_id": det["class_id"],
                "class_name": det["class_name"],
                "confidence": det["confidence"],
                "bbox_x1": det["bbox"][0],
                "bbox_y1": det["bbox"][1],
                "bbox_x2": det["bbox"][2],
                "bbox_y2": det["bbox"][3],
            })

    tracks_csv_path = out_dir / "tracks.csv"
    with open(tracks_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["track_id", "class_name", "frame_idx", "timestamp_sec", "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]
        writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
        writer_csv.writeheader()
        for trk in all_tracks:
            writer_csv.writerow({
                "track_id": trk["track_id"],
                "class_name": trk["class_name"],
                "frame_idx": trk["frame_idx"],
                "timestamp_sec": trk["timestamp_sec"],
                "confidence": trk["confidence"],
                "bbox_x1": trk["bbox"][0],
                "bbox_y1": trk["bbox"][1],
                "bbox_x2": trk["bbox"][2],
                "bbox_y2": trk["bbox"][3],
            })

    events_json_path = out_dir / "events.json"
    with open(events_json_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    # 7. Calculate artifact hashes and log to SQLite audit log
    annotated_hash = calculate_sha256(annotated_video_path) if annotated_video_path.exists() else ""
    detections_hash = calculate_sha256(detections_csv_path) if detections_csv_path.exists() else ""
    tracks_hash = calculate_sha256(tracks_csv_path) if tracks_csv_path.exists() else ""
    events_hash = calculate_sha256(events_json_path) if events_json_path.exists() else ""

    db.log_event(
        run_id=run_id,
        evidence_id=evidence_id,
        stage_name="cctv_export",
        action="exported_annotated_video_and_metadata",
        input_sha256=working_sha256,
        output_sha256=annotated_hash,
        artifact_path=str(annotated_video_path),
        details={
            "detections_csv_sha256": detections_hash,
            "tracks_csv_sha256": tracks_hash,
            "events_json_sha256": events_hash,
        },
    )

    metrics = {
        "frames_processed": frame_idx,
        "total_detections": len(all_detections),
        "unique_tracks": len(track_summaries),
        "total_events": len(events),
        "video_duration_seconds": round(frame_idx / fps, 2),
    }

    db.complete_run(run_id, metrics=metrics)

    return {
        "status": "completed",
        "evidence_id": evidence_id,
        "run_id": run_id,
        "original_sha256": orig_sha256,
        "working_copy_sha256": working_sha256,
        "artifacts": {
            "annotated_video": str(annotated_video_path),
            "annotated_video_sha256": annotated_hash,
            "detections_csv": str(detections_csv_path),
            "detections_csv_sha256": detections_hash,
            "tracks_csv": str(tracks_csv_path),
            "tracks_csv_sha256": tracks_hash,
            "events_json": str(events_json_path),
            "events_json_sha256": events_hash,
            "keyframes_dir": str(keyframes_dir),
            "keyframes_saved": saved_keyframe_count,
        },
        "metrics": metrics,
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }
