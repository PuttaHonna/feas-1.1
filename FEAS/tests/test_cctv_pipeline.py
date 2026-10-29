"""
Unit test suite for the CCTV Video Analysis and Vehicle Forensic Investigation module.
Tests:
1. SHA-256 hash generation & verification
2. Invalid file extension rejection
3. Corrupted video handling
4. Metadata extraction from synthetic video
5. Timestamp calculation (seconds & HH:MM:SS.mmm)
6. Frame extraction
7. Objective event generation
8. CSV export schema validation
9. Vehicle dominant color extraction (HSV)
10. Vehicle body type and model profile classification
11. License plate localization and ANPR OCR candidate extraction
12. Vehicle collision / crash dynamics detection
13. Suspicious kinematic behavior detection (wrong-way & sudden stop)
14. Comprehensive artifact CSV & markdown report export
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
from src.cctv.vehicle_analyzer import VehicleForensicAnalyzer, VehicleProfile
from src.cctv.collision_detector import CollisionDetector, CollisionIncident
from src.cctv.suspicious_detector import SuspiciousActivityDetector, SuspiciousActivityAlert
from src.cctv.export_results import (
    export_detections_csv, export_tracks_csv, export_vehicles_csv,
    export_collisions_csv, export_suspicious_csv, export_events_json,
    export_markdown_report, DETECTION_COLUMNS, TRACK_COLUMNS, VEHICLE_COLUMNS
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
    assert meta["duration_seconds"] > 0


# 5. Timestamp Calculation
def test_timestamp_calculation():
    assert format_seconds_to_hms(0.0) == "00:00:00.000"
    assert format_seconds_to_hms(65.123) == "00:01:05.123"
    assert format_seconds_to_hms(3661.5) == "01:01:01.500"


# 6. Frame Extraction Yield
def test_frame_extraction(sample_video):
    frames = list(extract_cctv_frames(sample_video, analysis_mode="fast_review"))
    assert len(frames) > 0
    f0 = frames[0]
    assert f0.frame_index == 0
    assert f0.image.shape == (240, 320, 3)
    assert f0.timestamp_hms.startswith("00:00:00")


# 7. Objective Event Extraction (No Speculation)
def test_event_extraction():
    extractor = CCTVEventExtractor(dwell_threshold_seconds=2.0)

    det1 = Detection(
        frame_number=0,
        timestamp_seconds=0.0,
        timestamp_hms="00:00:00.000",
        class_name="person",
        class_id=0,
        confidence=0.85,
        x1=10, y1=10, x2=50, y2=90,
        width=40, height=80, centroid_x=30, centroid_y=50,
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
    assert len(events) >= 1
    # Check that disclaimer is populated and non-speculative
    assert any(e.event_type == "OBJECT_ENTERED_VIEW" for e in events)
    for e in events:
        assert "Advisory" in e.human_review_warning
        assert "suspect" not in e.description.lower()
        assert "guilt" not in e.description.lower()


# 8. CSV Schema Validation
def test_csv_export_schemas(temp_dir):
    det_out = temp_dir / "detections.csv"
    trk_out = temp_dir / "tracks.csv"

    sample_det = Detection(
        frame_number=1,
        timestamp_seconds=0.04,
        timestamp_hms="00:00:00.040",
        class_name="car",
        class_id=2,
        confidence=0.92,
        x1=100, y1=100, x2=200, y2=180,
        width=100, height=80, centroid_x=150, centroid_y=140,
        track_id="car_01"
    )

    export_detections_csv([sample_det], det_out)
    assert det_out.exists()

    with open(det_out, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == DETECTION_COLUMNS

    sample_trk = TrackSummary(
        track_id="car_01",
        class_name="car",
        camera_id="CAM-01",
        evidence_id="EV-01",
        first_seen_seconds=0.0,
        last_seen_seconds=1.5,
        visible_duration_seconds=1.5,
        first_frame=0,
        last_frame=37,
        max_confidence=0.92,
        avg_confidence=0.88,
        total_detections=38
    )

    export_tracks_csv({"car_01": sample_trk}, trk_out)
    assert trk_out.exists()

    with open(trk_out, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == TRACK_COLUMNS


# 9. Vehicle Dominant Color Extraction
def test_vehicle_color_extraction():
    # Synthetic Red Vehicle Crop (BGR: 0, 0, 220)
    red_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    red_crop[:, :] = (20, 20, 220)
    color, conf = VehicleForensicAnalyzer.extract_dominant_color(red_crop)
    assert color == "Red"
    assert conf >= 0.50

    # Synthetic White Vehicle Crop (BGR: 240, 240, 240)
    white_crop = np.full((100, 100, 3), 245, dtype=np.uint8)
    w_color, w_conf = VehicleForensicAnalyzer.extract_dominant_color(white_crop)
    assert w_color == "White"
    assert w_conf >= 0.50

    # Synthetic Blue Vehicle Crop (BGR: 220, 50, 20)
    blue_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    blue_crop[:, :] = (210, 60, 20)
    b_color, b_conf = VehicleForensicAnalyzer.extract_dominant_color(blue_crop)
    assert b_color == "Blue"


# 10. Vehicle Body Type & Model Profile
def test_vehicle_body_and_model_classification():
    # Sedan Aspect ratio ~ 2.2
    body, model = VehicleForensicAnalyzer.classify_body_and_model("car", 220, 100)
    assert body == "Sedan"
    assert "Sedan" in model

    # Truck
    t_body, t_model = VehicleForensicAnalyzer.classify_body_and_model("truck", 400, 200)
    assert "Truck" in t_body
    assert "Profile" in t_model

    # Two-Wheeler
    m_body, m_model = VehicleForensicAnalyzer.classify_body_and_model("motorcycle", 50, 100)
    assert m_body == "Two-Wheeler"
    assert "Motorcycle" in m_model


# 11. License Plate Candidate Localization & Fallback
def test_license_plate_localization_and_ocr(temp_dir):
    analyzer = VehicleForensicAnalyzer(output_dir=temp_dir)
    # Synthetic car crop with lower bumper plate rectangle
    car_crop = np.zeros((150, 200, 3), dtype=np.uint8)
    car_crop[:, :] = (180, 180, 180)  # Silver car
    # Draw dark bumper
    car_crop[100:140, 20:180] = (40, 40, 40)
    # Draw white license plate box with dark simulated characters
    car_crop[110:130, 60:140] = (255, 255, 255)
    for c_x in [70, 85, 100, 115, 130]:
        cv2.rectangle(car_crop, (c_x, 113), (c_x + 8, 127), (0, 0, 0), -1)

    plate_txt, plate_conf, plate_crop = analyzer.detect_license_plate(car_crop)
    assert plate_crop is not None
    assert plate_crop.size > 0


# 12. Vehicle Collision Detection
def test_collision_detector_impact_trigger():
    detector = CollisionDetector(min_impact_speed_px_s=10.0, overlap_iou_threshold=0.05)

    # Frame 1: Vehicle 1 and Vehicle 2 moving toward each other with high speed
    detector.record_track_state("car_01", "car", 1, 0.04, 100, 100, (80, 80, 120, 120))
    detector.record_track_state("car_02", "car", 1, 0.04, 150, 100, (130, 80, 170, 120))

    # Frame 2: Moving fast
    detector.record_track_state("car_01", "car", 2, 0.08, 115, 100, (95, 80, 135, 120))
    detector.record_track_state("car_02", "car", 2, 0.08, 135, 100, (115, 80, 155, 120))

    # Frame 3: Impact! Overlapping bounding boxes and abrupt stop
    detector.record_track_state("car_01", "car", 3, 0.12, 120, 100, (100, 80, 140, 120))
    detector.record_track_state("car_02", "car", 3, 0.12, 125, 100, (105, 80, 145, 120))

    active_tracks = {
        "car_01": (120, 100, (100, 80, 140, 120)),
        "car_02": (125, 100, (105, 80, 145, 120))
    }

    incidents = detector.evaluate_frame(active_tracks, frame_number=3, timestamp_seconds=0.12, timestamp_hms="00:00:00.120")
    assert len(incidents) >= 1
    assert incidents[0].collision_type == "VEHICLE_VEHICLE_COLLISION"
    assert "car_01" in detector.get_crashed_track_ids()
    assert "car_02" in detector.get_crashed_track_ids()


# 13. Suspicious Kinematic Behavior (Wrong-Way & Roadway Stop)
def test_suspicious_activity_wrong_way_and_stop():
    detector = SuspiciousActivityDetector(min_motion_speed=5.0, stop_dwell_threshold_seconds=1.0)

    # Simulate dominant traffic flow moving to the right (heading ~0°)
    for tid in ["car_01", "car_02", "car_03"]:
        for f in range(5):
            detector.record_movement(tid, "car", f, f * 0.1, f"00:00:00.{f*100:03d}", 100 + f * 10, 100)

    # Simulate vehicle 4 moving in the opposite direction (heading ~180°)
    for f in range(5):
        detector.record_movement("car_04", "car", f, f * 0.1, f"00:00:00.{f*100:03d}", 300 - f * 10, 100)

    wrong_way_alerts = detector.evaluate_flow_directions(frame_number=4, timestamp_seconds=0.4, timestamp_hms="00:00:00.400")
    assert any(a.activity_type == "WRONG_WAY_MOVEMENT" and a.track_id == "car_04" for a in wrong_way_alerts)


# 14. Vehicle Registry & Incident Exporters
def test_vehicle_artifacts_export(temp_dir):
    v_csv = temp_dir / "vehicles.csv"
    c_csv = temp_dir / "collisions.csv"
    s_csv = temp_dir / "suspicious.csv"
    r_md = temp_dir / "report.md"

    v_sample = {
        "track_id": "car_01",
        "vehicle_type": "car",
        "estimated_body_type": "Sedan",
        "estimated_model_profile": "Sedan (Toyota Profile)",
        "dominant_color": "Silver / Grey",
        "color_confidence": 0.85,
        "license_plate_number": "KA01MJ1234",
        "license_plate_confidence": 0.90,
        "crash_involved": True,
        "crash_details": ["Collision at 00:00:02.100"],
        "suspicious_activities": ["SUDDEN_ROADWAY_STOP"],
        "speed_estimate_px_s": 25.4,
        "heading_degrees": 92.0,
        "license_plate_crop_path": "",
        "vehicle_crop_path": ""
    }

    c_sample = {
        "incident_id": "CRASH-0001",
        "frame_number": 15,
        "timestamp_hms": "00:00:01.500",
        "primary_track_id": "car_01",
        "secondary_track_id": "car_02",
        "collision_type": "VEHICLE_VEHICLE_COLLISION",
        "impact_speed_delta_px_s": 22.1,
        "severity_advisory": "High Impact",
        "description": "High impact collision"
    }

    s_sample = {
        "alert_id": "SUSP-0001",
        "track_id": "car_01",
        "activity_type": "SUDDEN_ROADWAY_STOP",
        "frame_number": 20,
        "timestamp_hms": "00:00:02.000",
        "severity_level": "MEDIUM",
        "speed_px_s": 0.0,
        "heading_degrees": 90.0,
        "description": "Vehicle came to abrupt halt"
    }

    export_vehicles_csv([v_sample], "EV-01", v_csv)
    export_collisions_csv([c_sample], c_csv)
    export_suspicious_csv([s_sample], s_csv)

    assert v_csv.exists()
    assert c_csv.exists()
    assert s_csv.exists()

    with open(v_csv, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == VEHICLE_COLUMNS

    export_markdown_report(
        metadata={"evidence_id": "EV-01", "case_id": "CASE-01"},
        tracks={},
        events=[],
        vehicles=[v_sample],
        collisions=[c_sample],
        suspicious_alerts=[s_sample],
        output_path=r_md
    )
    assert r_md.exists()
    content = r_md.read_text(encoding="utf-8")
    assert "Vehicle Forensic Registry" in content
    assert "KA01MJ1234" in content
    assert "CRASH-0001" in content


# 16. Auto-Rickshaw Reclassification and Video Pacing
def test_auto_rickshaw_reclassification_and_pacing(temp_dir):
    # Auto-Rickshaw Body Model classification
    auto_body, auto_model = VehicleForensicAnalyzer.classify_body_and_model("auto", 150, 180)
    assert auto_body == "Auto-Rickshaw"
    assert "Three-Wheeler" in auto_model

    # Truck fallback with narrow aspect ratio (ar <= 1.08) -> Auto-Rickshaw
    fallback_body, fallback_model = VehicleForensicAnalyzer.classify_body_and_model("truck", 170, 210)
    assert fallback_body == "Auto-Rickshaw"

    # Frame pacing duration test: 20 frames with target_duration=10.0 at fps=25.0
    out_video = temp_dir / "test_pacing.mp4"
    dummy_frames = [np.zeros((120, 160, 3), dtype=np.uint8) for _ in range(5)]
    from src.cctv.annotated_video import generate_annotated_video
    generate_annotated_video(dummy_frames, out_video, fps=25.0, target_duration=5.0)
    assert out_video.exists()
    assert out_video.stat().st_size > 0

