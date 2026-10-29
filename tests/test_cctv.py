"""
Unit and integration tests for Module 2: CCTV Video Enhancement, Detection, and Tracking.
"""

from pathlib import Path
import pytest
import cv2
import numpy as np

from src.cctv.enhancement import enhance_frame
from src.cctv.tracker import ForensicTracker, calculate_iou
from src.cctv.events import ObjectiveEventExtractor
from src.cctv.pipeline import run_cctv_pipeline
from src.common.audit_db import AuditDatabase


def test_enhancement_and_forensic_banner():
    arr = np.full((100, 100, 3), 120, dtype=np.uint8)
    enhanced = enhance_frame(
        arr,
        gamma=1.2,
        enable_clahe=True,
        enable_denoise=True,
        enable_sharpen=True,
        add_banner=True,
    )
    # Banner increases height
    assert enhanced.shape[0] > 100
    assert enhanced.shape[1] == 100
    assert enhanced.dtype == np.uint8


def test_iou_and_tracking():
    box1 = [10.0, 10.0, 50.0, 50.0]
    box2 = [10.0, 10.0, 50.0, 50.0]
    box3 = [100.0, 100.0, 150.0, 150.0]

    assert calculate_iou(box1, box2) == 1.0
    assert calculate_iou(box1, box3) == 0.0

    tracker = ForensicTracker(iou_threshold=0.3)

    # Frame 1
    dets_f1 = [{"class_name": "person", "confidence": 0.85, "bbox": [10.0, 10.0, 50.0, 50.0]}]
    t1 = tracker.update(dets_f1, frame_idx=0, timestamp_sec=0.0)
    assert len(t1) == 1
    assert t1[0]["track_id"] == 1

    # Frame 2: slightly moved person
    dets_f2 = [{"class_name": "person", "confidence": 0.87, "bbox": [12.0, 12.0, 52.0, 52.0]}]
    t2 = tracker.update(dets_f2, frame_idx=1, timestamp_sec=0.1)
    assert len(t2) == 1
    assert t2[0]["track_id"] == 1  # Retains track ID 1

    # Frame 3: second object appears
    dets_f3 = [
        {"class_name": "person", "confidence": 0.86, "bbox": [14.0, 14.0, 54.0, 54.0]},
        {"class_name": "car", "confidence": 0.90, "bbox": [100.0, 100.0, 200.0, 180.0]},
    ]
    t3 = tracker.update(dets_f3, frame_idx=2, timestamp_sec=0.2)
    assert len(t3) == 2
    track_ids = {item["track_id"] for item in t3}
    assert 1 in track_ids
    assert 2 in track_ids


def test_objective_event_extractor():
    roi = [(50, 50), (150, 50), (150, 150), (50, 150)]
    extractor = ObjectiveEventExtractor(
        frame_width=200,
        frame_height=200,
        duration_threshold_sec=1.0,
        roi_polygon=roi,
    )

    # Fake active tracker mock
    active_instances = {
        1: {
            "first_frame": 0,
            "first_timestamp": 0.0,
        }
    }

    # Frame 0: Inside ROI, first detected
    tracks_f0 = [{
        "track_id": 1,
        "class_name": "car",
        "bbox": [60.0, 60.0, 100.0, 100.0],
    }]
    events_f0 = extractor.process_frame(tracks_f0, frame_idx=0, timestamp_sec=0.0, active_tracker_instances=active_instances)
    ev_types = [e["event_type"] for e in events_f0]
    assert "first_detected" in ev_types
    assert "roi_entered" in ev_types

    # Frame 10: at timestamp 1.2s -> duration exceeded
    events_f10 = extractor.process_frame(tracks_f0, frame_idx=10, timestamp_sec=1.2, active_tracker_instances=active_instances)
    assert any(e["event_type"] == "duration_threshold_exceeded" for e in events_f10)


def test_cctv_pipeline_synthetic_video(tmp_path: Path):
    # 1. Create a synthetic MP4 test video
    video_file = tmp_path / "test_surveillance.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 10.0
    w, h = 320, 240
    writer = cv2.VideoWriter(str(video_file), fourcc, fps, (w, h))

    for f in range(12):
        frame = np.full((h, w, 3), 80, dtype=np.uint8)
        # Draw a moving square simulating an object
        x_pos = 20 + f * 10
        cv2.rectangle(frame, (x_pos, 50), (x_pos + 40, 120), (220, 220, 220), -1)
        writer.write(frame)
    writer.release()

    out_dir = tmp_path / "cctv_results"
    db_path = tmp_path / "cctv_test_audit.db"
    db = AuditDatabase(db_path=db_path)

    # Run pipeline on synthetic video (10 frames)
    result = run_cctv_pipeline(
        video_path=video_file,
        output_dir=out_dir,
        audit_db=db,
        max_frames_to_process=10,
    )

    assert result["status"] == "completed"
    assert "evidence_id" in result
    assert "original_sha256" in result
    assert Path(result["artifacts"]["annotated_video"]).exists()
    assert Path(result["artifacts"]["detections_csv"]).exists()
    assert Path(result["artifacts"]["tracks_csv"]).exists()
    assert Path(result["artifacts"]["events_json"]).exists()
    assert result["metrics"]["frames_processed"] == 10

    # Verify audit trail in SQLite
    runs = db.get_run_history(result["evidence_id"])
    assert len(runs) == 1
    assert runs[0]["status"] == "COMPLETED"

    trail = db.get_audit_trail(runs[0]["run_id"])
    assert len(trail) >= 1
    assert any(ev["stage_name"] == "cctv_export" for ev in trail)
