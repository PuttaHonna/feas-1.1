"""
Objective Surveillance Event Extractor
Extracts strictly factual events:
- First detected
- Entered frame boundaries
- Exited frame boundaries
- Visible for more than N seconds
- Entered / exited a configured Region of Interest (ROI)
Strictly excludes speculative or behavioral interpretations (no crime/intent/suspicious claims).
"""

from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np


class ObjectiveEventExtractor:
    """
    Extracts purely factual spatial and temporal events.
    """

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        duration_threshold_sec: float = 5.0,
        roi_polygon: Optional[List[Tuple[int, int]]] = None,
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.duration_threshold_sec = duration_threshold_sec
        self.roi_np = (
            np.array(roi_polygon, dtype=np.int32)
            if (roi_polygon and len(roi_polygon) >= 3)
            else None
        )

        self.events: List[Dict[str, Any]] = []
        self._duration_alerted_tracks = set()
        self._roi_inside_tracks = set()

    def _is_near_boundary(self, bbox: List[float], margin: int = 15) -> bool:
        """Determines if a bounding box touches or is adjacent to the frame edge."""
        x1, y1, x2, y2 = bbox
        return (
            x1 <= margin
            or y1 <= margin
            or x2 >= (self.frame_width - margin)
            or y2 >= (self.frame_height - margin)
        )

    def _is_inside_roi(self, centroid: Tuple[float, float]) -> bool:
        if self.roi_np is None:
            return False
        dist = cv2.pointPolygonTest(self.roi_np, (float(centroid[0]), float(centroid[1])), False)
        return dist >= 0

    def process_frame(
        self,
        tracks: List[Dict[str, Any]],
        frame_idx: int,
        timestamp_sec: float,
        active_tracker_instances: Dict[int, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Analyzes track positions on current frame to register objective events.
        """
        frame_events: List[Dict[str, Any]] = []

        for trk in tracks:
            tid = trk["track_id"]
            cls_name = trk["class_name"]
            bbox = trk["bbox"]
            centroid = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

            track_info = active_tracker_instances.get(tid)
            if not track_info:
                continue

            # 1. First Detected Event
            if track_info["first_frame"] == frame_idx:
                near_edge = self._is_near_boundary(bbox)
                ev_type = "entered_frame" if near_edge else "first_detected"
                ev = {
                    "event_type": ev_type,
                    "track_id": tid,
                    "class_name": cls_name,
                    "frame_idx": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "details": {
                        "bbox": bbox,
                        "origin_boundary": near_edge,
                    },
                }
                self.events.append(ev)
                frame_events.append(ev)

            # 2. Duration Threshold Event
            current_duration = timestamp_sec - track_info["first_timestamp"]
            if (
                current_duration >= self.duration_threshold_sec
                and tid not in self._duration_alerted_tracks
            ):
                ev = {
                    "event_type": "duration_threshold_exceeded",
                    "track_id": tid,
                    "class_name": cls_name,
                    "frame_idx": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "details": {
                        "duration_seconds": round(current_duration, 2),
                        "threshold_seconds": self.duration_threshold_sec,
                    },
                }
                self._duration_alerted_tracks.add(tid)
                self.events.append(ev)
                frame_events.append(ev)

            # 3. ROI Enter/Exit Events
            if self.roi_np is not None:
                inside = self._is_inside_roi(centroid)
                was_inside = tid in self._roi_inside_tracks

                if inside and not was_inside:
                    self._roi_inside_tracks.add(tid)
                    ev = {
                        "event_type": "roi_entered",
                        "track_id": tid,
                        "class_name": cls_name,
                        "frame_idx": frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "details": {"centroid": [round(c, 1) for c in centroid]},
                    }
                    self.events.append(ev)
                    frame_events.append(ev)
                elif not inside and was_inside:
                    self._roi_inside_tracks.remove(tid)
                    ev = {
                        "event_type": "roi_exited",
                        "track_id": tid,
                        "class_name": cls_name,
                        "frame_idx": frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "details": {"centroid": [round(c, 1) for c in centroid]},
                    }
                    self.events.append(ev)
                    frame_events.append(ev)

        return frame_events

    def finalize_exits(self, track_summaries: Dict[int, Dict[str, Any]]) -> None:
        """Records exited_frame events for finished tracks."""
        for tid, summary in track_summaries.items():
            ev = {
                "event_type": "exited_frame",
                "track_id": tid,
                "class_name": summary["class_name"],
                "frame_idx": summary["last_frame"],
                "timestamp_sec": summary["last_timestamp"],
                "details": {
                    "total_visible_duration_seconds": summary["duration_seconds"],
                    "total_observations": summary["total_observations"],
                },
            }
            self.events.append(ev)

    def get_events(self) -> List[Dict[str, Any]]:
        return self.events
