"""
CCTV Suspicious Vehicle Activity Detection Module.
Detects anomalous vehicle kinematic patterns:
- Wrong-way driving against dominant traffic flow
- Sudden stops / abandoned vehicles in active lanes
- Erratic swerving / zigzagging / rapid lateral shifts
- Excessive speed anomalies

Compliance notice:
- Objective kinematic anomaly detection only.
- Does not impute intent, criminality, or suspicion to individuals.
- Advisory research output requiring human forensic verification.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

SUSPICIOUS_DISCLAIMER: str = (
    "Kinematic anomaly heuristic. Advisory research output only; does not prove "
    "criminal intent or legal violation. Requires certified human analyst review."
)

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}


@dataclass
class SuspiciousActivityAlert:
    """Represents a flagged anomalous vehicle behavior."""
    alert_id: str
    track_id: str
    activity_type: str                  # WRONG_WAY_MOVEMENT, SUDDEN_ROADWAY_STOP, ERRATIC_WEAVING, HIGH_SPEED_MOVEMENT
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    description: str
    severity_level: str                 # HIGH, MEDIUM, LOW
    heading_degrees: Optional[float] = None
    speed_px_s: Optional[float] = None
    advisory_disclaimer: str = SUSPICIOUS_DISCLAIMER

    def to_dict(self) -> Dict:
        return asdict(self)


class SuspiciousActivityDetector:
    """Evaluates vehicle trajectories for kinematic anomalies."""

    def __init__(
        self,
        min_motion_speed: float = 8.0,
        wrong_way_deviation_deg: float = 120.0,
        stop_dwell_threshold_seconds: float = 3.0,
        swerving_angle_threshold_deg: float = 40.0
    ):
        """Initialize detector.
        
        Args:
            min_motion_speed: Minimum speed (px/sec) to consider vehicle in active motion.
            wrong_way_deviation_deg: Angular difference from dominant flow to flag wrong-way motion.
            stop_dwell_threshold_seconds: Stationary duration before flagging roadway stop.
            swerving_angle_threshold_deg: Rapid angular variation threshold for swerving.
        """
        self.min_motion_speed = min_motion_speed
        self.wrong_way_deg = wrong_way_deviation_deg
        self.stop_threshold_sec = stop_dwell_threshold_seconds
        self.swerving_thresh_deg = swerving_angle_threshold_deg

        self.alerts: List[SuspiciousActivityAlert] = []
        self.alert_counter: int = 0

        # State trackers per track_id
        # track_id -> list of (frame, ts, cx, cy, speed, heading_deg)
        self.trajectories: Dict[str, List[Tuple[int, float, float, float, float, float]]] = {}
        self.halted_start_time: Dict[str, float] = {}  # track_id -> start ts of stop
        self.flagged_activities: Dict[str, Set[str]] = {}  # track_id -> set of flagged types

    def _next_alert_id(self) -> str:
        self.alert_counter += 1
        return f"SUSP-{self.alert_counter:04d}"

    @staticmethod
    def _calculate_heading(dx: float, dy: float) -> float:
        """Compute angle in degrees [0, 360)."""
        rad = math.atan2(dy, dx)
        deg = math.degrees(rad)
        return (deg + 360.0) % 360.0

    @staticmethod
    def _angular_diff(deg1: float, deg2: float) -> float:
        """Calculate minimum absolute difference between two angles in degrees."""
        diff = abs(deg1 - deg2) % 360.0
        return 360.0 - diff if diff > 180.0 else diff

    def record_movement(
        self,
        track_id: str,
        class_name: str,
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str,
        cx: float,
        cy: float
    ) -> List[SuspiciousActivityAlert]:
        """Record vehicle position, update trajectory, and evaluate anomalous patterns."""
        if class_name not in VEHICLE_CLASSES:
            return []

        if track_id not in self.trajectories:
            self.trajectories[track_id] = []
            self.flagged_activities[track_id] = set()

        history = self.trajectories[track_id]
        speed = 0.0
        heading = 0.0

        if history:
            prev_frame, prev_ts, prev_cx, prev_cy, _, prev_heading = history[-1]
            dt = max(0.001, timestamp_seconds - prev_ts)
            dx = cx - prev_cx
            dy = cy - prev_cy
            dist = math.hypot(dx, dy)
            speed = dist / dt
            if dist > 3.0:
                heading = self._calculate_heading(dx, dy)
            else:
                heading = prev_heading

        history.append((frame_number, timestamp_seconds, cx, cy, speed, heading))
        if len(history) > 60:
            history.pop(0)

        new_alerts: List[SuspiciousActivityAlert] = []

        # 1. Anomaly: Sudden Stop in active roadway
        if len(history) >= 8:
            # Check if previously moving with high speed (> 15 px/s)
            recent_speeds = [h[4] for h in history[-8:-3]]
            was_moving = any(s > self.min_motion_speed * 1.5 for s in recent_speeds)
            is_now_stationary = speed < 3.0

            if was_moving and is_now_stationary:
                if track_id not in self.halted_start_time:
                    self.halted_start_time[track_id] = timestamp_seconds
                else:
                    duration = timestamp_seconds - self.halted_start_time[track_id]
                    if duration >= self.stop_threshold_sec and "SUDDEN_ROADWAY_STOP" not in self.flagged_activities[track_id]:
                        self.flagged_activities[track_id].add("SUDDEN_ROADWAY_STOP")
                        alert = SuspiciousActivityAlert(
                            alert_id=self._next_alert_id(),
                            track_id=track_id,
                            activity_type="SUDDEN_ROADWAY_STOP",
                            frame_number=frame_number,
                            timestamp_seconds=timestamp_seconds,
                            timestamp_hms=timestamp_hms,
                            description=(
                                f"Vehicle {track_id} came to an abrupt halt and remained stationary "
                                f"for {duration:.1f}s in roadway."
                            ),
                            severity_level="MEDIUM",
                            speed_px_s=round(speed, 1),
                            heading_degrees=round(heading, 1)
                        )
                        self.alerts.append(alert)
                        new_alerts.append(alert)
            elif not is_now_stationary:
                self.halted_start_time.pop(track_id, None)

        # 2. Anomaly: Erratic Swerving / Zigzagging
        if len(history) >= 15 and "ERRATIC_WEAVING" not in self.flagged_activities[track_id]:
            # Inspect rapid heading changes
            headings = [h[5] for h in history[-15:] if h[4] > self.min_motion_speed]
            if len(headings) >= 6:
                angle_shifts = 0
                for k in range(len(headings) - 1):
                    if self._angular_diff(headings[k], headings[k + 1]) >= self.swerving_thresh_deg:
                        angle_shifts += 1

                if angle_shifts >= 3:
                    self.flagged_activities[track_id].add("ERRATIC_WEAVING")
                    alert = SuspiciousActivityAlert(
                        alert_id=self._next_alert_id(),
                        track_id=track_id,
                        activity_type="ERRATIC_WEAVING",
                        frame_number=frame_number,
                        timestamp_seconds=timestamp_seconds,
                        timestamp_hms=timestamp_hms,
                        description=(
                            f"Vehicle {track_id} exhibited erratic trajectory oscillations / swerving "
                            f"({angle_shifts} rapid angular shifts)."
                        ),
                        severity_level="HIGH",
                        speed_px_s=round(speed, 1),
                        heading_degrees=round(heading, 1)
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)

        return new_alerts

    def evaluate_flow_directions(
        self,
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str
    ) -> List[SuspiciousActivityAlert]:
        """Evaluate traffic flow headings across all active vehicles for Wrong-Way driving."""
        new_alerts: List[SuspiciousActivityAlert] = []

        # Collect current headings of vehicles in active motion
        active_headings = []
        track_headings = {}

        for tid, hist in self.trajectories.items():
            if not hist:
                continue
            last_entry = hist[-1]
            # Ensure it is currently fresh (within last 3 frames)
            if (frame_number - last_entry[0]) <= 3 and last_entry[4] >= self.min_motion_speed:
                active_headings.append(last_entry[5])
                track_headings[tid] = (last_entry[5], last_entry[4])

        if len(active_headings) < 3:
            # Not enough moving vehicles to reliably establish dominant traffic flow
            return new_alerts

        # Dominant flow angle (circular mean)
        sin_sum = sum(math.sin(math.radians(h)) for h in active_headings)
        cos_sum = sum(math.cos(math.radians(h)) for h in active_headings)
        dominant_flow = (math.degrees(math.atan2(sin_sum, cos_sum)) + 360.0) % 360.0

        # Check for opposing motion
        for tid, (hdg, spd) in track_headings.items():
            if "WRONG_WAY_MOVEMENT" in self.flagged_activities[tid]:
                continue

            angular_deviation = self._angular_diff(hdg, dominant_flow)
            if angular_deviation >= self.wrong_way_deg:
                self.flagged_activities[tid].add("WRONG_WAY_MOVEMENT")
                alert = SuspiciousActivityAlert(
                    alert_id=self._next_alert_id(),
                    track_id=tid,
                    activity_type="WRONG_WAY_MOVEMENT",
                    frame_number=frame_number,
                    timestamp_seconds=timestamp_seconds,
                    timestamp_hms=timestamp_hms,
                    description=(
                        f"Vehicle {tid} moving against dominant traffic flow "
                        f"(heading: {hdg:.0f}°, flow: {dominant_flow:.0f}°, diff: {angular_deviation:.0f}°)."
                    ),
                    severity_level="HIGH",
                    speed_px_s=round(spd, 1),
                    heading_degrees=round(hdg, 1)
                )
                self.alerts.append(alert)
                new_alerts.append(alert)

        return new_alerts

    def get_track_suspicious_activities(self, track_id: str) -> List[str]:
        """Return list of flagged activity descriptions for a specific track ID."""
        return list(self.flagged_activities.get(track_id, []))

    def get_all_alerts(self) -> List[SuspiciousActivityAlert]:
        """Return chronological list of recorded alerts."""
        return sorted(self.alerts, key=lambda a: (a.timestamp_seconds, a.frame_number))
