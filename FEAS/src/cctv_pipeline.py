"""
CCTV Analysis Pipeline Orchestrator.
Coordinates the end-to-end execution flow:
Validation -> Immutable Intake -> Cryptographic Hashing -> Working Copy
-> Frame Extraction -> Deterministic Enhancement -> YOLO Detection
-> Multi-Object Tracking -> Vehicle Forensic Profiling (ANPR / Color / Model)
-> Collision & Crash Detection -> Suspicious Behavior Analysis
-> Event Extraction -> Video Annotation -> Keyframe Curation
-> Multi-CSV/JSON/Markdown Export -> Audit Logging.
"""

from __future__ import annotations
from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
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
from src.cctv.event_extractor import CCTVEventExtractor, CCTVEvent
from src.cctv.annotated_video import draw_detection_overlay, generate_annotated_video
from src.cctv.vehicle_analyzer import VehicleForensicAnalyzer, VehicleProfile
from src.cctv.collision_detector import CollisionDetector, CollisionIncident
from src.cctv.suspicious_detector import SuspiciousActivityDetector, SuspiciousActivityAlert
from src.cctv.line_crossing import LineCrossingCounter
from src.cctv.audit_logger import CCTVAuditLogger
from src.cctv.export_results import export_cctv_artifacts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CCTVPipeline")

VEHICLE_CLASSES: Set[str] = {"car", "truck", "bus", "motorcycle", "auto", "auto_rickshaw"}


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
    confidence_threshold: float = 0.25,
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
    feas_root = Path(__file__).resolve().parent.parent
    results_base = Path(results_dir).resolve() if results_dir else (feas_root / "results" / "cctv")
    store_base = Path(evidence_store_dir).resolve() if evidence_store_dir else (results_base / "evidence_store")
    database_file = Path(db_path).resolve() if db_path else (store_base / "audit_log.db")

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
    val_res = validate_cctv_video(input_video_path)
    is_valid = getattr(val_res, "is_valid", bool(val_res))
    val_reason = getattr(val_res, "error_message", "Invalid video")
    if not is_valid:
        raise ValueError(f"Video validation failed: {val_reason}")

    # 2. Step 3 & 4: Secure original evidence and compute SHA-256
    update_progress(0.08, "Securing immutable original evidence & calculating SHA-256...")
    in_path = Path(input_video_path)
    original_target_path = originals_dir / f"{evidence_id}_ORIGINAL{in_path.suffix.lower()}"

    if not original_target_path.exists() or original_target_path.resolve() != in_path.resolve():
        if original_target_path.exists():
            import stat
            try:
                original_target_path.chmod(stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        shutil.copy2(in_path, original_target_path)
        try:
            original_target_path.chmod(0o444)
        except Exception:
            pass

    original_sha256 = calculate_file_sha256(original_target_path)

    # 3. Step 5: Extract technical metadata
    update_progress(0.12, "Extracting technical container metadata...")
    metadata = extract_technical_metadata(
        video_path=original_target_path,
        evidence_id=evidence_id,
        case_id=case_id,
        precomputed_sha256=original_sha256
    )
    metadata["case_id"] = case_id
    metadata["evidence_id"] = evidence_id
    metadata["camera_id"] = camera_id
    metadata["camera_location"] = camera_location
    metadata["event_datetime"] = event_datetime
    metadata["timezone"] = timezone_str
    metadata["analysis_mode"] = analysis_mode
    metadata["enhancement_mode"] = enhancement_mode
    metadata["yolo_model"] = yolo_model_name
    metadata["confidence_threshold"] = confidence_threshold
    metadata["tracking_method"] = tracking_method
    metadata["original_sha256"] = original_sha256
    metadata["processing_start_time"] = datetime.now(timezone.utc).isoformat()

    # 4. Step 6, 7 & 8: Create verified working copy
    update_progress(0.18, "Generating verified working copy...")
    working_copy_path, working_copy_sha256 = create_verified_working_copy(
        original_path=original_target_path,
        working_copies_dir=working_copies_dir,
        evidence_id=evidence_id
    )
    metadata["working_copy_path"] = str(working_copy_path)
    metadata["working_copy_sha256"] = working_copy_sha256

    # 5. Initialize audit log entry
    update_progress(0.22, "Initializing audit log and integrity records...")
    audit_logger.record_analysis_run(
        run_id=run_id,
        case_id=case_id,
        evidence_id=evidence_id,
        camera_id=camera_id,
        original_sha256=original_sha256,
        working_copy_sha256=working_copy_sha256,
        parameters=metadata
    )

    try:
        # Audit log step: INGESTION
        audit_logger.record_step(
            step_id=f"STEP-INGEST-{evidence_id}",
            run_id=run_id,
            step_name="INGEST_AND_HASH",
            input_ref=str(original_target_path),
            output_ref=str(working_copy_path),
            parameters={"hash_algorithm": "SHA-256"},
            original_sha256=original_sha256,
            working_copy_sha256=working_copy_sha256
        )

        # 6. Initialize Analytic Engines
        update_progress(0.25, f"Loading YOLOv8 model ({yolo_model_name}) & Forensic Profilers...")
        detector = CCTVDetector(
            model_name=yolo_model_name,
            confidence_threshold=confidence_threshold
        )
        tracker = CCTVTracker()
        configured_roi = roi_polygon
        event_extractor = CCTVEventExtractor(
            dwell_threshold_seconds=5.0,
            roi_polygon=configured_roi,
            roi_dwell_threshold_seconds=3.0
        )
        vehicle_analyzer = VehicleForensicAnalyzer(output_dir=results_base)
        collision_detector = CollisionDetector()
        suspicious_detector = SuspiciousActivityDetector()
        line_crossing_counter = LineCrossingCounter()
        vehicle_profiles: Dict[str, VehicleProfile] = {}

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
        enhancement_impact_records = []
        for frame_item in frame_stream:
            frame_counter += 1
            f_idx = frame_item.frame_index
            t_sec = frame_item.timestamp_seconds
            t_hms = frame_item.timestamp_hms
            raw_bgr = frame_item.image

            # Step 10: Apply targeted enhancement with degradation diagnosis & automated fallback
            if str(enhancement_mode).lower().replace("-", "_") in ("adaptive_smart", "smart", "adaptive"):
                from src.cctv.adaptive_enhancer import enhance_frame_with_audit_and_fallback
                def det_eval(img):
                    return detector.detect_frame(
                        frame_bgr=img,
                        frame_number=f_idx,
                        timestamp_seconds=t_sec,
                        timestamp_hms=t_hms,
                        camera_id=camera_id,
                        evidence_id=evidence_id
                    )
                enhanced_bgr, audit_rec = enhance_frame_with_audit_and_fallback(
                    raw_bgr,
                    frame_index=f_idx,
                    detector_callable=det_eval,
                    allow_fallback=True
                )
                enhancement_impact_records.append(audit_rec.to_dict())
            else:
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

            active_vehicle_boxes: Dict[str, Tuple[float, float, Tuple[float, float, float, float]]] = {}

            # Manage track entry, best-detection, and vehicle attributes
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

                # Process Vehicle-specific Analytics (ANPR, Color, Model) only for confident detections
                if det.class_name in VEHICLE_CLASSES and det.confidence >= 0.45:
                    collision_detector.record_track_state(
                        track_id=tid,
                        class_name=det.class_name,
                        frame_number=f_idx,
                        timestamp_seconds=t_sec,
                        cx=det.centroid_x,
                        cy=det.centroid_y,
                        bbox=(det.x1, det.y1, det.x2, det.y2)
                    )
                    suspicious_detector.record_movement(
                        track_id=tid,
                        class_name=det.class_name,
                        frame_number=f_idx,
                        timestamp_seconds=t_sec,
                        timestamp_hms=t_hms,
                        cx=det.centroid_x,
                        cy=det.centroid_y
                    )
                    active_vehicle_boxes[tid] = (det.centroid_x, det.centroid_y, (det.x1, det.y1, det.x2, det.y2))

                    # Perform vehicle profiling if unanalyzed or plate not yet resolved
                    need_analysis = (
                        tid not in vehicle_profiles or
                        (vehicle_profiles[tid].license_plate_number is None and det.confidence > 0.55)
                    )
                    if need_analysis:
                        v_prof = vehicle_analyzer.analyze_vehicle(
                            track_id=tid,
                            class_name=det.class_name,
                            frame_bgr=enhanced_bgr,
                            bbox=(det.x1, det.y1, det.x2, det.y2),
                            frame_number=f_idx,
                            timestamp_seconds=t_sec
                        )
                        if tid in vehicle_profiles:
                            v_prof.first_seen_seconds = vehicle_profiles[tid].first_seen_seconds
                            v_prof.total_detections = vehicle_profiles[tid].total_detections + 1
                        vehicle_profiles[tid] = v_prof
                    else:
                        vehicle_profiles[tid].last_seen_seconds = t_sec
                        vehicle_profiles[tid].total_detections += 1

            # Check frame-level collision incidents
            new_collisions = collision_detector.evaluate_frame(
                active_vehicle_tracks=active_vehicle_boxes,
                frame_number=f_idx,
                timestamp_seconds=t_sec,
                timestamp_hms=t_hms
            )
            # Note: Collisions and heading alerts are handled in separate incident telemetry,
            # while event_extractor generates strictly objective, low-risk events as requested.

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

            # Step 13.5: Update virtual tripwire line crossing & In/Out telemetry
            line_crossing_counter.update_tracks(
                active_detections=tracked_detections,
                frame_w=raw_bgr.shape[1],
                frame_h=raw_bgr.shape[0],
                frame_number=f_idx,
                timestamp_seconds=t_sec,
                timestamp_hms=t_hms
            )

            # Step 14: Render derived visualization overlay with vehicle attributes & alerts
            annotated_frame = draw_detection_overlay(
                frame_bgr=enhanced_bgr,
                detections=tracked_detections,
                timestamp_hms=t_hms,
                roi_polygon=roi_polygon,
                vehicle_profiles=vehicle_profiles,
                crashed_track_ids=collision_detector.get_crashed_track_ids(),
                suspicious_track_ids=suspicious_detector.flagged_activities,
                line_crossing_counter=line_crossing_counter,
                overlay_style="reference_mot"
            )
            annotated_frames.append(annotated_frame)
            all_detections.extend(tracked_detections)

            # Periodic progress update
            if frame_counter % 20 == 0:
                pct = min(0.75, 0.30 + (frame_counter / 200.0) * 0.45)
                update_progress(pct, f"Processed {frame_counter} frames... (Vehicles: {len(vehicle_profiles)}, Collisions: {len(collision_detector.incidents)})")

        # Save best confidence keyframes for all tracks
        for tid, img in track_best_img.items():
            best_path = keyframes_dir / "best_detections" / f"best_{tid}.jpg"
            cv2.imwrite(str(best_path), img)
            if tid in tracker.active_tracks:
                tracker.active_tracks[tid]["best_keyframe"] = str(best_path)

        # Finalize tracks and evaluate exits
        update_progress(0.80, "Finalizing trajectories and incident analytics...")
        final_tracks = tracker.finalize(min_detections=2 if frame_counter > 2 else 1)
        confirmed_ids = set(final_tracks.keys())
        event_extractor.filter_to_confirmed_tracks(confirmed_ids)
        event_extractor.evaluate_completed_tracks(final_tracks, total_frames=frame_counter)
        events = event_extractor.get_events()

        # Save best and last seen keyframes and attach to tracks
        for tid, t in final_tracks.items():
            best_path = keyframes_dir / "best_detections" / f"best_{tid}.jpg"
            if best_path.exists():
                t.best_keyframe = str(best_path)

            if t.last_keyframe is None and tid in track_best_img:
                exit_path = keyframes_dir / "exits" / f"exit_{tid}_f{t.last_frame}.jpg"
                cv2.imwrite(str(exit_path), track_best_img[tid])
                t.last_keyframe = str(exit_path)

        # Finalize vehicle profiles with incident logs (confirmed tracks only)
        vehicle_profiles = {tid: v for tid, v in vehicle_profiles.items() if tid in confirmed_ids}
        crashed_ids = collision_detector.get_crashed_track_ids()
        all_collisions = collision_detector.get_all_incidents()
        all_susp_alerts = suspicious_detector.get_all_alerts()

        for tid, v_prof in vehicle_profiles.items():
            if tid in crashed_ids:
                v_prof.crash_involved = True
                v_prof.crash_details = [
                    c.description for c in all_collisions
                    if c.primary_track_id == tid or c.secondary_track_id == tid
                ]
            v_prof.suspicious_activities = suspicious_detector.get_track_suspicious_activities(tid)

        # Step 15: Create annotated output video
        update_progress(0.85, "Encoding derived annotated video output...")
        annotated_video_path = annotated_vids_dir / f"{evidence_id}_annotated.mp4"
        if annotated_frames:
            orig_duration = float(metadata.get("duration_seconds", 0.0))
            orig_fps = float(metadata.get("fps", 25.0))
            generate_annotated_video(
                annotated_frames=annotated_frames,
                output_path=annotated_video_path,
                fps=orig_fps if orig_fps > 0 else 25.0,
                target_duration=orig_duration if orig_duration > 0.5 else None
            )
            audit_logger.record_artifact(
                artifact_id=f"ART-VID-{evidence_id}",
                run_id=run_id,
                artifact_type="ANNOTATED_VIDEO",
                artifact_path=str(annotated_video_path)
            )

        # Step 16: Export CSV, JSON logs, vehicle registry, and summary dossier
        update_progress(0.92, "Exporting structured detection logs, vehicle registry, CSVs, and dossier...")
        metadata["processing_finish_time"] = datetime.now(timezone.utc).isoformat()
        audit_summary = audit_logger.get_run_audit_summary(run_id)

        exported_files = export_cctv_artifacts(
            results_dir=results_base,
            evidence_id=evidence_id,
            metadata=metadata,
            detections=all_detections,
            tracks=final_tracks,
            events=events,
            audit_summary=audit_summary,
            vehicles=[v.to_dict() for v in vehicle_profiles.values()],
            collisions=[c.to_dict() for c in all_collisions],
            suspicious_alerts=[a.to_dict() for a in all_susp_alerts]
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
        update_progress(1.0, "CCTV forensic video analysis & vehicle incident extraction complete.")

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
            "vehicles_csv_path": str(exported_files["vehicles_csv"]),
            "collisions_csv_path": str(exported_files["collisions_csv"]),
            "suspicious_csv_path": str(exported_files["suspicious_csv"]),
            "events_json_path": str(exported_files["events_json"]),
            "summary_json_path": str(exported_files["summary_json"]),
            "report_md_path": str(exported_files["report_md"]),
            "audit_log_json_path": str(exported_files["audit_log_json"]),
            "total_frames_processed": frame_counter,
            "total_detections": len(all_detections),
            "total_tracks": len(final_tracks),
            "total_vehicles": len(vehicle_profiles),
            "total_collisions": len(all_collisions),
            "total_suspicious_alerts": len(all_susp_alerts),
            "total_events": len(events),
            "vehicles": [v.to_dict() for v in vehicle_profiles.values()],
            "collisions": [c.to_dict() for c in all_collisions],
            "suspicious_activities": [a.to_dict() for a in all_susp_alerts],
            "events": [e.to_dict() for e in events],
            "tracks": [t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in final_tracks.values()],
            "overview_keyframes": overview_keyframes[:10],
            "line_crossing_summary": line_crossing_counter.get_summary(),
            "enhancement_impact_audit": enhancement_impact_records[:50],
            "enhancement_utility_summary": {
                "total_audited": len(enhancement_impact_records),
                "fallbacks_triggered": len([r for r in enhancement_impact_records if r.get("action_taken") == "fallback_to_raw"]),
                "bypassed_clean": len([r for r in enhancement_impact_records if r.get("action_taken") == "bypassed_clean"]),
                "targeted_enhanced": len([r for r in enhancement_impact_records if r.get("action_taken") == "enhanced_targeted"]),
            },
            "derived_label": (
                DERIVED_FRAME_LABEL + " [FORENSIC NOTICE: Super-resolution generated textures (REDS/RealBasicVSR) are investigative hypotheses and not verified proof]."
                if ("reds" in str(enhancement_mode).lower() or "sr" in str(enhancement_mode).lower())
                else DERIVED_FRAME_LABEL
            )
        }

    except Exception as e:
        logger.error(f"Pipeline failure: {e}", exc_info=True)
        audit_logger.record_run_finish(run_id=run_id, status="FAILED", error_message=str(e))
        raise
