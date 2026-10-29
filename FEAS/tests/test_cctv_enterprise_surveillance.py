"""
Unit & Integration Test Suite for Enterprise CCTV Surveillance Modules.
========================================================================
Tests:
- TripwireZoneService (crossing cross-products and polygon point-in-polygon tests)
- LoiteringDetector (dwell thresholds and alert triggers)
- UnattendedBaggageDetector (stationary displacement and owner proximity detachment)
- CCTVHeatmapGenerator (spatial Gaussian accumulation and overlay image rendering)
- CameraTamperDetector (MOG2 motion ratio, lens occlusion, and lighting transitions)
- CCTVSearchEngine (natural query parser and attribute filtering)
"""

import numpy as np
import pytest
from pathlib import Path

from src.cctv.tripwire_zone_service import TripwireZoneService, ZoneDefinition, TripwireDefinition
from src.cctv.loitering_service import LoiteringDetector
from src.cctv.stationary_object_service import UnattendedBaggageDetector
from src.cctv.heatmap_service import CCTVHeatmapGenerator
from src.cctv.camera_tamper_service import CameraTamperDetector
from src.cctv.cctv_search_service import CCTVSearchEngine, SearchQuery, extract_dominant_color


def test_tripwire_crossing_detection():
    service = TripwireZoneService(
        tripwires=[TripwireDefinition(tripwire_id="TW-01", name="Entry Gate", pt1=(100, 0), pt2=(100, 500))]
    )
    # Track moving from x=80 (side A) to x=120 (side B) across vertical tripwire at x=100
    alert1, cross1 = service.process_track(
        track_id="person_01",
        track_number=1,
        class_name="person",
        centroid=(80.0, 250.0),
        bbox=(60, 200, 100, 300),
        frame_number=1,
        timestamp_seconds=1.0
    )
    assert len(cross1) == 0

    alert2, cross2 = service.process_track(
        track_id="person_01",
        track_number=1,
        class_name="person",
        centroid=(120.0, 250.0),
        bbox=(100, 200, 140, 300),
        frame_number=20,
        timestamp_seconds=2.0
    )
    assert len(cross2) == 1
    assert cross2[0].direction.value in ("ENTRY", "EXIT")
    assert service.crossing_counts["TW-01"]["ENTRY"] + service.crossing_counts["TW-01"]["EXIT"] == 1


def test_zone_perimeter_intrusion():
    # Define rectangular perimeter zone [200, 200] to [400, 400]
    zone = ZoneDefinition(
        zone_id="ZONE-VAULT",
        name="Vault Area",
        polygon=[(200, 200), (400, 200), (400, 400), (200, 400)],
        zone_type="restricted"
    )
    service = TripwireZoneService(zones=[zone])

    # Centroid outside zone at (100, 100)
    alerts1, _ = service.process_track("person_02", 2, "person", (100, 100), (90, 80, 110, 120), 1, 1.0)
    assert len(alerts1) == 0

    # Centroid inside zone at (300, 300) -> triggers intrusion
    alerts2, _ = service.process_track("person_02", 2, "person", (300, 300), (290, 280, 310, 320), 2, 2.0)
    assert len(alerts2) == 1
    assert alerts2[0].zone_id == "ZONE-VAULT"
    assert alerts2[0].severity == "CRITICAL"


def test_loitering_detector():
    detector = LoiteringDetector(dwell_threshold_seconds=10.0)

    # Enters at t=0
    a1 = detector.update_track_state(
        "ZONE-LOBBY", "Lobby", True, "person_03", 3, "person", (150, 150), (140, 130, 160, 170), 1, 0.0
    )
    assert a1 is None

    # Still inside at t=5s (below threshold)
    a2 = detector.update_track_state(
        "ZONE-LOBBY", "Lobby", True, "person_03", 3, "person", (152, 151), (140, 130, 160, 170), 5, 5.0
    )
    assert a2 is None

    # Exceeds 10s at t=12s -> Loitering alert
    a3 = detector.update_track_state(
        "ZONE-LOBBY", "Lobby", True, "person_03", 3, "person", (153, 152), (140, 130, 160, 170), 12, 12.0
    )
    assert a3 is not None
    assert a3.alert_id.startswith("ALT-LOITER")
    assert a3.dwell_duration_seconds >= 10.0


def test_unattended_baggage_detector():
    detector = UnattendedBaggageDetector(
        stationary_time_threshold_seconds=5.0,
        abandonment_distance_px=50.0
    )

    # Initial lock at t=0
    alerts0 = detector.evaluate_frame(
        baggage_detections=[{"track_id": "bag_01", "class_name": "backpack", "centroid": (200, 200), "bbox": (180, 180, 220, 220)}],
        person_centroids=[(210, 210)],  # Owner right beside bag
        frame_number=1,
        timestamp_s=0.0
    )
    assert len(alerts0) == 0

    # At t=6s, person has walked away to (400, 400), bag remains stationary
    alerts1 = detector.evaluate_frame(
        baggage_detections=[{"track_id": "bag_01", "class_name": "backpack", "centroid": (201, 201), "bbox": (180, 180, 220, 220)}],
        person_centroids=[(400, 400)],  # Distance = 282px > 50px
        frame_number=6,
        timestamp_s=6.0
    )
    assert len(alerts1) == 1
    assert alerts1[0].object_class == "backpack"
    assert alerts1[0].severity == "CRITICAL"


def test_heatmap_generation(tmp_path: Path):
    generator = CCTVHeatmapGenerator(frame_width=640, frame_height=480)
    for _ in range(30):
        generator.add_point(320, 240, weight=1.0)

    summary = generator.save_heatmap(tmp_path / "test_density.jpg")
    assert summary.total_samples == 30
    assert summary.peak_density_value > 0
    assert Path(summary.output_image_path).exists()


def test_camera_tamper_detection():
    detector = CameraTamperDetector(occlusion_variance_thresh=10.0)

    # Normal diverse texture frame
    normal_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    for f in range(6):
        detector.process_frame(normal_frame, f, float(f))

    # Occluded lens frame (e.g. solid black / covered with cloth)
    black_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    _, alert = detector.process_frame(black_frame, 7, 7.0)
    assert alert is not None
    assert alert.tamper_type == "OCCLUSION_BLIND"


def test_cctv_search_engine():
    tracks = [
        {"track_id": "car_01", "class": "car", "color": "red", "first_seen_timestamp": "5.0s", "last_seen_timestamp": "25.0s"},
        {"track_id": "person_01", "class": "person", "color": "blue", "first_seen_timestamp": "1.0s", "last_seen_timestamp": "10.0s"}
    ]
    events = [
        {"event_id": "EVT-1", "event_type": "LOITERING", "timestamp_seconds": 15.0}
    ]
    engine = CCTVSearchEngine(tracks=tracks, events=events)

    # Natural query "red car"
    q1 = engine.parse_natural_query("red car")
    res1 = engine.search_tracks(q1)
    assert len(res1) == 1
    assert res1[0]["track_id"] == "car_01"

    # Search event "loitering"
    q2 = engine.parse_natural_query("show loitering events")
    res2 = engine.search_events(q2)
    assert len(res2) == 1
    assert res2[0]["event_id"] == "EVT-1"

