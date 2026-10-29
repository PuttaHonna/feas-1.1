"""
Unit tests for CCTV Virtual Tripwire, In/Out Line-Crossing Counter, and Reference MOT Visuals.
"""

import numpy as np
import pytest

from src.cctv.line_crossing import LineCrossingCounter, CrossingDirection
from src.cctv.detector import Detection
from src.cctv.annotated_video import draw_detection_overlay


def test_line_crossing_vertical_tripwire_in_and_out():
    """Test line crossing detection for objects moving across a vertical tripwire."""
    counter = LineCrossingCounter(default_x_ratio=0.70)
    w, h = 1000, 800
    line_x = int(w * 0.70)  # 700

    # Frame 1: Person at x=650 (Left / Side A of line at 700)
    det_f1 = Detection(
        frame_number=1,
        timestamp_seconds=1.0,
        timestamp_hms="00:00:01",
        class_name="person",
        class_id=0,
        confidence=0.88,
        x1=630, y1=300, x2=670, y2=500,
        width=40, height=200,
        centroid_x=650, centroid_y=400,
        track_id="person_01",
        track_number=102
    )
    events_f1 = counter.update_tracks([det_f1], w, h, frame_number=1, timestamp_seconds=1.0, timestamp_hms="00:00:01")
    assert len(events_f1) == 0
    assert counter.in_count == 0
    assert counter.out_count == 0

    # Frame 2: Person moves across line to x=740 (Right / Side B)
    det_f2 = Detection(
        frame_number=2,
        timestamp_seconds=1.04,
        timestamp_hms="00:00:01",
        class_name="person",
        class_id=0,
        confidence=0.89,
        x1=720, y1=300, x2=760, y2=500,
        width=40, height=200,
        centroid_x=740, centroid_y=400,
        track_id="person_01",
        track_number=102
    )
    events_f2 = counter.update_tracks([det_f2], w, h, frame_number=2, timestamp_seconds=1.04, timestamp_hms="00:00:01")
    assert len(events_f2) == 1
    assert events_f2[0].direction == CrossingDirection.OUT
    assert counter.out_count == 1
    assert counter.in_count == 0
    assert events_f2[0].track_number == 102

    # Frame 3: Another person moves from Right (x=750) to Left (x=640) -> IN crossing
    det_in_f1 = Detection(
        frame_number=3,
        timestamp_seconds=2.0,
        timestamp_hms="00:00:02",
        class_name="person",
        class_id=0,
        confidence=0.85,
        x1=730, y1=200, x2=770, y2=400,
        width=40, height=200,
        centroid_x=750, centroid_y=300,
        track_id="person_02",
        track_number=71
    )
    counter.update_tracks([det_in_f1], w, h, frame_number=3, timestamp_seconds=2.0, timestamp_hms="00:00:02")

    det_in_f2 = Detection(
        frame_number=4,
        timestamp_seconds=2.04,
        timestamp_hms="00:00:02",
        class_name="person",
        class_id=0,
        confidence=0.86,
        x1=620, y1=200, x2=660, y2=400,
        width=40, height=200,
        centroid_x=640, centroid_y=300,
        track_id="person_02",
        track_number=71
    )
    events_in = counter.update_tracks([det_in_f2], w, h, frame_number=4, timestamp_seconds=2.04, timestamp_hms="00:00:02")
    assert len(events_in) == 1
    assert events_in[0].direction == CrossingDirection.IN
    assert counter.in_count == 1
    assert counter.out_count == 1


def test_reference_mot_overlay_rendering():
    """Verify reference MOT style with red box, dual badges, counter box, and direction vectors."""
    frame = np.full((480, 640, 3), 150, dtype=np.uint8)
    counter = LineCrossingCounter(default_x_ratio=0.70)
    counter.out_count = 4
    counter.in_count = 0
    counter.track_vectors["person_01"] = (12.0, 2.0, 12.16, 9.4)

    det = Detection(
        frame_number=10,
        timestamp_seconds=1.0,
        timestamp_hms="00:00:01",
        class_name="person",
        class_id=0,
        confidence=0.91,
        x1=150, y1=100, x2=220, y2=320,
        width=70, height=220,
        centroid_x=185, centroid_y=210,
        track_id="person_01",
        track_number=102
    )

    annotated = draw_detection_overlay(
        frame_bgr=frame,
        detections=[det],
        timestamp_hms="00:00:01",
        line_crossing_counter=counter,
        overlay_style="reference_mot"
    )

    assert annotated.shape == frame.shape
    assert annotated.dtype == np.uint8
    # Frame has been modified with annotations
    assert not np.array_equal(annotated, frame)


def test_summary_telemetry():
    """Verify get_summary() produces structured telemetry."""
    counter = LineCrossingCounter()
    counter.in_count = 2
    counter.out_count = 5
    summary = counter.get_summary()

    assert summary["in_count"] == 2
    assert summary["out_count"] == 5
    assert summary["total_crossings"] == 7
    assert "events" in summary
