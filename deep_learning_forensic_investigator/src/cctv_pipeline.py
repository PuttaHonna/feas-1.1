"""
CCTV Analysis Pipeline Orchestrator.
Coordinates the end-to-end execution flow:
Validation -> Immutable Intake -> Cryptographic Hashing -> Working Copy
-> Frame Extraction -> Deterministic Enhancement -> YOLO Detection
-> Multi-Object Tracking -> Event Extraction -> Video Annotation
-> Keyframe Curation -> CSV/JSON Export -> Audit Logging.
"""

from __future__ import annotations
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.cctv.integrity import calculate_file_sha256, verify_sha256
from src.cctv.video_validator import validate_cctv_video
from src.cctv.video_metadata import extract_technical_metadata
from src.cctv.working_copy import create_verified_working_copy
from src.cctv.frame_extractor import extract_cctv_frames
from src.cctv.enhancement import enhance_frame, EnhancementMode, DERIVED_FRAME_LABEL
from src.cctv.detector import CCTVDetector
from src.cctv.tracker import CCTVTracker
from src.cctv.event_extractor import CCTVEventExtractor
from src.cctv.annotated_video import draw_detection_overlay, generate_annotated_video
from src.cctv.audit_logger import CCTVAuditLogger
from src.cctv.export_results import export_cctv_artifacts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CCTVPipeline")


def run_cctv_analysis(
    input_video_path: Path | str,
    case_id: str = "CASE-2026-001",
    evidence_id: str = "EV-CCTV-01",
    camera_id: str = "CAM-01",
    camera_location: str = "Main Entrance",
    event_datetime: Optional[str] = None,
    timezone_str: str = "UTC",
    analysis_mode: str = "fast_review",
    frame_sampling_step: int = 1,
    enhancement_mode: str = "basic",
    yolo_model_name: str = "yolov8n.pt",
    confidence_threshold: float = 0.40,
    tracking_method: str = "bytetrack",
    roi_polygon: Optional[List[Tuple[float, float]]] = None,
    evidence_store_dir: Optional[Path | str] = None,
    results_dir: Optional[Path | str] = None,
    db_path: Optional[Path | str] = None,
    max_frames_to_process: Optional[int] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """Execute complete CCTV analysis workflow conforming to forensic integrity guidelines.

    Args:
        input_video_path: Path to user-uploaded source video file.
        case_id: Associated investigation case ID.
        evidence_id: Unique evidence identifier.
        camera_id: User-supplied camera ID.
        camera_location: User-supplied camera location.
        event_datetime: User-supplied incident date/time.
        timezone_str: User-supplied timezone string.
        analysis_mode: 'fast_review' (1 FPS) or 'full_analysis'.
        frame_sampling_step: Sampling step for full analysis mode (e.g. 1, 2, 5).
        enhancement_mode: 'none', 'basic', or 'low_light'.
        yolo_model_name: Model weights filename (default 'yolov8n.pt').
        confidence_threshold: Confidence threshold for detection (default 0.40).
        tracking_method: Multi-object tracking algorithm identifier.
        roi_polygon: Optional list of (x, y) coordinates defining an ROI zone.
        evidence_store_dir: Base directory for originals and working copies.
        results_dir: Base directory for exported CCTV artifacts.
        db_path: Path to SQLite audit database.
        max_frames_to_process: Optional cap for total frames (testing/benchmarking).
        progress_callback: Optional callable accepting (progress_float, status_text).

    Returns:
        Structured result dictionary containing paths to generated artifacts and statistics.
    """
    def update_progress(pct: float, message: str):
        logger.info(f"[{int(pct * 100)}%] {message}")
        if progress_callback:
            try:
                progress_callback(pct, message)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")

    update_progress(0.02, "Initializing CCTV forensic analysis environment...")

    # Configure directory hierarchy
    repo_root = Path(input_video_path).resolve().parent
    store_base = Path(evidence_store_dir) if evidence_store_dir else repo_root / "evidence_store"
    results_base = Path(results_dir) if results_dir else repo_root / "results" / "cctv"
    database_file = Path(db_path) if db_path else store_base / "audit_log.db"

    originals_dir = store_base / "originals"
    working_copies_dir = store_base / "working_copies"
    enhanced_frames_dir = results_base / "enhanced_frames"
    keyframes_dir = results_base / "keyframes"
    annotated_vids_dir = results_base / "annotated_videos"
    logs_dir = results_base / "detection_logs"
    meta_dir = results_base / "metadata"
    reports_dir = results_base / "reports"

    for d in [
        originals_dir, working_copies_dir, enhanced_frames_dir,
        keyframes_dir / "overview", keyframes_dir / "entries",
        keyframes_dir / "exits", keyframes_dir / "best_detections",
        annotated_vids_dir, logs_dir, meta_dir, reports_dir
    ]:
        d.mkdir(parents=True, exist_ok=True)

    audit_logger = CCTVAuditLogger(database_file)
    run_id = f"RUN-{evidence_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # 1. Step 1 & 2: Validate video container and size
    update_progress(0.05, "Validating video format and stream integrity...")
    val_result = validate_cctv_video(input_video_path)
    if not val_result.is_valid:
        raise ValueError(f"Video validation failed: {val_result.error_message}")

    # 2. Step 3 & 4: Preserve Original Evidence & Calculate Hash
    update_progress(0.10, "Preserving original evidence and calculating SHA-256 hash...")
    input_p = Path(input_video_path)
    target_original = originals_dir / f"{evidence_id}_{input_p.name}"

    # Only copy to originals if it is not already located there
    if input_p.resolve() != target_original.resolve():
        shutil.copy2(input_p, target_original)
        orig_evidence_path = target_original
    else:
        orig_evidence_path = input_p

    original_sha256 = calculate_file_sha256(orig_evidence_path)
    original_size = orig_evidence_path.stat().st_size

    # 3. Step 5: Store original file in SQLite audit log
    audit_logger.record_evidence_intake(
        evidence_id=evidence_id,
        case_id=case_id,
        original_filename=orig_evidence_path.name,
        original_path=str(orig_evidence_path),
        original_sha256=original_sha256,
        original_size_bytes=original_size
    )

    audit_logger.record_run_start(
        run_id=run_id,
        evidence_id=evidence_id,
        enhancement_mode=enhancement_mode,
        frame_sampling=f"{analysis_mode}:{frame_sampling_step}",
        yolo_model=yolo_model_name,
        confidence_threshold=confidence_threshold,
        tracking_method=tracking_method
    )

    try:
        # 4. Step 6 & 7: Extract Technical Metadata
        update_progress(0.15, "Extracting video container metadata...")
        user_meta = {
            "camera_id": camera_id,
            "camera_location": camera_location,
            "event_datetime": event_datetime,
            "timezone": timezone_str,
            "yolo_model": yolo_model_name,
            "confidence_threshold": confidence_threshold,
            "tracking_method": tracking_method,
            "enhancement_settings": enhancement_mode,
            "processing_start_time": datetime.now(timezone.utc).isoformat()
        }
        metadata = extract_technical_metadata(
            video_path=orig_evidence_path,
            evidence_id=evidence_id,
            case_id=case_id,
            user_metadata=user_meta,
            precomputed_sha256=original_sha256
        )

        # 5. Step 8: Create verified derived working copy
        update_progress(0.20, "Creating cryptographically verified working copy...")
        working_copy_path, working_copy_sha256 = create_verified_working_copy(
            original_path=orig_evidence_path,
            working_copies_dir=working_copies_dir,
            unique_prefix=evidence_id
        )
        metadata["working_copy_sha256"] = working_copy_sha256

        # Update evidence table with working copy hash
        audit_logger.record_evidence_intake(
            evidence_id=evidence_id,
            case_id=case_id,
            original_filename=orig_evidence_path.name,
            original_path=str(orig_evidence_path),
            original_sha256=original_sha256,
            original_size_bytes=original_size,
            working_copy_path=str(working_copy_path),
            working_copy_sha256=working_copy_sha256
        )

        # 6. Initialize Analytic Engines
        update_progress(0.25, f"Loading YOLOv8 model ({yolo_model_name})...")
        detector = CCTVDetector(
            model_name=yolo_model_name,
            confidence_threshold=confidence_threshold
        )
        tracker = CCTVTracker()
        event_extractor = CCTVEventExtractor(
            dwell_threshold_seconds=10.0,
            roi_polygon=roi_polygon,
            roi_dwell_threshold_seconds=5.0
        )

        # 7. Extract, Enhance, Detect, Track, and Annotate Frames
        update_progress(0.30, "Streaming and analyzing video frames...")
        annotated_frames: List[np.ndarray] = []
        all_detections = []
        overview_keyframes = []

        track_best_conf: Dict[str, float] = {}
        track_best_img: Dict[str, np.ndarray] = {}
        track_first_saved: Set[str] = set()

        frame_stream = extract_cctv_frames(
            video_path=working_copy_path,
            analysis_mode=analysis_mode,
            sampling_step=frame_sampling_step,
            target_fps=1.0,
            max_frames=max_frames_to_process
        )

        # Process frames iteratively
        frame_counter = 0
        for frame_item in frame_stream:
            frame_counter += 1
            f_idx = frame_item.frame_index
            t_sec = frame_item.timestamp_seconds
            t_hms = frame_item.timestamp_hms
            raw_bgr = frame_item.image

            # Step 10: Apply deterministic enhancement to working frame only
            enhanced_bgr = enhance_frame(raw_bgr, mode=enhancement_mode)

            # Step 11: Run YOLO object detection
            detections = detector.detect_frame(
                frame_bgr=enhanced_bgr,
                frame_number=f_idx,
                timestamp_seconds=t_sec,
                timestamp_hms=t_hms,
                camera_id=camera_id,
                evidence_id=evidence_id
            )

            # Step 12: Run multi-object tracking
            tracked_detections = tracker.update(
                detections=detections,
                frame_number=f_idx,
                timestamp_seconds=t_sec
            )

            # Save overview keyframes at 1 FPS
            if frame_item.is_overview_keyframe:
                ov_path = keyframes_dir / "overview" / f"overview_{f_idx:06d}.jpg"
                cv2.imwrite(str(ov_path), raw_bgr)
                overview_keyframes.append(str(ov_path))

            # Manage track entry, best-detection, and exit keyframes
            for det in tracked_detections:
                tid = det.track_id
                if not tid:
                    continue

                # First seen keyframe
                if tid not in track_first_saved:
                    entry_path = keyframes_dir / "entries" / f"entry_{tid}_f{f_idx}.jpg"
                    cv2.imwrite(str(entry_path), enhanced_bgr)
                    det.keyframe_path = str(entry_path)
                    track_first_saved.add(tid)
                    if tid in tracker.active_tracks:
                        tracker.active_tracks[tid]["first_keyframe"] = str(entry_path)

                # Best confidence keyframe candidate
                prev_best = track_best_conf.get(tid, 0.0)
                if det.confidence > prev_best:
                    track_best_conf[tid] = det.confidence
                    track_best_img[tid] = enhanced_bgr.copy()

            # Step 13: Extract objective spatio-temporal events
            current_kf = det.keyframe_path if tracked_detections else None
            event_extractor.process_frame_detections(
                detections=tracked_detections,
                frame_number=f_idx,
                timestamp_seconds=t_sec,
                timestamp_hms=t_hms,
                camera_id=camera_id,
                keyframe_path=current_kf
            )

            # Step 14: Render derived visualization overlay
            annotated_frame = draw_detection_overlay(
                frame_bgr=enhanced_bgr,
                detections=tracked_detections,
                timestamp_hms=t_hms,
                roi_polygon=roi_polygon
            )
            annotated_frames.append(annotated_frame)
            all_detections.extend(tracked_detections)

            # Periodic progress update
            if frame_counter % 20 == 0:
                pct = min(0.75, 0.30 + (frame_counter / 200.0) * 0.45)
                update_progress(pct, f"Processed {frame_counter} frames... (Tracks: {len(tracker.active_tracks)})")

        # Save best confidence keyframes for all tracks
        for tid, img in track_best_img.items():
            best_path = keyframes_dir / "best_detections" / f"best_{tid}.jpg"
            cv2.imwrite(str(best_path), img)
            if tid in tracker.active_tracks:
                tracker.active_tracks[tid]["best_keyframe"] = str(best_path)

        # Finalize tracks and evaluate exits
        update_progress(0.80, "Finalizing trajectories and exit events...")
        final_tracks = tracker.finalize()
        event_extractor.evaluate_completed_tracks(final_tracks)
        events = event_extractor.get_events()

        # Save last seen keyframes
        for tid, t in final_tracks.items():
            if t.last_keyframe is None and tid in track_best_img:
                exit_path = keyframes_dir / "exits" / f"exit_{tid}_f{t.last_frame}.jpg"
                cv2.imwrite(str(exit_path), track_best_img[tid])
                t.last_keyframe = str(exit_path)

        # Step 15: Create annotated output video
        update_progress(0.85, "Encoding derived annotated video output...")
        annotated_video_path = annotated_vids_dir / f"{evidence_id}_annotated.mp4"
        if annotated_frames:
            generate_annotated_video(
                annotated_frames=annotated_frames,
                output_path=annotated_video_path,
                fps=metadata.get("fps", 25.0)
            )
            audit_logger.record_artifact(
                artifact_id=f"ART-VID-{evidence_id}",
                run_id=run_id,
                artifact_type="ANNOTATED_VIDEO",
                artifact_path=str(annotated_video_path)
            )

        # Step 16: Export CSV, JSON logs, and summary
        update_progress(0.92, "Exporting structured detection logs, CSVs, and dossier...")
        metadata["processing_finish_time"] = datetime.now(timezone.utc).isoformat()
        audit_summary = audit_logger.get_run_audit_summary(run_id)

        exported_files = export_cctv_artifacts(
            results_dir=results_base,
            evidence_id=evidence_id,
            metadata=metadata,
            detections=all_detections,
            tracks=final_tracks,
            events=events,
            audit_summary=audit_summary
        )

        for name, fpath in exported_files.items():
            audit_logger.record_artifact(
                artifact_id=f"ART-{name.upper()}-{evidence_id}",
                run_id=run_id,
                artifact_type=name.upper(),
                artifact_path=str(fpath)
            )

        # Mark run finished in audit log
        audit_logger.record_run_finish(run_id=run_id, status="COMPLETED")
        update_progress(1.0, "CCTV forensic video analysis complete.")

        return {
            "status": "success",
            "run_id": run_id,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "original_sha256": original_sha256,
            "working_copy_sha256": working_copy_sha256,
            "metadata": metadata,
            "annotated_video_path": str(annotated_video_path),
            "detections_csv_path": str(exported_files["detections_csv"]),
            "tracks_csv_path": str(exported_files["tracks_csv"]),
            "events_json_path": str(exported_files["events_json"]),
            "summary_json_path": str(exported_files["summary_json"]),
            "audit_log_json_path": str(exported_files["audit_log_json"]),
            "total_frames_processed": frame_counter,
            "total_detections": len(all_detections),
            "total_tracks": len(final_tracks),
            "total_events": len(events),
            "events": [e.to_dict() for e in events],
            "tracks": final_tracks,
            "overview_keyframes": overview_keyframes[:10],
            "derived_label": DERIVED_FRAME_LABEL
        }

    except Exception as e:
        logger.error(f"Pipeline failure: {e}", exc_info=True)
        audit_logger.record_run_finish(run_id=run_id, status="FAILED", error_message=str(e))
        raise
