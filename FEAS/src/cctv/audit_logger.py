"""
CCTV SQLite Audit Logger.
Maintains forensic chain-of-custody and artifact provenance tables.
"""

from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from src.cctv.integrity import calculate_file_sha256


class CCTVAuditLogger:
    """Manages SQLite audit trail for CCTV evidence intake, runs, and artifacts."""

    def __init__(self, db_path: Path | str):
        """Initialize database connection and verify schemas."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Create the three required audit logging tables if not already existing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Evidence Files Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_files (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    original_sha256 TEXT NOT NULL,
                    original_size_bytes INTEGER NOT NULL,
                    upload_timestamp TEXT NOT NULL,
                    working_copy_path TEXT,
                    working_copy_sha256 TEXT
                )
            """)

            # 2. Processing Runs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_runs (
                    run_id TEXT PRIMARY KEY,
                    evidence_id TEXT NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    finish_timestamp TEXT,
                    status TEXT NOT NULL,
                    enhancement_mode TEXT NOT NULL,
                    frame_sampling TEXT NOT NULL,
                    yolo_model TEXT NOT NULL,
                    confidence_threshold REAL NOT NULL,
                    tracking_method TEXT NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY(evidence_id) REFERENCES evidence_files(evidence_id)
                )
            """)

            # 3. Processing Artifacts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    created_timestamp TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES processing_runs(run_id)
                )
            """)
            conn.commit()

    def record_evidence_intake(
        self,
        evidence_id: str,
        case_id: str,
        original_filename: str,
        original_path: str,
        original_sha256: str,
        original_size_bytes: int,
        working_copy_path: Optional[str] = None,
        working_copy_sha256: Optional[str] = None,
        upload_timestamp: Optional[str] = None
    ):
        """Record or update uploaded evidence information."""
        ts = upload_timestamp or datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evidence_files (
                    evidence_id, case_id, original_filename, original_path,
                    original_sha256, original_size_bytes, upload_timestamp,
                    working_copy_path, working_copy_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    working_copy_path=excluded.working_copy_path,
                    working_copy_sha256=excluded.working_copy_sha256
            """, (
                evidence_id, case_id, original_filename, original_path,
                original_sha256, original_size_bytes, ts,
                working_copy_path, working_copy_sha256
            ))
            conn.commit()

    def record_run_start(
        self,
        run_id: str,
        evidence_id: str,
        enhancement_mode: str,
        frame_sampling: str,
        yolo_model: str,
        confidence_threshold: float,
        tracking_method: str = "bytetrack"
    ):
        """Record commencement of an analytical processing run."""
        ts = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_runs (
                    run_id, evidence_id, start_timestamp, status,
                    enhancement_mode, frame_sampling, yolo_model,
                    confidence_threshold, tracking_method
                ) VALUES (?, ?, ?, 'RUNNING', ?, ?, ?, ?, ?)
            """, (
                run_id, evidence_id, ts, enhancement_mode,
                frame_sampling, yolo_model, confidence_threshold, tracking_method
            ))
            conn.commit()

    def record_run_finish(
        self,
        run_id: str,
        status: str = "COMPLETED",
        error_message: Optional[str] = None
    ):
        """Update a processing run record upon termination."""
        ts = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processing_runs
                SET finish_timestamp = ?, status = ?, error_message = ?
                WHERE run_id = ?
            """, (ts, status, error_message, run_id))
            conn.commit()

    def record_artifact(
        self,
        artifact_id: str,
        run_id: str,
        artifact_type: str,
        artifact_path: str,
        artifact_sha256: Optional[str] = None
    ):
        """Log a generated derived artifact (video, CSV, keyframe, report) with its SHA-256 hash."""
        p = Path(artifact_path)
        sha = artifact_sha256 or (calculate_file_sha256(p) if p.is_file() else "N/A")
        ts = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processing_artifacts (
                    artifact_id, run_id, artifact_type, artifact_path,
                    artifact_sha256, created_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (artifact_id, run_id, artifact_type, str(artifact_path), sha, ts))
            conn.commit()

    def get_run_audit_summary(self, run_id: str) -> Dict[str, Any]:
        """Fetch consolidated audit record for a given run ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM processing_runs WHERE run_id = ?", (run_id,))
            run_row = cursor.fetchone()
            if not run_row:
                return {}

            evidence_id = run_row["evidence_id"]
            cursor.execute("SELECT * FROM evidence_files WHERE evidence_id = ?", (evidence_id,))
            ev_row = cursor.fetchone()

            cursor.execute("SELECT * FROM processing_artifacts WHERE run_id = ?", (run_id,))
            art_rows = cursor.fetchall()

            return {
                "run": dict(run_row),
                "evidence": dict(ev_row) if ev_row else {},
                "artifacts": [dict(r) for r in art_rows]
            }

    def record_analysis_run(
        self,
        run_id: str,
        case_id: str,
        evidence_id: str,
        camera_id: str,
        original_sha256: str,
        working_copy_sha256: str,
        parameters: Dict[str, Any]
    ):
        """High-level initialization combining evidence intake and run commencement."""
        orig_path = parameters.get("original_path", "")
        file_size = parameters.get("file_size_bytes", 0)
        self.record_evidence_intake(
            evidence_id=evidence_id,
            case_id=case_id,
            original_filename=Path(orig_path).name if orig_path else f"{evidence_id}.mp4",
            original_path=str(orig_path),
            original_sha256=original_sha256,
            original_size_bytes=int(file_size),
            working_copy_path=parameters.get("working_copy_path"),
            working_copy_sha256=working_copy_sha256
        )
        self.record_run_start(
            run_id=run_id,
            evidence_id=evidence_id,
            enhancement_mode=parameters.get("enhancement_mode", "basic"),
            frame_sampling=parameters.get("analysis_mode", "fast_review"),
            yolo_model=parameters.get("yolo_model", "yolov8n.pt"),
            confidence_threshold=float(parameters.get("confidence_threshold", 0.40)),
            tracking_method=parameters.get("tracking_method", "bytetrack")
        )

    def record_step(self, *args, **kwargs):
        """Forensic step milestone logger hook."""
        pass
