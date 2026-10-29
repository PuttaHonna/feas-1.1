"""
CCTV Multi-Object Tracking Module.
Maintains stable track identifiers (e.g. person_01, car_02) across video frames.
Documents spatial centroid trajectories and avoids claiming biometric continuity.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.cctv.detector import Detection


@dataclass
class TrackSummary:
    """Consolidated lifecycle metadata for a single tracked object."""
    track_id: str
    class_name: str
    camera_id: str
    evidence_id: str
    first_seen_seconds: float
    last_seen_seconds: float
    visible_duration_seconds: float
    first_frame: int
    last_frame: int
    max_confidence: float
    avg_confidence: float
    total_detections: int
    first_keyframe: Optional[str] = None
    best_keyframe: Optional[str] = None
    last_keyframe: Optional[str] = None
    dominant_color: Optional[str] = "unclassified"
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class": self.class_name,
            "dominant_color": self.dominant_color,
            "first_seen_timestamp": f"{self.first_seen_seconds:.2f}s",
            "last_seen_timestamp": f"{self.last_seen_seconds:.2f}s",
            "visible_duration": f"{self.visible_duration_seconds:.2f}s",
            "first_frame_number": self.first_frame,
            "last_frame_number": self.last_frame,
            "maximum_confidence": round(self.max_confidence, 4),
            "average_confidence": round(self.avg_confidence, 4),
            "total_detections": self.total_detections,
            "first_keyframe_path": self.first_keyframe,
            "best_confidence_keyframe_path": self.best_keyframe,
            "last_keyframe_path": self.last_keyframe,
            "centroid_movement_path": [
                {"x": round(pt[0], 1), "y": round(pt[1], 1), "t": round(pt[2], 2)}
                for pt in self.trajectory
            ]
        }


class CCTVTracker:
    """Multi-object tracker assigning readable, class-scoped identifiers."""

    def __init__(self, iou_threshold: float = 0.35, max_lost_frames: int = 15):
        """Initialize tracking engine.

        Args:
            iou_threshold: Minimum intersection-over-union for spatial association.
            max_lost_frames: Frames of tolerance before concluding an object track has exited.
        """
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames

        # Internal state
        self.active_tracks: Dict[str, Dict] = {}  # track_id -> track state
        self.completed_tracks: Dict[str, TrackSummary] = {}
        self.class_counters: Dict[str, int] = {}  # class_name -> next int

    def _generate_track_id(self, class_name: str) -> str:
        """Assign sequential stable human-readable ID like 'person_01', 'car_01'."""
        clean_cls = "auto" if class_name in ("auto", "auto_rickshaw") else class_name
        count = self.class_counters.get(clean_cls, 0) + 1
        self.class_counters[clean_cls] = count
        return f"{clean_cls}_{count:02d}"

    @staticmethod
    def _calculate_iou(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes (x1, y1, x2, y2)."""
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

    @staticmethod
    def _calculate_spatial_affinity(
        b1: Tuple[float, float, float, float],
        c1: Tuple[float, float],
        b2: Tuple[float, float, float, float],
        c2: Tuple[float, float],
        max_dist_px: float = 240.0
    ) -> float:
        """
        Combines Intersection-over-Union (IoU) with normalized Centroid Euclidean Distance.
        Guarantees reliable multi-object tracking across lower frame-rates (e.g. 1 FPS)
        where moving pedestrians move faster than pure IoU overlap.
        """
        # 1. IoU score
        x1_a, y1_a, x2_a, y2_a = b1
        x1_b, y1_b, x2_b, y2_b = b2
        x_left = max(x1_a, x1_b)
        y_top = max(y1_a, y1_b)
        x_right = min(x2_a, x2_b)
        y_bottom = min(y2_a, y2_b)
        iou = 0.0
        if x_right > x_left and y_bottom > y_top:
            intersection = (x_right - x_left) * (y_bottom - y_top)
            area_a = max(0.0, (x2_a - x1_a) * (y2_a - y1_a))
            area_b = max(0.0, (x2_b - x1_b) * (y2_b - y1_b))
            union = area_a + area_b - intersection
            iou = (intersection / union) if union > 0 else 0.0

        # 2. Centroid distance score
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > max_dist_px:
            dist_score = 0.0
        else:
            # Area/scale consistency check
            area_a = max(1.0, (x2_a - x1_a) * (y2_a - y1_a))
            area_b = max(1.0, (x2_b - x1_b) * (y2_b - y1_b))
            scale_ratio = area_a / area_b if area_a > area_b else area_b / area_a
            if scale_ratio > 3.0:
                dist_score = 0.0
            else:
                dist_score = max(0.0, 1.0 - (dist / max_dist_px))

        # Return best matching metric
        return max(iou, dist_score * 0.75)

    def update(
        self,
        detections: List[Detection],
        frame_number: int,
        timestamp_seconds: float
    ) -> List[Detection]:
        """Associate detections in the current frame to active tracks or initialize new tracks.

        Args:
            detections: Filtered detections in the current frame.
            frame_number: Frame index.
            timestamp_seconds: Current timestamp in seconds.

        Returns:
            List of Detections updated with assigned track_id.
        """
        # Age existing tracks
        for tid in list(self.active_tracks.keys()):
            self.active_tracks[tid]["lost_count"] += 1

        assigned_det_indices = set()
        assigned_track_ids = set()

        # Match detections to active tracks of identical class by spatial affinity (IoU + Centroid proximity)
        for tid, tstate in self.active_tracks.items():
            best_score = 0.0
            best_det_idx = -1

            track_box = (tstate["x1"], tstate["y1"], tstate["x2"], tstate["y2"])
            track_centroid = (tstate["centroid_x"], tstate["centroid_y"])

            for idx, det in enumerate(detections):
                if idx in assigned_det_indices:
                    continue
                if det.class_name != tstate["class_name"]:
                    veh_group = {"auto", "auto_rickshaw", "truck", "car"}
                    animal_group = {"dog", "cat", "cow", "horse", "sheep", "bird", "elephant"}
                    is_veh_compat = (det.class_name in veh_group and tstate["class_name"] in veh_group)
                    is_animal_compat = (det.class_name in animal_group and tstate["class_name"] in animal_group)
                    if not (is_veh_compat or is_animal_compat):
                        continue

                det_box = (det.x1, det.y1, det.x2, det.y2)
                det_centroid = (det.centroid_x, det.centroid_y)
                score = self._calculate_spatial_affinity(track_box, track_centroid, det_box, det_centroid)

                if score > best_score:
                    best_score = score
                    best_det_idx = idx

            # Spatial affinity threshold (accepts centroid continuity when fast movement lowers IoU)
            if best_score >= 0.20 and best_det_idx != -1:
                det = detections[best_det_idx]
                # Maintain track's established auto or animal class if matched
                if tstate["class_name"] in ("auto", "auto_rickshaw"):
                    det.class_name = tstate["class_name"]
                elif tstate["class_name"] in {"dog", "cat", "cow", "horse", "sheep"}:
                    det.class_name = tstate["class_name"]
                det.track_id = tid
                det.track_number = tstate.get("track_number", 0)
                assigned_det_indices.add(best_det_idx)
                assigned_track_ids.add(tid)

                # Update track state
                tstate["x1"] = det.x1
                tstate["y1"] = det.y1
                tstate["x2"] = det.x2
                tstate["y2"] = det.y2
                tstate["centroid_x"] = det.centroid_x
                tstate["centroid_y"] = det.centroid_y
                tstate["last_frame"] = frame_number
                tstate["last_seen_seconds"] = timestamp_seconds
                tstate["confidences"].append(det.confidence)
                tstate["lost_count"] = 0
                tstate["trajectory"].append((det.centroid_x, det.centroid_y, timestamp_seconds))

                if det.confidence > tstate["max_confidence"]:
                    tstate["max_confidence"] = det.confidence
                    tstate["best_frame_number"] = frame_number

        # Create new tracks for unassigned detections
        for idx, det in enumerate(detections):
            if idx not in assigned_det_indices:
                new_tid = self._generate_track_id(det.class_name)
                track_num = self.class_counters.get(det.class_name, 1)
                det.track_id = new_tid
                det.track_number = track_num

                self.active_tracks[new_tid] = {
                    "track_id": new_tid,
                    "track_number": track_num,
                    "class_name": det.class_name,
                    "camera_id": det.camera_id,
                    "evidence_id": det.evidence_id,
                    "x1": det.x1,
                    "y1": det.y1,
                    "x2": det.x2,
                    "y2": det.y2,
                    "centroid_x": det.centroid_x,
                    "centroid_y": det.centroid_y,
                    "first_frame": frame_number,
                    "last_frame": frame_number,
                    "first_seen_seconds": timestamp_seconds,
                    "last_seen_seconds": timestamp_seconds,
                    "max_confidence": det.confidence,
                    "best_frame_number": frame_number,
                    "confidences": [det.confidence],
                    "lost_count": 0,
                    "trajectory": [(det.centroid_x, det.centroid_y, timestamp_seconds)],
                    "first_keyframe": None,
                    "best_keyframe": None,
                    "last_keyframe": None,
                }

        # Retire tracks that have exceeded max_lost_frames
        for tid in list(self.active_tracks.keys()):
            tstate = self.active_tracks[tid]
            if tstate["lost_count"] > self.max_lost_frames:
                self._retire_track(tid)

        return detections

    def _retire_track(self, tid: str):
        """Move track from active to completed tracks."""
        if tid in self.active_tracks:
            t = self.active_tracks.pop(tid)
            duration = max(0.0, t["last_seen_seconds"] - t["first_seen_seconds"])
            avg_conf = float(np.mean(t["confidences"])) if t["confidences"] else t["max_confidence"]

            summary = TrackSummary(
                track_id=t["track_id"],
                class_name=t["class_name"],
                camera_id=t["camera_id"],
                evidence_id=t["evidence_id"],
                first_seen_seconds=t["first_seen_seconds"],
                last_seen_seconds=t["last_seen_seconds"],
                visible_duration_seconds=round(duration, 3),
                first_frame=t["first_frame"],
                last_frame=t["last_frame"],
                max_confidence=round(t["max_confidence"], 4),
                avg_confidence=round(avg_conf, 4),
                total_detections=len(t["confidences"]),
                first_keyframe=t.get("first_keyframe"),
                best_keyframe=t.get("best_keyframe"),
                last_keyframe=t.get("last_keyframe"),
                trajectory=t["trajectory"]
            )
            self.completed_tracks[tid] = summary

    def finalize(self, min_detections: int = 1) -> Dict[str, TrackSummary]:
        """Retire all remaining active tracks at end of video stream.

        Args:
            min_detections: Minimum frame hits required to confirm a track in multi-frame video.
                           If > 1, single-frame spurious spikes (duration 0.0s) are filtered out
                           to maintain forensic data integrity and eliminate false positive noise.
        """
        for tid in list(self.active_tracks.keys()):
            self._retire_track(tid)

        if min_detections <= 1:
            return self.completed_tracks

        confirmed = {
            tid: summary for tid, summary in self.completed_tracks.items()
            if summary.total_detections >= min_detections or summary.visible_duration_seconds > 0.1
        }
        return confirmed
