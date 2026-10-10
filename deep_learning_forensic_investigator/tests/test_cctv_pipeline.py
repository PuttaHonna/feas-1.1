"""
Unit test suite for the CCTV Video Analysis module.
Tests:
1. SHA-256 hash generation & verification
2. Invalid file extension rejection
3. Corrupted video handling
4. Metadata extraction from synthetic video
5. Timestamp calculation (seconds & HH:MM:SS.mmm)
6. Frame extraction
7. Objective event generation
8. CSV export schema validation
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
import pytest

from src.cctv.integrity import calculate_file_sha256, verify_sha256
from src.cctv.video_validator import validate_cctv_video
from src.cctv.video_metadata import extract_technical_metadata
from src.cctv.frame_extractor import format_seconds_to_hms, extract_cctv_frames
from src.cctv.detector import Detection
from src.cctv.tracker import CCTVTracker, TrackSummary
from src.cctv.event_extractor import CCTVEventExtractor
from src.cctv.export_results import (
    export_detections_csv, export_tracks_csv, export_events_json,
    DETECTION_COLUMNS, TRACK_COLUMNS
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_video(temp_dir):
    """Generate a clean synthetic 1-second 25fps video for deterministic testing."""
    vid_path = temp_dir / "sample_cctv.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 25.0, (320, 240))
    for i in range(25):
        frame = np.full((240, 320, 3), (i * 10) % 255, dtype=np.uint8)
        # Draw a moving square simulating an object
        cv2.rectangle(frame, (20 + i * 2, 50), (60 + i * 2, 90), (0, 255, 0), -1)
        out.write(frame)
    out.release()
    return vid_path


# 1. SHA-256 Hash Generation & Verification
def test_sha256_generation(temp_dir):
    test_file = temp_dir / "test_data.txt"
    test_file.write_text("Forensic CCTV Evidence Integrity Test", encoding="utf-8")

    hash1 = calculate_file_sha256(test_file)
    assert len(hash1) == 64
    assert verify_sha256(test_file, hash1) is True
    assert verify_sha256(test_file, "0000000000000000000000000000000000000000000000000000000000000000") is False


# 2. Invalid Extension Rejection
def test_invalid_extension_rejection(temp_dir):
    bad_file = temp_dir / "evidence.exe"
    bad_file.write_bytes(b"\x00\x01\x02")

    res = validate_cctv_video(bad_file)
    assert res.is_valid is False
    assert "Unsupported video format" in res.error_message


# 3. Corrupted Video Handling
def test_corrupted_video_handling(temp_dir):
    corrupt_file = temp_dir / "corrupted.mp4"
    corrupt_file.write_bytes(b"NOT_A_VALID_MP4_HEADER_RANDOM_GARBAGE")

    res = validate_cctv_video(corrupt_file)
    assert res.is_valid is False
    assert ("could not open" in res.error_message or "no readable" in res.error_message)


# 4. Metadata Extraction from Sample Video
def test_metadata_extraction(sample_video):
    meta = extract_technical_metadata(
        video_path=sample_video,
        evidence_id="EV-TEST-01",
        case_id="CASE-TEST-01",
        user_metadata={"camera_id": "CAM-TEST"}
    )
    assert meta["evidence_id"] == "EV-TEST-01"
    assert meta["case_id"] == "CASE-TEST-01"
    assert meta["video_width"] == 320
    assert meta["video_height"] == 240
    assert meta["fps"] == 25.0
    assert meta["frame_count"] == 25
    assert len(meta["original_sha256"]) == 64


# 5. Timestamp Calculation
def test_timestamp_calculation():
    assert format_seconds_to_hms(0.0) == "00:00:00.000"
    assert format_seconds_to_hms(65.5) == "00:01:05.500"
    assert format_seconds_to_hms(3661.123) == "01:01:01.123"


# 6. Frame Extraction
def test_frame_extraction(sample_video):
    frames = list(extract_cctv_frames(sample_video, analysis_mode="full_analysis", sampling_step=5))
    assert len(frames) == 5
    for f in frames:
        assert f.image.shape == (240, 320, 3)
        assert f.timestamp_seconds >= 0.0
        assert ":" in f.timestamp_hms


# 7. Event Generation
def test_event_generation():
    extractor = CCTVEventExtractor(dwell_threshold_seconds=2.0)
    det1 = Detection(
        frame_number=0,
        timestamp_seconds=0.0,
        timestamp_hms="00:00:00.000",
        class_name="person",
        class_id=0,
        confidence=0.88,
        x1=10, y1=10, x2=50, y2=80,
        width=40, height=70,
        centroid_x=30, centroid_y=45,
        track_id="person_01"
    )

    extractor.process_frame_detections(
        detections=[det1],
        frame_number=0,
        timestamp_seconds=0.0,
        timestamp_hms="00:00:00.000",
        camera_id="CAM-01"
    )

    events = extractor.get_events()
    event_types = [e.event_type for e in events]
    assert "OBJECT_ENTERED_VIEW" in event_types
    assert "NEW_CLASS_DETECTED" in event_types

    for e in events:
        assert "Advisory research output only" in e.human_review_warning


# 8. CSV Export Schema Validation
def test_csv_export_schema(temp_dir):
    det = Detection(
        frame_number=1,
        timestamp_seconds=0.04,
        timestamp_hms="00:00:00.040",
        class_name="car",
        class_id=2,
        confidence=0.92,
        x1=50, y1=60, x2=150, y2=120,
        width=100, height=60,
        centroid_x=100, centroid_y=90,
        track_id="car_01"
    )
    det_csv = temp_dir / "detections.csv"
    export_detections_csv([det], det_csv)

    with open(det_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == DETECTION_COLUMNS

    track = TrackSummary(
        track_id="car_01",
        class_name="car",
        camera_id="CAM-01",
        evidence_id="EV-01",
        first_seen_seconds=0.0,
        last_seen_seconds=5.0,
        visible_duration_seconds=5.0,
        first_frame=0,
        last_frame=125,
        max_confidence=0.95,
        avg_confidence=0.91,
        total_detections=10
    )
    trk_csv = temp_dir / "tracks.csv"
    export_tracks_csv({"car_01": track}, trk_csv)

    with open(trk_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == TRACK_COLUMNS
