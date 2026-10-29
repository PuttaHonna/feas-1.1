"""
CCTV Event Extraction Module.
Extracts objective, non-judgmental spatial and temporal events.
Strictly avoids alleging suspicious behaviour, intent, crimes, or identity.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple

from src.cctv.detector import Detection
from src.cctv.tracker import TrackSummary

HUMAN_REVIEW_DISCLAIMER: str = (
    "Automated heuristic event extraction. Advisory research output only. "
    "Requires human analyst review; does not imply intent, guilt, or legal wrongdoing."
)

VEHICLE_CLASSES = {"car", "motorcycle", "bicycle", "bus", "truck", "auto", "auto_rickshaw"}


@dataclass
class CCTVEvent:
    """Represents a discrete, non-speculative observable video event."""
    event_id: str
    event_type: str
    description: str
    track_id: Optional[str]
    timestamp_seconds: float
    timestamp_hms: str
    frame_number: int
    confidence_summary: float
    camera_id: str
    related_keyframe_path: Optional[str] = None
    human_review_warning: str = HUMAN_REVIEW_DISCLAIMER

    def to_dict(self) -> Dict:
        return asdict(self)


class CCTVEventExtractor:
    """Rule-based extractor for objective spatio-temporal CCTV events."""

    def __init__(
        self,
        dwell_threshold_seconds: float = 10.0,
        roi_polygon: Optional[List[Tuple[float, float]]] = None,
        roi_dwell_threshold_seconds: float = 5.0
    ):
        """Initialize event extractor.

        Args:
            dwell_threshold_seconds: Seconds of visibility before logging prolonged presence.
            roi_polygon: Optional list of (x, y) vertices defining an arbitrary ROI zone.
            roi_dwell_threshold_seconds: Seconds inside ROI before logging prolonged ROI presence.
        """
        self.dwell_threshold = dwell_threshold_seconds
        self.roi_polygon = roi_polygon
        self.roi_dwell_threshold = roi_dwell_threshold_seconds

        self.events: List[CCTVEvent] = []
        self.event_counter: int = 0

        # State trackers
        self.seen_classes: Set[str] = set()
        self.first_detected_tracks: Set[str] = set()
        self.prolonged_tracks: Set[str] = set()
        self.roi_entered_tracks: Set[str] = set()
        self.roi_dwell_tracks: Set[str] = set()
        self.track_roi_first_sec: Dict[str, float] = {}

    def _next_event_id(self) -> str:
        self.event_counter += 1
        return f"EVT-{self.event_counter:04d}"

    @staticmethod
    def _point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
        """Ray-casting algorithm to test whether (x, y) lies inside polygon."""
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def process_frame_detections(
        self,
        detections: List[Detection],
        frame_number: int,
        timestamp_seconds: float,
        timestamp_hms: str,
        camera_id: str,
        keyframe_path: Optional[str] = None
    ):
        """Evaluate frame detections against objective event criteria."""
        has_person = False
        has_vehicle = False

        for det in detections:
            tid = det.track_id or "untracked"

            # 1. Event: Entered camera view (consolidated factual entrance)
            if tid not in self.first_detected_tracks and tid != "untracked":
                self.first_detected_tracks.add(tid)
                self.events.append(CCTVEvent(
                    event_id=self._next_event_id(),
                    event_type="OBJECT_ENTERED_VIEW",
                    description=f"{tid} entered camera view",
                    track_id=tid,
                    timestamp_seconds=timestamp_seconds,
                    timestamp_hms=timestamp_hms,
                    frame_number=frame_number,
                    confidence_summary=det.confidence,
                    camera_id=camera_id,
                    related_keyframe_path=keyframe_path
                ))

            # 2. Event: new object class detected
            if det.class_name not in self.seen_classes:
                self.seen_classes.add(det.class_name)
                self.events.append(CCTVEvent(
                    event_id=self._next_event_id(),
                    event_type="NEW_CLASS_DETECTED",
                    description=f"new object class detected: {det.class_name}",
                    track_id=tid,
                    timestamp_seconds=timestamp_seconds,
                    timestamp_hms=timestamp_hms,
                    frame_number=frame_number,
                    confidence_summary=det.confidence,
                    camera_id=camera_id,
                    related_keyframe_path=keyframe_path
                ))

            # Check co-occurrence
            if det.class_name == "person":
                has_person = True
            elif det.class_name in VEHICLE_CLASSES or det.class_name == "train":
                has_vehicle = True

            # 3. Optional ROI Zone analysis
            if self.roi_polygon and len(self.roi_polygon) >= 3:
                in_roi = self._point_in_polygon(det.centroid_x, det.centroid_y, self.roi_polygon)
                if in_roi:
                    if tid not in self.roi_entered_tracks and tid != "untracked":
                        self.roi_entered_tracks.add(tid)
                        self.track_roi_first_sec[tid] = timestamp_seconds
                        self.events.append(CCTVEvent(
                            event_id=self._next_event_id(),
                            event_type="ENTERED_ROI_ZONE",
                            description="object entered configured ROI zone",
                            track_id=tid,
                            timestamp_seconds=timestamp_seconds,
                            timestamp_hms=timestamp_hms,
                            frame_number=frame_number,
                            confidence_summary=det.confidence,
                            camera_id=camera_id,
                            related_keyframe_path=keyframe_path
                        ))
                    elif tid in self.roi_entered_tracks and tid not in self.roi_dwell_tracks:
                        entry_time = self.track_roi_first_sec.get(tid, timestamp_seconds)
                        if (timestamp_seconds - entry_time) >= self.roi_dwell_threshold:
                            self.roi_dwell_tracks.add(tid)
                            self.events.append(CCTVEvent(
                                event_id=self._next_event_id(),
                                event_type="REMAINED_IN_ROI_ZONE",
                                description=(
                                    f"object remained in configured ROI zone for more than "
                                    f"{int(self.roi_dwell_threshold)} seconds"
                                ),
                                track_id=tid,
                                timestamp_seconds=timestamp_seconds,
                                timestamp_hms=timestamp_hms,
                                frame_number=frame_number,
                                confidence_summary=det.confidence,
                                camera_id=camera_id,
                                related_keyframe_path=keyframe_path
                            ))
                else:
                    if tid in self.roi_entered_tracks:
                        self.roi_entered_tracks.remove(tid)
                        self.events.append(CCTVEvent(
                            event_id=self._next_event_id(),
                            event_type="EXITED_ROI_ZONE",
                            description="object exited configured ROI zone",
                            track_id=tid,
                            timestamp_seconds=timestamp_seconds,
                            timestamp_hms=timestamp_hms,
                            frame_number=frame_number,
                            confidence_summary=det.confidence,
                            camera_id=camera_id,
                            related_keyframe_path=keyframe_path
                        ))

        # 4. Event: person and vehicle visible in same frame
        if has_person and has_vehicle:
            # Throttle co-occurrence event to avoid spamming every frame
            co_id = f"co_{frame_number // 25}"
            if not hasattr(self, "_seen_co_occurrences"):
                self._seen_co_occurrences = set()
            if co_id not in self._seen_co_occurrences:
                self._seen_co_occurrences.add(co_id)
                self.events.append(CCTVEvent(
                    event_id=self._next_event_id(),
                    event_type="PERSON_VEHICLE_SAME_FRAME",
                    description="person and vehicle visible in same frame",
                    track_id=None,
                    timestamp_seconds=timestamp_seconds,
                    timestamp_hms=timestamp_hms,
                    frame_number=frame_number,
                    confidence_summary=1.0,
                    camera_id=camera_id,
                    related_keyframe_path=keyframe_path
                ))

    def filter_to_confirmed_tracks(self, confirmed_track_ids: Set[str]):
        """Purge events associated with unconfirmed / spurious transient detections."""
        self.events = [
            ev for ev in self.events
            if ev.track_id is None or ev.track_id in confirmed_track_ids
        ]

    def evaluate_completed_tracks(self, tracks: Dict[str, TrackSummary], total_frames: int = 0):
        """Generate exit events and prolonged duration events from completed confirmed tracks."""
        for tid, t in tracks.items():
            # Prolonged visibility event
            if t.visible_duration_seconds >= self.dwell_threshold and tid not in self.prolonged_tracks:
                self.prolonged_tracks.add(tid)
                mins = int(t.last_seen_seconds // 60)
                secs = int(t.last_seen_seconds % 60)
                millis = int(round((t.last_seen_seconds - int(t.last_seen_seconds)) * 1000))
                self.events.append(CCTVEvent(
                    event_id=self._next_event_id(),
                    event_type="VISIBLE_MORE_THAN_DURATION",
                    description=f"{tid} visible for more than configurable duration",
                    track_id=tid,
                    timestamp_seconds=t.last_seen_seconds,
                    timestamp_hms=f"{mins:02d}:{secs:02d}.{millis:03d}",
                    frame_number=t.last_frame,
                    confidence_summary=t.avg_confidence,
                    camera_id=t.camera_id,
                    related_keyframe_path=t.last_keyframe or t.best_keyframe
                ))

            # Exit event: Only emit if the track was genuinely tracked across >= 2 detections
            # AND actually exited before the video stream ended (not merely visible when recording stopped)
            is_multi_frame = total_frames > 2
            exited_before_end = (t.last_frame < max(0, total_frames - 2)) if is_multi_frame else False
            if t.total_detections >= 2 and exited_before_end:
                mins = int(t.last_seen_seconds // 60)
                secs = int(t.last_seen_seconds % 60)
                millis = int(round((t.last_seen_seconds - int(t.last_seen_seconds)) * 1000))
                self.events.append(CCTVEvent(
                    event_id=self._next_event_id(),
                    event_type="EXITED_CAMERA_VIEW",
                    description=f"{tid} exited camera view",
                    track_id=tid,
                    timestamp_seconds=t.last_seen_seconds,
                    timestamp_hms=f"{mins:02d}:{secs:02d}.{millis:03d}",
                    frame_number=t.last_frame,
                    confidence_summary=t.avg_confidence,
                    camera_id=t.camera_id,
                    related_keyframe_path=t.last_keyframe
                ))

    def get_events(self) -> List[CCTVEvent]:
        """Return chronological list of extracted events."""
        return sorted(self.events, key=lambda e: (e.timestamp_seconds, e.frame_number))
