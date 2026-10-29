"""
CCTV Stationary Object & Unattended Baggage Service.
===================================================
Detects static items (backpacks, suitcases, parcels, boxes) that remain stationary (zero displacement)
while the associated owner/person departs the vicinity, flagging security abandonment risks.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
import math
import numpy as np


@dataclass
class UnattendedObjectAlert:
    """Alert emitted when baggage/item is left stationary without a nearby owner."""
    alert_id: str
    track_id: str
    object_class: str
    stationary_duration_seconds: float
    distance_to_nearest_person_px: float
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    centroid: Tuple[float, float]
    bounding_box: Tuple[float, float, float, float]
    severity: str = "CRITICAL"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UnattendedBaggageDetector:
    """
    Analyzes item displacement kinematics and proximity to person tracks.
    """

    BAGGAGE_CLASSES: Set[str] = {
        "backpack", "suitcase", "handbag", "bag", "package", "box", "unattended_bag"
    }

    def __init__(
        self,
        stationary_time_threshold_seconds: float = 30.0,
        max_displacement_px: float = 12.0,
        abandonment_distance_px: float = 150.0
    ):
        self.stationary_threshold = stationary_time_threshold_seconds
        self.max_displacement = max_displacement_px
        self.abandonment_distance = abandonment_distance_px

        # track_id -> (start_stationary_timestamp, initial_centroid_x, initial_centroid_y)
        self._stationary_since: Dict[str, Tuple[float, float, float]] = {}
        self._alert_fired: Set[str] = set()

        self.alerts: List[UnattendedObjectAlert] = []
        self._counter = 0

    @staticmethod
    def _euclidean_dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def evaluate_frame(
        self,
        baggage_detections: List[Dict[str, Any]],
        person_centroids: List[Tuple[float, float]],
        frame_number: int,
        timestamp_s: float
    ) -> List[UnattendedObjectAlert]:
        """
        Evaluate all candidate baggage detections in the frame against person proximity.
        
        Args:
            baggage_detections: list of dicts with keys: 'track_id', 'class_name', 'centroid', 'bbox'
            person_centroids: list of (x, y) coordinates for all active person tracks
            frame_number: current video frame index
            timestamp_s: current timestamp in seconds
        """
        new_alerts: List[UnattendedObjectAlert] = []

        for item in baggage_detections:
            tid = item["track_id"]
            cls_name = item["class_name"].lower()
            cx, cy = item["centroid"]
            bbox = item["bbox"]

            if cls_name not in self.BAGGAGE_CLASSES:
                continue

            # Check if stationary compared to initial lock
            if tid not in self._stationary_since:
                self._stationary_since[tid] = (timestamp_s, cx, cy)
            else:
                start_ts, init_x, init_y = self._stationary_since[tid]
                displacement = self._euclidean_dist((cx, cy), (init_x, init_y))

                if displacement > self.max_displacement:
                    # Object moved, reset stationary timer
                    self._stationary_since[tid] = (timestamp_s, cx, cy)
                    self._alert_fired.discard(tid)
                    continue

                duration = timestamp_s - start_ts

                # Check proximity to all active persons
                min_dist_to_person = float("inf")
                if person_centroids:
                    min_dist_to_person = min(
                        self._euclidean_dist((cx, cy), p) for p in person_centroids
                    )

                # Trigger alert if stationary > threshold and owner is far away
                if (
                    duration >= self.stationary_threshold
                    and min_dist_to_person > self.abandonment_distance
                    and tid not in self._alert_fired
                ):
                    self._counter += 1
                    self._alert_fired.add(tid)
                    alert_id = f"ALT-ABANDON-{self._counter:04d}"
                    hms = f"{int(timestamp_s // 3600):02d}:{int((timestamp_s % 3600) // 60):02d}:{timestamp_s % 60:05.2f}"

                    alert = UnattendedObjectAlert(
                        alert_id=alert_id,
                        track_id=tid,
                        object_class=cls_name,
                        stationary_duration_seconds=round(duration, 1),
                        distance_to_nearest_person_px=round(min_dist_to_person, 1),
                        frame_number=frame_number,
                        timestamp_seconds=round(timestamp_s, 2),
                        timestamp_hms=hms,
                        centroid=(round(cx, 1), round(cy, 1)),
                        bounding_box=tuple(round(v, 1) for v in bbox),
                        severity="CRITICAL",
                        description=f"Stationary {cls_name} ({tid}) unattended for {int(duration)}s (nearest person: {int(min_dist_to_person)}px)"
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)

        return new_alerts

