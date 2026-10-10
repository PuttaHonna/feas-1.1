"""
CCTV Vehicle Crash & Collision Incident Detection Module.
Detects potential vehicle-to-vehicle and vehicle-to-barrier collisions:
- Evaluates spatial bounding box overlap and proximity
- Analyzes instantaneous velocity vectors and impact deceleration (delta-V)
- Flags post-collision entanglement or sudden immobilization

Compliance notice:
- Automated advisory heuristic only. Requires expert forensic review.
- Does not assign legal liability or fault.
- Operates strictly on derived working copies.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

CRASH_DISCLAIMER: str = (
    "Automated crash heuristic. Advisory output only; does not establish legal fault "
    "or court admissibility. Must be verified by a qualified collision reconstruction specialist."
)

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}


@dataclass
class CollisionIncident:
    """Represents a discrete detected vehicle crash or impact incident."""
    incident_id: str
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    primary_track_id: str
    secondary_track_id: Optional[str]
    collision_type: str                  # VEHICLE_VEHICLE_COLLISION, VEHICLE_BARRIER_IMPACT
    impact_speed_delta_px_s: float
    description: str
    severity_advisory: str               # High Impact, Moderate Impact, Low Speed Contact
    location_xy: Tuple[float, float]
    advisory_disclaimer: str = CRASH_DISCLAIMER

    def to_dict(self) -> Dict:
        return asdict(self)


class CollisionDetector:
    """Heuristic detector for vehicle collision dynamics in CCTV streams."""

    def __init__(
        self,
        min_impact_speed_px_s: float = 12.0,
        deceleration_ratio_threshold: float = 0.50,
        overlap_iou_threshold: float = 0.05
    ):
        """Initialize collision detector.
        
        Args:
            min_impact_speed_px_s: Minimum pre-impact velocity to be considered a collision candidate.
            deceleration_ratio_threshold: Fraction of speed loss required to indicate impact.
            overlap_iou_threshold: Minimum bounding box IoU indicating vehicle contact.
        """
        self.min_impact_speed = min_impact_speed_px_s
        self.decel_threshold = deceleration_ratio_threshold
        self.iou_threshold = overlap_iou_threshold

        self.incidents: List[CollisionIncident] = []
        self.incident_counter: int = 0
        self.reported_pairs: Set[Tuple[str, str]] = set()

        # Track history cache: track_id -> list of (frame, ts, cx, cy, speed, (x1, y1, x2, y2))
        self.track_histories: Dict[str, List[Tuple[int, float, float, float, float, Tuple[float, float, float, float]]]] = {}

    def _next_incident_id(self) -> str:
        self.incident_counter += 1
        return f"CRASH-{self.incident_counter:04d}"

    @staticmethod
    def _box_iou(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
        x1_a, y1_a, x2_a, y2_a = b1
        x1_b, y1_b, x2_b, y2_b = b2
        x_left = max(x1_a, x1_b)
        y_top = max(y1_a, y1_b)
        x_right = min(x2_a, x2_b)
        y_bottom = min(y2_a, y2_b)
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area_a = max(0.0, (x2_a - x1_a) * (y2_a - y1_a))
        area_b = max(0.0, (x2_b - x1_b) * (y2_b - y1_b))
        union = area_a + area_b - intersection
        return (intersection / union) if union > 0 else 0.0

    def record_track_state(
        self,
        track_id: str,
        class_name: str,
        frame_number: int,
        timestamp_seconds: float,
        cx: float,
        cy: float,
        bbox: Tuple[float, float, float, float]
    ):
        """Append track state and compute instantaneous velocity."""
        if class_name not in VEHICLE_CLASSES:
            return

        if track_id not in self.track_histories:
            self.track_histories[track_id] = []

        history = self.track_histories[track_id]
        speed = 0.0
        if history:
            prev_frame, prev_ts, prev_cx, prev_cy, _, _ = history[-1]
            dt = max(0.001, timestamp_seconds - prev_ts)
            dist = math.hypot(cx - prev_cx, cy - prev_cy)
            speed = dist / dt

        history.append((frame_number, timestamp_seconds, cx, cy, speed, bbox))
        # Keep recent 40 frames for impact window analysis
        if len(history) > 40:
            history.pop(0)

    def evaluate_frame(
        self,
        active_vehicle_tracks: Dict[str, Tuple[float, float, Tuple[float, float, float, float]]],
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str
    ) -> List[CollisionIncident]:
        """Check all active vehicle pairs for collision dynamics.
        
        Args:
            active_vehicle_tracks: track_id -> (cx, cy, (x1, y1, x2, y2))
            frame_number: Current frame index
            timestamp_seconds: Current seconds
            timestamp_hms: HH:MM:SS string
        """
        new_incidents: List[CollisionIncident] = []
        track_ids = list(active_vehicle_tracks.keys())

        # 1. Multi-vehicle collision evaluation
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                t1 = track_ids[i]
                t2 = track_ids[j]

                # Pair key for deduplication
                pair_key = (min(t1, t2), max(t1, t2))
                if pair_key in self.reported_pairs:
                    continue

                cx1, cy1, box1 = active_vehicle_tracks[t1]
                cx2, cy2, box2 = active_vehicle_tracks[t2]

                iou = self._box_iou(box1, box2)
                centroid_dist = math.hypot(cx1 - cx2, cy1 - cy2)

                # Are vehicles in contact or extreme proximity?
                box1_diag = math.hypot(box1[2] - box1[0], box1[3] - box1[1])
                box2_diag = math.hypot(box2[2] - box2[0], box2[3] - box2[1])
                proximity_thresh = (box1_diag + box2_diag) * 0.35

                if iou >= self.iou_threshold or centroid_dist <= proximity_thresh:
                    # Check pre-impact velocity profile of both vehicles
                    h1 = self.track_histories.get(t1, [])
                    h2 = self.track_histories.get(t2, [])

                    speeds1 = [entry[4] for entry in h1[:-1]] if len(h1) >= 2 else ([h1[0][4]] if h1 else [0.0])
                    speeds2 = [entry[4] for entry in h2[:-1]] if len(h2) >= 2 else ([h2[0][4]] if h2 else [0.0])

                    max_pre_speed = max(max(speeds1), max(speeds2))

                    if max_pre_speed >= self.min_impact_speed:
                        # Significant kinetic speed prior to contact
                        curr_speed1 = h1[-1][4] if h1 else 0.0
                        curr_speed2 = h2[-1][4] if h2 else 0.0
                        curr_speed = max(curr_speed1, curr_speed2)

                        delta_v = max_pre_speed - curr_speed

                        # Did velocity drop sharply?
                        if delta_v >= (max_pre_speed * self.decel_threshold) or iou > 0.15:
                            severity = "High Impact" if max_pre_speed > 35.0 else "Moderate Impact"
                            desc = (
                                f"Collision detected between {t1} and {t2} (Impact speed delta: "
                                f"{delta_v:.1f} px/s, IoU: {iou:.2f})."
                            )
                            incident = CollisionIncident(
                                incident_id=self._next_incident_id(),
                                frame_number=frame_number,
                                timestamp_seconds=timestamp_seconds,
                                timestamp_hms=timestamp_hms,
                                primary_track_id=t1,
                                secondary_track_id=t2,
                                collision_type="VEHICLE_VEHICLE_COLLISION",
                                impact_speed_delta_px_s=round(delta_v, 2),
                                description=desc,
                                severity_advisory=severity,
                                location_xy=(round((cx1 + cx2) / 2.0, 1), round((cy1 + cy2) / 2.0, 1))
                            )
                            self.incidents.append(incident)
                            new_incidents.append(incident)
                            self.reported_pairs.add(pair_key)

        return new_incidents

    def get_crashed_track_ids(self) -> Set[str]:
        """Return set of all track IDs involved in detected collisions."""
        crashed: Set[str] = set()
        for inc in self.incidents:
            if inc.primary_track_id:
                crashed.add(inc.primary_track_id)
            if inc.secondary_track_id:
                crashed.add(inc.secondary_track_id)
        return crashed

    def get_all_incidents(self) -> List[CollisionIncident]:
        """Return chronological list of recorded collision incidents."""
        return sorted(self.incidents, key=lambda x: (x.timestamp_seconds, x.frame_number))
