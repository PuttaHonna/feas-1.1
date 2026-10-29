"""
CCTV Loitering Detection Service.
=================================
Calculates continuous temporal dwell times for persistent tracks within monitored polygon zones.
Triggers Loitering Alerts when (Current_Time - Entry_Time) > Threshold (default 60s).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
import cv2
import numpy as np


@dataclass
class LoiteringAlert:
    """Security alert emitted when a person/vehicle dwell time exceeds safety threshold."""
    alert_id: str
    track_id: str
    track_number: int
    class_name: str
    zone_id: str
    zone_name: str
    entry_timestamp_s: float
    current_timestamp_s: float
    dwell_duration_seconds: float
    threshold_seconds: float
    frame_number: int
    timestamp_hms: str
    centroid: Tuple[float, float]
    bounding_box: Tuple[float, float, float, float]
    cropped_snapshot_path: Optional[str] = None
    severity: str = "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LoiteringDetector:
    """
    Evaluates individual track dwell times inside configured zones.
    """

    def __init__(
        self,
        dwell_threshold_seconds: float = 60.0,
        monitored_classes: Optional[Set[str]] = None,
        snapshot_dir: Optional[str] = None
    ):
        self.dwell_threshold = dwell_threshold_seconds
        self.monitored_classes = monitored_classes or {"person", "car", "motorcycle", "bicycle"}
        self.snapshot_dir = snapshot_dir

        # (zone_id, track_id) -> entry_timestamp_s
        self._zone_entry_time: Dict[Tuple[str, str], float] = {}
        # (zone_id, track_id) -> last_seen_s
        self._zone_last_seen: Dict[Tuple[str, str], float] = {}
        # (zone_id, track_id) -> boolean indicating if alert has fired
        self._alert_fired: Dict[Tuple[str, str], bool] = {}

        self.alerts: List[LoiteringAlert] = []
        self._alert_counter = 0

    def update_track_state(
        self,
        zone_id: str,
        zone_name: str,
        is_inside_zone: bool,
        track_id: str,
        track_number: int,
        class_name: str,
        centroid: Tuple[float, float],
        bbox: Tuple[float, float, float, float],
        frame_number: int,
        current_time_s: float,
        frame_bgr: Optional[np.ndarray] = None
    ) -> Optional[LoiteringAlert]:
        """
        Update dwell status for a track in a zone. Returns LoiteringAlert if threshold just breached.
        """
        if class_name.lower() not in self.monitored_classes:
            return None

        key = (zone_id, track_id)

        if is_inside_zone:
            if key not in self._zone_entry_time:
                self._zone_entry_time[key] = current_time_s
            self._zone_last_seen[key] = current_time_s

            dwell = current_time_s - self._zone_entry_time[key]

            # Check if threshold exceeded and alert not yet emitted for this loitering episode
            if dwell >= self.dwell_threshold and not self._alert_fired.get(key, False):
                self._alert_counter += 1
                self._alert_fired[key] = True

                alert_id = f"ALT-LOITER-{self._alert_counter:04d}"
                hms = f"{int(current_time_s // 3600):02d}:{int((current_time_s % 3600) // 60):02d}:{current_time_s % 60:05.2f}"

                # Extract cropped keyframe snapshot if frame is provided
                snapshot_file = None
                if frame_bgr is not None and self.snapshot_dir:
                    try:
                        x1, y1, x2, y2 = [int(v) for v in bbox]
                        h, w = frame_bgr.shape[:2]
                        x1 = max(0, x1 - 10)
                        y1 = max(0, y1 - 10)
                        x2 = min(w, x2 + 10)
                        y2 = min(h, y2 + 10)
                        crop = frame_bgr[y1:y2, x1:x2]
                        if crop.size > 0:
                            import os
                            os.makedirs(self.snapshot_dir, exist_ok=True)
                            snapshot_file = os.path.join(self.snapshot_dir, f"{alert_id}_{track_id}.jpg")
                            cv2.imwrite(snapshot_file, crop)
                    except Exception:
                        pass

                alert = LoiteringAlert(
                    alert_id=alert_id,
                    track_id=track_id,
                    track_number=track_number,
                    class_name=class_name,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    entry_timestamp_s=round(self._zone_entry_time[key], 2),
                    current_timestamp_s=round(current_time_s, 2),
                    dwell_duration_seconds=round(dwell, 1),
                    threshold_seconds=self.dwell_threshold,
                    frame_number=frame_number,
                    timestamp_hms=hms,
                    centroid=(round(centroid[0], 1), round(centroid[1], 1)),
                    bounding_box=tuple(round(v, 1) for v in bbox),
                    cropped_snapshot_path=snapshot_file,
                    severity="HIGH" if dwell > self.dwell_threshold * 1.5 else "MEDIUM"
                )
                self.alerts.append(alert)
                return alert
        else:
            # If track left zone, reset after grace period (e.g. 5 seconds to handle brief occlusion)
            if key in self._zone_last_seen:
                if current_time_s - self._zone_last_seen[key] > 5.0:
                    self._zone_entry_time.pop(key, None)
                    self._zone_last_seen.pop(key, None)
                    self._alert_fired.pop(key, None)

        return None

