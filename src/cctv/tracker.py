"""
Deterministic Forensic Multi-Object Tracker
Associates bounding boxes across frames using Hungarian/IoU matching.
Produces deterministic trajectories, continuous track IDs, and visibility records.
"""

from typing import List, Dict, Any, Optional
import numpy as np


def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """Computes Intersection over Union between two [x1, y1, x2, y2] bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])

    union = area1 + area2 - intersection
    return (intersection / union) if union > 0 else 0.0


class ForensicTracker:
    """
    Deterministic multi-object tracker based on spatial IoU proximity.
    Maintains track history, avoids non-deterministic heuristics.
    """

    def __init__(self, iou_threshold: float = 0.3, max_lost_frames: int = 20):
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.next_track_id = 1

        # Active tracks: {track_id: {"bbox": [...], "class_name": str, "lost_count": int, "last_timestamp": float, ...}}
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        # Completed track summaries: {track_id: summary_dict}
        self.track_summaries: Dict[int, Dict[str, Any]] = {}

    def update(
        self,
        detections: List[Dict[str, Any]],
        frame_idx: int,
        timestamp_sec: float,
    ) -> List[Dict[str, Any]]:
        """
        Updates tracks with detections from current frame.
        
        Returns:
            List of active track instances for the current frame.
        """
        updated_records: List[Dict[str, Any]] = []

        if not self.active_tracks:
            # Initialize tracks with current detections
            for det in detections:
                tid = self.next_track_id
                self.next_track_id += 1

                self.active_tracks[tid] = {
                    "track_id": tid,
                    "class_name": det["class_name"],
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                    "lost_count": 0,
                    "first_frame": frame_idx,
                    "last_frame": frame_idx,
                    "first_timestamp": timestamp_sec,
                    "last_timestamp": timestamp_sec,
                    "trajectory": [(frame_idx, timestamp_sec, det["bbox"])],
                }

                updated_records.append({
                    "track_id": tid,
                    "class_name": det["class_name"],
                    "frame_idx": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                })
            return updated_records

        # Match existing active tracks with current detections
        track_ids = list(self.active_tracks.keys())
        matched_track_ids = set()
        matched_detection_indices = set()

        # Build IoU cost matrix
        if detections and track_ids:
            cost_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)
            for t_idx, tid in enumerate(track_ids):
                for d_idx, det in enumerate(detections):
                    # Only match same class
                    if self.active_tracks[tid]["class_name"] == det["class_name"]:
                        cost_matrix[t_idx, d_idx] = calculate_iou(
                            self.active_tracks[tid]["bbox"], det["bbox"]
                        )
                    else:
                        cost_matrix[t_idx, d_idx] = 0.0

            # Greedy assignment by highest IoU above threshold
            while True:
                max_val = np.max(cost_matrix)
                if max_val < self.iou_threshold:
                    break

                t_idx, d_idx = np.unravel_index(np.argmax(cost_matrix), cost_matrix.shape)
                tid = track_ids[t_idx]

                # Assign match
                det = detections[d_idx]
                self.active_tracks[tid]["bbox"] = det["bbox"]
                self.active_tracks[tid]["confidence"] = det["confidence"]
                self.active_tracks[tid]["lost_count"] = 0
                self.active_tracks[tid]["last_frame"] = frame_idx
                self.active_tracks[tid]["last_timestamp"] = timestamp_sec
                self.active_tracks[tid]["trajectory"].append((frame_idx, timestamp_sec, det["bbox"]))

                updated_records.append({
                    "track_id": tid,
                    "class_name": det["class_name"],
                    "frame_idx": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                })

                matched_track_ids.add(tid)
                matched_detection_indices.add(d_idx)

                # Zero out row and column
                cost_matrix[t_idx, :] = -1.0
                cost_matrix[:, d_idx] = -1.0

        # Unmatched detections become new tracks
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_detection_indices:
                tid = self.next_track_id
                self.next_track_id += 1

                self.active_tracks[tid] = {
                    "track_id": tid,
                    "class_name": det["class_name"],
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                    "lost_count": 0,
                    "first_frame": frame_idx,
                    "last_frame": frame_idx,
                    "first_timestamp": timestamp_sec,
                    "last_timestamp": timestamp_sec,
                    "trajectory": [(frame_idx, timestamp_sec, det["bbox"])],
                }

                updated_records.append({
                    "track_id": tid,
                    "class_name": det["class_name"],
                    "frame_idx": frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "bbox": det["bbox"],
                    "confidence": det["confidence"],
                })

        # Increase lost_count on unmatched active tracks and prune expired tracks
        expired_tids = []
        for tid, track_info in self.active_tracks.items():
            if tid not in matched_track_ids and tid not in [r["track_id"] for r in updated_records]:
                track_info["lost_count"] += 1
                if track_info["lost_count"] > self.max_lost_frames:
                    expired_tids.append(tid)

        for tid in expired_tids:
            info = self.active_tracks.pop(tid)
            duration = round(info["last_timestamp"] - info["first_timestamp"], 2)
            self.track_summaries[tid] = {
                "track_id": tid,
                "class_name": info["class_name"],
                "first_frame": info["first_frame"],
                "last_frame": info["last_frame"],
                "first_timestamp": info["first_timestamp"],
                "last_timestamp": info["last_timestamp"],
                "duration_seconds": duration,
                "total_observations": len(info["trajectory"]),
            }

        return updated_records

    def finalize(self) -> Dict[int, Dict[str, Any]]:
        """Flush remaining active tracks to summaries."""
        for tid, info in list(self.active_tracks.items()):
            duration = round(info["last_timestamp"] - info["first_timestamp"], 2)
            self.track_summaries[tid] = {
                "track_id": tid,
                "class_name": info["class_name"],
                "first_frame": info["first_frame"],
                "last_frame": info["last_frame"],
                "first_timestamp": info["first_timestamp"],
                "last_timestamp": info["last_timestamp"],
                "duration_seconds": duration,
                "total_observations": len(info["trajectory"]),
            }
        self.active_tracks.clear()
        return self.track_summaries
