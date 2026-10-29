"""
Append-Only SQLite WAL Forensic Audit Database
Maintains an immutable chain of custody, evidence ledger, run registry, and granular event logs.
Strictly adheres to digital forensic integrity principles.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.common.config import FORENSIC_CONFIG


def get_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class AuditDatabase:
    """
    Forensic SQLite Audit Database using WAL mode.
    Guarantees that audit trails are append-only.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or FORENSIC_CONFIG.AUDIT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize schema with ledger, processing runs, and append-only audit events."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS evidence_ledger (
                evidence_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                original_sha256 TEXT NOT NULL,
                working_copy_sha256 TEXT,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                ingested_at_utc TEXT NOT NULL,
                original_path TEXT NOT NULL,
                working_copy_path TEXT,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS processing_runs (
                run_id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                module_name TEXT NOT NULL,
                model_name TEXT,
                model_version TEXT,
                config_json TEXT,
                seed INTEGER,
                started_at_utc TEXT NOT NULL,
                completed_at_utc TEXT,
                status TEXT NOT NULL, -- 'PENDING', 'COMPLETED', 'FAILED'
                error_message TEXT,
                metrics_json TEXT,
                FOREIGN KEY (evidence_id) REFERENCES evidence_ledger(evidence_id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                action TEXT NOT NULL,
                input_sha256 TEXT,
                output_sha256 TEXT,
                artifact_path TEXT,
                details_json TEXT,
                FOREIGN KEY (run_id) REFERENCES processing_runs(run_id),
                FOREIGN KEY (evidence_id) REFERENCES evidence_ledger(evidence_id)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_events(run_id);
            CREATE INDEX IF NOT EXISTS idx_audit_evidence ON audit_events(evidence_id);
            CREATE INDEX IF NOT EXISTS idx_runs_evidence ON processing_runs(evidence_id);
            """)

    def register_evidence(
        self,
        original_filename: str,
        original_sha256: str,
        file_type: str,
        file_size_bytes: int,
        original_path: str,
        working_copy_sha256: Optional[str] = None,
        working_copy_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        evidence_id: Optional[str] = None,
    ) -> str:
        """Register a new piece of evidence into the ledger."""
        eid = evidence_id or str(uuid.uuid4())
        now = get_utc_iso()
        meta_str = json.dumps(metadata or {})

        with self._get_connection() as conn:
            cur = conn.execute("SELECT evidence_id FROM evidence_ledger WHERE evidence_id = ?", (eid,))
            if cur.fetchone():
                return eid

            conn.execute(
                """
                INSERT INTO evidence_ledger (
                    evidence_id, original_filename, original_sha256, working_copy_sha256,
                    file_type, file_size_bytes, ingested_at_utc, original_path,
                    working_copy_path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    original_filename,
                    original_sha256,
                    working_copy_sha256,
                    file_type,
                    file_size_bytes,
                    now,
                    str(original_path),
                    str(working_copy_path) if working_copy_path else None,
                    meta_str,
                ),
            )
        return eid

    def start_processing_run(
        self,
        evidence_id: str,
        module_name: str,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> str:
        """Start a new processing run attached to registered evidence."""
        rid = run_id or str(uuid.uuid4())
        now = get_utc_iso()
        cfg_str = json.dumps(config or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO processing_runs (
                    run_id, evidence_id, module_name, model_name,
                    model_version, config_json, seed, started_at_utc, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    rid,
                    evidence_id,
                    module_name,
                    model_name,
                    model_version,
                    cfg_str,
                    seed,
                    now,
                ),
            )
        return rid

    def log_event(
        self,
        run_id: str,
        evidence_id: str,
        stage_name: str,
        action: str,
        input_sha256: Optional[str] = None,
        output_sha256: Optional[str] = None,
        artifact_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Append an immutable audit event to the log."""
        now = get_utc_iso()
        details_str = json.dumps(details or {})

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_events (
                    run_id, evidence_id, timestamp_utc, stage_name,
                    action, input_sha256, output_sha256, artifact_path, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    evidence_id,
                    now,
                    stage_name,
                    action,
                    input_sha256,
                    output_sha256,
                    str(artifact_path) if artifact_path else None,
                    details_str,
                ),
            )
            return cursor.lastrowid

    def complete_run(
        self,
        run_id: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a processing run as COMPLETED with actual metrics."""
        now = get_utc_iso()
        metrics_str = json.dumps(metrics or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE processing_runs
                SET completed_at_utc = ?, status = 'COMPLETED', metrics_json = ?
                WHERE run_id = ?
                """,
                (now, metrics_str, run_id),
            )

    def fail_run(
        self,
        run_id: str,
        error_message: str,
    ) -> None:
        """Mark a processing run as FAILED with the exact error message."""
        now = get_utc_iso()

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE processing_runs
                SET completed_at_utc = ?, status = 'FAILED', error_message = ?
                WHERE run_id = ?
                """,
                (now, error_message, run_id),
            )

    def get_run_history(self, evidence_id: str) -> List[Dict[str, Any]]:
        """Fetch all processing runs for a given evidence ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM processing_runs WHERE evidence_id = ? ORDER BY started_at_utc ASC
                """,
                (evidence_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_audit_trail(self, run_id: str) -> List[Dict[str, Any]]:
        """Fetch chronological audit events for a given run ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM audit_events WHERE run_id = ? ORDER BY event_id ASC
                """,
                (run_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
