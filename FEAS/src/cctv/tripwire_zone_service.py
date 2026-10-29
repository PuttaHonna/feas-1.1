"""
CCTV Virtual Tripwire & Perimeter Zone Intrusion Service.
=========================================================
Implements vector cross-product tripwire crossing detection with directional semantics (ENTRY vs. EXIT)
and ray-casting / point-in-polygon perimeter security zones (cv2.pointPolygonTest / shapely).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import math
import cv2
import numpy as np


class CrossingDirection(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    NONE = "NONE"


@dataclass
class ZoneDefinition:
    """Represents a user-defined polygon zone on the camera canvas."""
    zone_id: str
    name: str
    polygon: List[Tuple[float, float]]  # List of normalized or pixel (x, y) coordinates
    zone_type: str = "restricted"       # 'restricted', 'exclusion', 'entry_point', 'loitering_zone'
    color_bgr: Tuple[int, int, int] = (0, 0, 255)  # Red for restricted by default


@dataclass
class TripwireDefinition:
    """Represents a virtual tripwire line with directional vector."""
    tripwire_id: str
    name: str
    pt1: Tuple[float, float]  # (x1, y1)
    pt2: Tuple[float, float]  # (x2, y2)
    entry_label: str = "ENTRY"
    exit_label: str = "EXIT"


@dataclass
class IntrusionAlert:
    """Security alert emitted when a track enters a restricted polygon zone."""
    alert_id: str
    zone_id: str
    zone_name: str
    track_id: str
    track_number: int
    class_name: str
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    centroid: Tuple[float, float]
    bounding_box: Tuple[float, float, float, float]
    severity: str = "HIGH"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TripwireCrossingEvent:
    """Audit record for a line crossing event."""
    event_id: str
    tripwire_id: str
    track_id: str
    track_number: int
    class_name: str
    direction: CrossingDirection
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    crossing_point: Tuple[float, float]
    speed_px_s: float
    heading_degrees: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TripwireZoneService:
    """
    Unified geometric engine for Virtual Tripwires and Perimeter Zone monitoring.
    """

    def __init__(
        self,
        zones: Optional[List[ZoneDefinition]] = None,
        tripwires: Optional[List[TripwireDefinition]] = None
    ):
        self.zones: Dict[str, ZoneDefinition] = {z.zone_id: z for z in (zones or [])}
        self.tripwires: Dict[str, TripwireDefinition] = {t.tripwire_id: t for t in (tripwires or [])}

        # Tripwire telemetry state
        # (tripwire_id, track_id) -> previous sign
        self._prev_tripwire_sides: Dict[Tuple[str, str], float] = {}
        # (tripwire_id, track_id) -> last crossing frame
        self._last_crossed_frame: Dict[Tuple[str, str], int] = {}
        # Counter aggregates
        self.crossing_counts: Dict[str, Dict[str, int]] = {
            t.tripwire_id: {"ENTRY": 0, "EXIT": 0} for t in (tripwires or [])
        }

        # Zone telemetry state: (zone_id, track_id) -> is_inside
        self._inside_zones: Dict[Tuple[str, str], bool] = {}
        self._zone_entry_timestamps: Dict[Tuple[str, str], float] = {}

        # Logged events
        self.intrusion_alerts: List[IntrusionAlert] = []
        self.crossing_events: List[TripwireCrossingEvent] = []
        self._alert_counter = 0

    def add_zone(self, zone: ZoneDefinition) -> None:
        self.zones[zone.zone_id] = zone

    def add_tripwire(self, tripwire: TripwireDefinition) -> None:
        self.tripwires[tripwire.tripwire_id] = tripwire
        if tripwire.tripwire_id not in self.crossing_counts:
            self.crossing_counts[tripwire.tripwire_id] = {"ENTRY": 0, "EXIT": 0}

    @staticmethod
    def _cross_product_side(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Calculate vector cross-product (b - a) x (p - a) in 2D."""
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    @staticmethod
    def _is_point_in_polygon(point: Tuple[float, float], polygon_pts: List[Tuple[float, float]]) -> bool:
        """Fast point-in-polygon test using OpenCV."""
        if len(polygon_pts) < 3:
            return False
        contour = np.array(polygon_pts, dtype=np.float32).reshape((-1, 1, 2))
        res = cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), measureDist=False)
        return res >= 0

    def process_track(
        self,
        track_id: str,
        track_number: int,
        class_name: str,
        centroid: Tuple[float, float],
        bbox: Tuple[float, float, float, float],
        frame_number: int,
        timestamp_seconds: float,
        speed_px_s: float = 0.0,
        heading_degrees: float = 0.0
    ) -> Tuple[List[IntrusionAlert], List[TripwireCrossingEvent]]:
        """
        Evaluate single track against all configured tripwires and security zones.
        """
        new_intrusions: List[IntrusionAlert] = []
        new_crossings: List[TripwireCrossingEvent] = []

        # 1. Evaluate Perimeter Zones
        for zone_id, zone in self.zones.items():
            key = (zone_id, track_id)
            is_inside = self._is_point_in_polygon(centroid, zone.polygon)
            was_inside = self._inside_zones.get(key, False)

            if is_inside and not was_inside:
                # Trigger Intrusion Alert
                self._alert_counter += 1
                alert_id = f"ALT-ZONE-{self._alert_counter:04d}"
                hms = f"{int(timestamp_seconds // 3600):02d}:{int((timestamp_seconds % 3600) // 60):02d}:{timestamp_seconds % 60:05.2f}"
                
                alert = IntrusionAlert(
                    alert_id=alert_id,
                    zone_id=zone_id,
                    zone_name=zone.name,
                    track_id=track_id,
                    track_number=track_number,
                    class_name=class_name,
                    frame_number=frame_number,
                    timestamp_seconds=round(timestamp_seconds, 2),
                    timestamp_hms=hms,
                    centroid=(round(centroid[0], 1), round(centroid[1], 1)),
                    bounding_box=tuple(round(v, 1) for v in bbox),
                    severity="CRITICAL" if zone.zone_type == "restricted" else "MEDIUM",
                    description=f"{class_name.upper()} ({track_id}) breached perimeter zone '{zone.name}'"
                )
                self.intrusion_alerts.append(alert)
                new_intrusions.append(alert)
                self._zone_entry_timestamps[key] = timestamp_seconds

            self._inside_zones[key] = is_inside

        # 2. Evaluate Virtual Tripwires
        for tripwire_id, tw in self.tripwires.items():
            tkey = (tripwire_id, track_id)
            current_side = self._cross_product_side(centroid, tw.pt1, tw.pt2)
            prev_side = self._prev_tripwire_sides.get(tkey)

            if prev_side is not None and abs(current_side) > 1e-4 and abs(prev_side) > 1e-4:
                # Sign change indicates crossing of the infinite line segment
                if (prev_side > 0 and current_side < 0) or (prev_side < 0 and current_side > 0):
                    last_f = self._last_crossed_frame.get(tkey, -999)
                    if frame_number - last_f > 15:  # Deduplication debounce window (15 frames)
                        direction = CrossingDirection.ENTRY if (prev_side > 0 and current_side < 0) else CrossingDirection.EXIT
                        dir_str = direction.value

                        self.crossing_counts[tripwire_id][dir_str] = self.crossing_counts[tripwire_id].get(dir_str, 0) + 1
                        self._last_crossed_frame[tkey] = frame_number

                        hms = f"{int(timestamp_seconds // 3600):02d}:{int((timestamp_seconds % 3600) // 60):02d}:{timestamp_seconds % 60:05.2f}"
                        evt = TripwireCrossingEvent(
                            event_id=f"EVT-TW-{len(self.crossing_events) + 1:04d}",
                            tripwire_id=tripwire_id,
                            track_id=track_id,
                            track_number=track_number,
                            class_name=class_name,
                            direction=direction,
                            frame_number=frame_number,
                            timestamp_seconds=round(timestamp_seconds, 2),
                            timestamp_hms=hms,
                            crossing_point=(round(centroid[0], 1), round(centroid[1], 1)),
                            speed_px_s=round(speed_px_s, 2),
                            heading_degrees=round(heading_degrees, 1)
                        )
                        self.crossing_events.append(evt)
                        new_crossings.append(evt)

            self._prev_tripwire_sides[tkey] = current_side

        return new_intrusions, new_crossings

    def render_overlays(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Draw interactive zones and tripwires onto a video frame."""
        overlay = frame_bgr.copy()

        # Render zones
        for zone in self.zones.values():
            if len(zone.polygon) >= 3:
                pts = np.array(zone.polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts], isClosed=True, color=zone.color_bgr, thickness=2)
                # Semi-transparent fill
                fill = overlay.copy()
                cv2.fillPoly(fill, [pts], color=zone.color_bgr)
                cv2.addWeighted(fill, 0.15, overlay, 0.85, 0, overlay)
                # Label
                x, y = int(zone.polygon[0][0]), int(zone.polygon[0][1])
                cv2.putText(overlay, f"ZONE: {zone.name}", (x, max(20, y - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone.color_bgr, 2)

        # Render tripwires
        for tw in self.tripwires.values():
            p1 = (int(tw.pt1[0]), int(tw.pt1[1]))
            p2 = (int(tw.pt2[0]), int(tw.pt2[1]))
            cv2.line(overlay, p1, p2, (0, 255, 255), 2, cv2.LINE_AA)
            counts = self.crossing_counts.get(tw.tripwire_id, {"ENTRY": 0, "EXIT": 0})
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(overlay, f"{tw.name} [IN:{counts['ENTRY']} | OUT:{counts['EXIT']}]",
                        (mid[0] + 5, mid[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        return overlay

