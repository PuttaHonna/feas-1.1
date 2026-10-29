"""
CCTV Virtual Tripwire & Line-Crossing In/Out Counting Module.
=============================================================
Provides geometric line-crossing event detection and direction telemetry:
1. Configurable virtual tripwire line across camera view (vertical, horizontal, or arbitrary 2D vector).
2. Trajectory intersection & side-transition tracking (Side A -> Side B = IN, Side B -> Side A = OUT).
3. Instantaneous velocity and heading direction vector calculation for motion arrows.
4. Persistent, deduplicated counting telemetry with per-track event auditing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import math
import numpy as np


class CrossingDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"
    NONE = "NONE"


@dataclass
class LineCrossingEvent:
    """Audit record for an object crossing the virtual tripwire."""
    track_id: str
    track_number: int
    class_name: str
    direction: CrossingDirection
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    crossing_point: Tuple[float, float]
    speed_px_per_frame: float
    heading_angle_degrees: float


class LineCrossingCounter:
    """
    Tripwire line crossing counter and direction analyzer for surveillance video.
    Default: Vertical counting line at 70% of frame width (matching lobby surveillance setups).
    """

    def __init__(
        self,
        line_pt1: Optional[Tuple[float, float]] = None,
        line_pt2: Optional[Tuple[float, float]] = None,
        default_x_ratio: float = 0.70,
        in_direction_label: str = "IN",
        out_direction_label: str = "OUT"
    ):
        """
        Args:
            line_pt1: Start point (x, y) of tripwire line. If None, calculated dynamically from frame size.
            line_pt2: End point (x, y) of tripwire line.
            default_x_ratio: Normalized horizontal position if vertical line is auto-configured.
            in_direction_label: Label for Side A -> Side B crossings (e.g. 'IN').
            out_direction_label: Label for Side B -> Side A crossings (e.g. 'OUT').
        """
        self.custom_line_pt1 = line_pt1
        self.custom_line_pt2 = line_pt2
        self.default_x_ratio = default_x_ratio
        self.in_direction_label = in_direction_label
        self.out_direction_label = out_direction_label

        # Counters
        self.in_count: int = 0
        self.out_count: int = 0

        # Internal state: track_id -> previous centroid (x, y, frame)
        self.previous_centroids: Dict[str, Tuple[float, float, int]] = {}
        # track_id -> previous sign relative to line
        self.previous_sides: Dict[str, float] = {}
        # Set of track_ids that already crossed to prevent duplicate counts on same crossing
        self.crossed_tracks: Set[str] = set()

        # Motion vectors: track_id -> (dx, dy, speed, angle)
        self.track_vectors: Dict[str, Tuple[float, float, float, float]] = {}

        # Log of all crossing events
        self.crossing_events: List[LineCrossingEvent] = []

    def get_tripwire_line(self, frame_w: int, frame_h: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Return the pixel coordinates of the tripwire line [(x1, y1), (x2, y2)]."""
        if self.custom_line_pt1 is not None and self.custom_line_pt2 is not None:
            return (
                (int(self.custom_line_pt1[0]), int(self.custom_line_pt1[1])),
                (int(self.custom_line_pt2[0]), int(self.custom_line_pt2[1]))
            )
        # Default: Vertical line through the hallway / lobby
        x = int(frame_w * self.default_x_ratio)
        return ((x, 0), (x, frame_h))

    @staticmethod
    def _point_line_side(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """
        Calculates cross-product (b - a) x (p - a).
        Positive = left / side A, Negative = right / side B, 0 = collinear.
        """
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    def update_tracks(
        self,
        active_detections: List[Any],
        frame_w: int,
        frame_h: int,
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str
    ) -> List[LineCrossingEvent]:
        """
        Process active tracks for the current frame, detect line crossings, and compute motion vectors.
        """
        line_a, line_b = self.get_tripwire_line(frame_w, frame_h)
        new_events: List[LineCrossingEvent] = []

        for det in active_detections:
            tid = getattr(det, "track_id", None)
            if not tid:
                continue

            cx = float(getattr(det, "centroid_x", (det.x1 + det.x2) / 2.0))
            cy = float(getattr(det, "centroid_y", (det.y1 + det.y2) / 2.0))
            class_name = getattr(det, "class_name", "person")

            # Extract integer track number if present (e.g. 'person_01' -> 1 or 'ID: 102' -> 102)
            track_num = 0
            if hasattr(det, "track_number") and det.track_number:
                track_num = int(det.track_number)
            else:
                digits = "".join(filter(str.isdigit, str(tid)))
                track_num = int(digits) if digits else 1

            curr_side = self._point_line_side((cx, cy), line_a, line_b)

            if tid in self.previous_centroids:
                prev_x, prev_y, prev_f = self.previous_centroids[tid]
                dx = cx - prev_x
                dy = cy - prev_y
                speed = math.sqrt(dx * dx + dy * dy)
                angle = math.degrees(math.atan2(dy, dx))
                self.track_vectors[tid] = (dx, dy, speed, angle)

                prev_side = self.previous_sides.get(tid, curr_side)

                # Check if object crossed the line between previous and current frame
                # Sign change indicates crossing
                if (prev_side * curr_side < 0) and (tid not in self.crossed_tracks) and (speed > 1.0):
                    # Direction determination:
                    # In standard coordinates with line running top to bottom:
                    # Side > 0 is Left/West, Side < 0 is Right/East
                    # Left to Right = OUT (or user defined), Right to Left = IN
                    if prev_side > 0 and curr_side < 0:
                        direction = CrossingDirection.OUT
                        self.out_count += 1
                    else:
                        direction = CrossingDirection.IN
                        self.in_count += 1

                    self.crossed_tracks.add(tid)

                    event = LineCrossingEvent(
                        track_id=tid,
                        track_number=track_num,
                        class_name=class_name,
                        direction=direction,
                        frame_number=frame_number,
                        timestamp_seconds=timestamp_seconds,
                        timestamp_hms=timestamp_hms,
                        crossing_point=(cx, cy),
                        speed_px_per_frame=round(speed, 2),
                        heading_angle_degrees=round(angle, 1)
                    )
                    self.crossing_events.append(event)
                    new_events.append(event)
            else:
                # First frame seen
                self.track_vectors[tid] = (0.0, 0.0, 0.0, 0.0)

            self.previous_centroids[tid] = (cx, cy, frame_number)
            self.previous_sides[tid] = curr_side

        return new_events

    def get_summary(self) -> Dict[str, Any]:
        """Return structured counting telemetry."""
        return {
            "in_count": self.in_count,
            "out_count": self.out_count,
            "total_crossings": self.in_count + self.out_count,
            "events_count": len(self.crossing_events),
            "events": [
                {
                    "track_id": e.track_id,
                    "track_number": e.track_number,
                    "class": e.class_name,
                    "direction": e.direction.value,
                    "frame": e.frame_number,
                    "timestamp": e.timestamp_hms,
                    "crossing_point": [round(e.crossing_point[0], 1), round(e.crossing_point[1], 1)],
                    "speed": e.speed_px_per_frame
                }
                for e in self.crossing_events
            ]
        }
