"""
CCTV Results & Artifacts Exporter Module.
Exports Pandas CSV logs, JSON event structures, vehicle forensic registry,
collision incidents, suspicious activity logs, and executive forensic dossiers.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
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

VEHICLE_COLUMNS = [
    "evidence_id",
    "track_id",
    "vehicle_type",
    "estimated_body_type",
    "estimated_model_profile",
    "dominant_color",
    "color_confidence",
    "license_plate_number",
    "license_plate_confidence",
    "crash_involved",
    "crash_details",
    "suspicious_activities",
    "speed_estimate_px_s",
    "heading_degrees",
    "license_plate_crop_path",
    "vehicle_crop_path"
]

COLLISION_COLUMNS = [
    "incident_id",
    "frame_number",
    "timestamp_hms",
    "primary_track_id",
    "secondary_track_id",
    "collision_type",
    "impact_speed_delta_px_s",
    "severity_advisory",
    "description"
]

SUSPICIOUS_COLUMNS = [
    "alert_id",
    "track_id",
    "activity_type",
    "frame_number",
    "timestamp_hms",
    "severity_level",
    "speed_px_s",
    "heading_degrees",
    "description"
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


def export_vehicles_csv(
    vehicles: List[Dict[str, Any]],
    evidence_id: str,
    output_path: Path | str
) -> Path:
    """Export detailed vehicle forensic attribute registry to CSV."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for v in vehicles:
        rows.append({
            "evidence_id": evidence_id,
            "track_id": v.get("track_id", ""),
            "vehicle_type": v.get("vehicle_type", ""),
            "estimated_body_type": v.get("estimated_body_type", ""),
            "estimated_model_profile": v.get("estimated_model_profile", ""),
            "dominant_color": v.get("dominant_color", ""),
            "color_confidence": v.get("color_confidence", 0.0),
            "license_plate_number": v.get("license_plate_number") or "N/A",
            "license_plate_confidence": v.get("license_plate_confidence", 0.0),
            "crash_involved": "YES" if v.get("crash_involved") else "NO",
            "crash_details": "; ".join(v.get("crash_details", [])),
            "suspicious_activities": "; ".join(v.get("suspicious_activities", [])),
            "speed_estimate_px_s": v.get("speed_estimate_px_s", 0.0),
            "heading_degrees": v.get("heading_degrees", 0.0),
            "license_plate_crop_path": v.get("license_plate_crop_path", ""),
            "vehicle_crop_path": v.get("vehicle_crop_path", "")
        })

    df = pd.DataFrame(rows, columns=VEHICLE_COLUMNS)
    df.to_csv(out, index=False)
    return out


def export_collisions_csv(
    collisions: List[Dict[str, Any]],
    output_path: Path | str
) -> Path:
    """Export vehicle collision incident records to CSV."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for c in collisions:
        rows.append({
            "incident_id": c.get("incident_id", ""),
            "frame_number": c.get("frame_number", 0),
            "timestamp_hms": c.get("timestamp_hms", ""),
            "primary_track_id": c.get("primary_track_id", ""),
            "secondary_track_id": c.get("secondary_track_id", ""),
            "collision_type": c.get("collision_type", ""),
            "impact_speed_delta_px_s": c.get("impact_speed_delta_px_s", 0.0),
            "severity_advisory": c.get("severity_advisory", ""),
            "description": c.get("description", "")
        })

    df = pd.DataFrame(rows, columns=COLLISION_COLUMNS)
    df.to_csv(out, index=False)
    return out


def export_suspicious_csv(
    alerts: List[Dict[str, Any]],
    output_path: Path | str
) -> Path:
    """Export kinematic anomalies and suspicious vehicle behavior alerts to CSV."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for a in alerts:
        rows.append({
            "alert_id": a.get("alert_id", ""),
            "track_id": a.get("track_id", ""),
            "activity_type": a.get("activity_type", ""),
            "frame_number": a.get("frame_number", 0),
            "timestamp_hms": a.get("timestamp_hms", ""),
            "severity_level": a.get("severity_level", ""),
            "speed_px_s": a.get("speed_px_s", 0.0),
            "heading_degrees": a.get("heading_degrees", 0.0),
            "description": a.get("description", "")
        })

    df = pd.DataFrame(rows, columns=SUSPICIOUS_COLUMNS)
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
    output_path: Path | str,
    vehicles: Optional[List[Dict[str, Any]]] = None,
    collisions: Optional[List[Dict[str, Any]]] = None,
    suspicious_alerts: Optional[List[Dict[str, Any]]] = None
) -> Path:
    """Export comprehensive report-ready JSON dossier for the processed evidence."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    v_list = vehicles or []
    c_list = collisions or []
    s_list = suspicious_alerts or []

    class_counts: Dict[str, int] = {}
    for t in tracks.values():
        class_counts[t.class_name] = class_counts.get(t.class_name, 0) + 1

    summary = {
        "report_title": "CCTV Forensic Video Analysis & Vehicle Incident Dossier",
        "advisory_disclaimer": (
            "EXPERIMENTAL PROTOTYPE OUTPUT — NOT COURT EVIDENCE. "
            "All detections, vehicle classifications, license plate readings, collision "
            "heuristics, and kinematic anomaly alerts are automated advisory indicators. "
            "Requires human expert verification."
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
            "total_vehicles_profiled": len(v_list),
            "total_collisions_flagged": len(c_list),
            "total_suspicious_alerts": len(s_list),
            "total_events_extracted": len(events)
        },
        "vehicles": v_list,
        "collisions": c_list,
        "suspicious_activities": s_list,
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


def export_markdown_report(
    metadata: Dict[str, Any],
    tracks: Dict[str, TrackSummary],
    events: List[CCTVEvent],
    vehicles: List[Dict[str, Any]],
    collisions: List[Dict[str, Any]],
    suspicious_alerts: List[Dict[str, Any]],
    output_path: Path | str
) -> Path:
    """Generate high-readability executive Markdown report for forensic examiners."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# CCTV Forensic Video Analysis & Vehicle Incident Report",
        "",
        "> **Advisory Notice**: This analysis was produced by an automated educational/research prototype.",
        "> All vehicle make/model classifications, license plates, crash flags, and suspicious behavior",
        "> alerts are computer vision heuristics and require verification by certified forensic analysts.",
        "> Original evidence was preserved unmodified under cryptographic SHA-256 verification.",
        "",
        "## 1. Chain of Custody & Video Technical Integrity",
        f"- **Evidence ID**: `{metadata.get('evidence_id')}`",
        f"- **Case ID**: `{metadata.get('case_id')}`",
        f"- **Camera ID / Location**: `{metadata.get('camera_id')}` ({metadata.get('camera_location')})",
        f"- **Original File**: `{metadata.get('original_filename')}`",
        f"- **Original SHA-256**: `{metadata.get('original_sha256')}`",
        f"- **Derived Copy SHA-256**: `{metadata.get('working_copy_sha256')}`",
        f"- **Resolution / FPS**: {metadata.get('resolution')} @ {metadata.get('fps')} FPS",
        f"- **Total Duration**: {metadata.get('duration_seconds')} seconds ({metadata.get('frame_count')} frames)",
        "",
        "## 2. Executive Incident Summary",
        f"- **Total Objects Tracked**: {len(tracks)}",
        f"- **Vehicles Profiled**: {len(vehicles)}",
        f"- **Crash / Collision Incidents**: {len(collisions)}",
        f"- **Suspicious Activity Alerts**: {len(suspicious_alerts)}",
        f"- **Total Spatio-temporal Events**: {len(events)}",
        ""
    ]

    # Collisions section
    if collisions:
        lines.extend([
            "## 3. 💥 Vehicle Crash & Collision Incidents",
            "| Incident ID | Timestamp | Vehicles Involved | Severity | Description |",
            "|---|---|---|---|---|"
        ])
        for c in collisions:
            p = c.get("primary_track_id", "")
            s = c.get("secondary_track_id", "") or "Obstacle"
            lines.append(f"| `{c.get('incident_id')}` | `{c.get('timestamp_hms')}` | `{p} & {s}` | **{c.get('severity_advisory')}** | {c.get('description')} |")
        lines.append("")
    else:
        lines.extend(["## 3. 💥 Vehicle Crash & Collision Incidents", "No collision dynamics or sudden impact decelerations detected in footage.", ""])

    # Suspicious Activity section
    if suspicious_alerts:
        lines.extend([
            "## 4. ⚠️ Suspicious Vehicle Behaviors & Kinematic Anomalies",
            "| Alert ID | Track ID | Anomaly Type | Timestamp | Severity | Details |",
            "|---|---|---|---|---|---|"
        ])
        for a in suspicious_alerts:
            lines.append(f"| `{a.get('alert_id')}` | `{a.get('track_id')}` | `{a.get('activity_type')}` | `{a.get('timestamp_hms')}` | {a.get('severity_level')} | {a.get('description')} |")
        lines.append("")
    else:
        lines.extend(["## 4. ⚠️ Suspicious Vehicle Behaviors", "No wrong-way movement, erratic swerving, or roadway halts detected.", ""])

    # Vehicle Table
    if vehicles:
        lines.extend([
            "## 5. 🚗 Vehicle Forensic Registry (ANPR, Make/Model, Paint Color)",
            "| Track ID | Type | Est. Body & Model Profile | Dominant Color | License Plate (OCR) | Crash? | Suspicious Flags |",
            "|---|---|---|---|---|---|---|"
        ])
        for v in vehicles:
            p_text = v.get("license_plate_number") or "N/A"
            p_conf = v.get("license_plate_confidence", 0.0)
            plate_fmt = f"`{p_text}` ({int(p_conf*100)}%)" if p_text != "N/A" else "Not Resolved"
            crash_fmt = "💥 **YES**" if v.get("crash_involved") else "No"
            susp_fmt = ", ".join(v.get("suspicious_activities", [])) or "None"
            lines.append(f"| `{v.get('track_id')}` | {v.get('vehicle_type')} | {v.get('estimated_model_profile')} | {v.get('dominant_color')} | {plate_fmt} | {crash_fmt} | {susp_fmt} |")
        lines.append("")

    with out.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out


def export_cctv_artifacts(
    results_dir: Path | str,
    evidence_id: str,
    metadata: Dict[str, Any],
    detections: List[Detection],
    tracks: Dict[str, TrackSummary],
    events: List[CCTVEvent],
    audit_summary: Optional[Dict[str, Any]] = None,
    vehicles: Optional[List[Dict[str, Any]]] = None,
    collisions: Optional[List[Dict[str, Any]]] = None,
    suspicious_alerts: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Path]:
    """Write all structured files to their designated directories under results/cctv/."""
    base = Path(results_dir)

    v_list = vehicles or []
    c_list = collisions or []
    s_list = suspicious_alerts or []

    meta_file = base / "metadata" / "video_metadata.json"
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    with meta_file.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    det_csv = export_detections_csv(detections, base / "detection_logs" / "detections.csv")
    trk_csv = export_tracks_csv(tracks, base / "detection_logs" / "tracks.csv")
    evt_json = export_events_json(events, base / "detection_logs" / "events.json")

    veh_csv = export_vehicles_csv(v_list, evidence_id, base / "detection_logs" / "vehicles.csv")
    col_csv = export_collisions_csv(c_list, base / "detection_logs" / "collisions.csv")
    susp_csv = export_suspicious_csv(s_list, base / "detection_logs" / "suspicious_activities.csv")

    audit_file = base / "detection_logs" / "audit_log.json"
    if audit_summary:
        with audit_file.open("w", encoding="utf-8") as f:
            json.dump(audit_summary, f, indent=2)

    summary_file = export_summary_json(
        metadata=metadata,
        tracks=tracks,
        events=events,
        output_path=base / "reports" / f"{evidence_id}_cctv_summary.json",
        vehicles=v_list,
        collisions=c_list,
        suspicious_alerts=s_list
    )

    report_md = export_markdown_report(
        metadata=metadata,
        tracks=tracks,
        events=events,
        vehicles=v_list,
        collisions=c_list,
        suspicious_alerts=s_list,
        output_path=base / "reports" / f"{evidence_id}_forensic_report.md"
    )

    return {
        "metadata_json": meta_file,
        "detections_csv": det_csv,
        "tracks_csv": trk_csv,
        "vehicles_csv": veh_csv,
        "collisions_csv": col_csv,
        "suspicious_csv": susp_csv,
        "events_json": evt_json,
        "audit_log_json": audit_file,
        "summary_json": summary_file,
        "report_md": report_md
    }
