"""
CCTV Results & Artifacts Exporter Module.
Exports Pandas CSV logs, JSON event structures, keyframe galleries, and executive summaries.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.cctv.detector import Detection
from src.cctv.event_extractor import CCTVEvent
from src.cctv.tracker import TrackSummary

DETECTION_COLUMNS = [
    "evidence_id",
    "camera_id",
    "frame_number",
    "timestamp_seconds",
    "timestamp_hms",
    "track_id",
    "class_name",
    "class_id",
    "confidence",
    "x1",
    "y1",
    "x2",
    "y2",
    "width",
    "height",
    "centroid_x",
    "centroid_y",
    "keyframe_path"
]

TRACK_COLUMNS = [
    "evidence_id",
    "camera_id",
    "track_id",
    "class_name",
    "first_seen_seconds",
    "last_seen_seconds",
    "visible_duration_seconds",
    "first_frame",
    "last_frame",
    "max_confidence",
    "avg_confidence",
    "first_keyframe",
    "best_keyframe",
    "last_keyframe"
]


def export_detections_csv(
    detections: List[Detection],
    output_path: Path | str
) -> Path:
    """Export frame-level detections conforming strictly to requested CSV schema."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for d in detections:
        rows.append({
            "evidence_id": d.evidence_id,
            "camera_id": d.camera_id,
            "frame_number": d.frame_number,
            "timestamp_seconds": d.timestamp_seconds,
            "timestamp_hms": d.timestamp_hms,
            "track_id": d.track_id or "unassigned",
            "class_name": d.class_name,
            "class_id": d.class_id,
            "confidence": d.confidence,
            "x1": d.x1,
            "y1": d.y1,
            "x2": d.x2,
            "y2": d.y2,
            "width": d.width,
            "height": d.height,
            "centroid_x": d.centroid_x,
            "centroid_y": d.centroid_y,
            "keyframe_path": d.keyframe_path or ""
        })

    df = pd.DataFrame(rows, columns=DETECTION_COLUMNS)
    df.to_csv(out, index=False)
    return out


def export_tracks_csv(
    tracks: Dict[str, TrackSummary],
    output_path: Path | str
) -> Path:
    """Export aggregated object track life cycles conforming to requested CSV schema."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for t in tracks.values():
        rows.append({
            "evidence_id": t.evidence_id,
            "camera_id": t.camera_id,
            "track_id": t.track_id,
            "class_name": t.class_name,
            "first_seen_seconds": t.first_seen_seconds,
            "last_seen_seconds": t.last_seen_seconds,
            "visible_duration_seconds": t.visible_duration_seconds,
            "first_frame": t.first_frame,
            "last_frame": t.last_frame,
            "max_confidence": t.max_confidence,
            "avg_confidence": t.avg_confidence,
            "first_keyframe": t.first_keyframe or "",
            "best_keyframe": t.best_keyframe or "",
            "last_keyframe": t.last_keyframe or ""
        })

    df = pd.DataFrame(rows, columns=TRACK_COLUMNS)
    df.to_csv(out, index=False)
    return out


def export_events_json(
    events: List[CCTVEvent],
    output_path: Path | str
) -> Path:
    """Export structured list of low-risk objective events to JSON."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    data = [e.to_dict() for e in events]
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out


def export_summary_json(
    metadata: Dict[str, Any],
    tracks: Dict[str, TrackSummary],
    events: List[CCTVEvent],
    output_path: Path | str
) -> Path:
    """Export comprehensive report-ready JSON dossier for the processed evidence."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    class_counts: Dict[str, int] = {}
    for t in tracks.values():
        class_counts[t.class_name] = class_counts.get(t.class_name, 0) + 1

    summary = {
        "report_title": "CCTV Derived Video Analysis Summary",
        "advisory_disclaimer": (
            "EXPERIMENTAL PROTOTYPE OUTPUT — NOT COURT EVIDENCE. "
            "All detections, tracks, and events are automated heuristic indicators. "
            "No identity verification, suspect matching, or intent is asserted."
        ),
        "evidence_id": metadata.get("evidence_id"),
        "case_id": metadata.get("case_id"),
        "camera_id": metadata.get("camera_id"),
        "camera_location": metadata.get("camera_location"),
        "original_filename": metadata.get("original_filename"),
        "original_sha256": metadata.get("original_sha256"),
        "working_copy_sha256": metadata.get("working_copy_sha256"),
        "video_metrics": {
            "resolution": metadata.get("resolution"),
            "fps": metadata.get("fps"),
            "frame_count": metadata.get("frame_count"),
            "duration_seconds": metadata.get("duration_seconds")
        },
        "analytics_metrics": {
            "total_unique_tracks": len(tracks),
            "object_class_distribution": class_counts,
            "total_events_extracted": len(events)
        },
        "tracks": [
            {
                "track_id": t.track_id,
                "class_name": t.class_name,
                "visible_duration_seconds": t.visible_duration_seconds,
                "max_confidence": t.max_confidence,
                "first_seen": t.first_seen_seconds,
                "last_seen": t.last_seen_seconds
            }
            for t in tracks.values()
        ],
        "events": [e.to_dict() for e in events]
    }

    with out.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return out


def export_cctv_artifacts(
    results_dir: Path | str,
    evidence_id: str,
    metadata: Dict[str, Any],
    detections: List[Detection],
    tracks: Dict[str, TrackSummary],
    events: List[CCTVEvent],
    audit_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Path]:
    """Write all structured files to their designated directories under results/cctv/."""
    base = Path(results_dir)

    meta_file = base / "metadata" / "video_metadata.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with meta_file.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    det_csv = export_detections_csv(detections, base / "detection_logs" / "detections.csv")
    trk_csv = export_tracks_csv(tracks, base / "detection_logs" / "tracks.csv")
    evt_json = export_events_json(events, base / "detection_logs" / "events.json")

    audit_file = base / "detection_logs" / "audit_log.json"
    if audit_summary:
        with audit_file.open("w", encoding="utf-8") as f:
            json.dump(audit_summary, f, indent=2)

    summary_file = export_summary_json(
        metadata,
        tracks,
        events,
        base / "reports" / f"{evidence_id}_cctv_summary.json"
    )

    return {
        "metadata_json": meta_file,
        "detections_csv": det_csv,
        "tracks_csv": trk_csv,
        "events_json": evt_json,
        "audit_log_json": audit_file,
        "summary_json": summary_file
    }
