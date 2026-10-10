"""
Forensic Evidence Analysis System (FEAS) - SQLite WAL Audit Trail & Database
Maintains court-admissible, immutable audit logs and suspect profiles.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite
from src.config import DB_PATH


def get_utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def get_sync_connection() -> sqlite3.Connection:
    """Return a synchronous SQLite connection with WAL mode enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the SQLite database schema synchronously."""
    target_path = str(db_path or DB_PATH)
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            investigator_name TEXT DEFAULT 'Forensic Analyst',
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            output_sha256 TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            verdict TEXT,
            summary_json TEXT,
            operator_notes TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            input_sha256 TEXT,
            output_sha256 TEXT,
            exif_data TEXT,
            confidence_scores TEXT,
            details_json TEXT,
            operator_notes TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS suspect_profiles (
            suspect_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            image_path TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log (case_id);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp);
        """)

        # Populate initial suspect profiles if empty
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM suspect_profiles")
        count = cur.fetchone()[0]
        if count == 0:
            import numpy as np
            # Seed 3 mock suspects with deterministic 512-d normalized embeddings
            rng = np.random.RandomState(42)
            suspects = [
                ("SUSP-10492", "Marcus Vance", "Prior Grand Larceny, subject spotted near sector 4 CCTV."),
                ("SUSP-88301", "Elena Rostova", "Cyber forgery suspect, known alias 'ZeroTrace'."),
                ("SUSP-44219", "David Chen", "Person of interest in ballistic casing recovery."),
            ]
            for s_id, name, notes in suspects:
                raw_emb = rng.randn(512).astype(np.float32)
                norm_emb = (raw_emb / np.linalg.norm(raw_emb)).tolist()
                cur.execute(
                    """
                    INSERT INTO suspect_profiles (suspect_id, name, embedding_json, image_path, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (s_id, name, json.dumps(norm_emb), "", notes, get_utc_now_iso())
                )


async def async_init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database asynchronously."""
    target_path = str(db_path or DB_PATH)
    async with aiosqlite.connect(target_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            investigator_name TEXT DEFAULT 'Forensic Analyst',
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            output_sha256 TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            verdict TEXT,
            summary_json TEXT,
            operator_notes TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            input_sha256 TEXT,
            output_sha256 TEXT,
            exif_data TEXT,
            confidence_scores TEXT,
            details_json TEXT,
            operator_notes TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS suspect_profiles (
            suspect_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            image_path TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        """)
        await db.commit()


def create_case_sync(
    filename: str,
    file_type: str,
    input_sha256: str,
    investigator_name: str = "Forensic Analyst",
    operator_notes: str = "",
    case_id: Optional[str] = None
) -> str:
    """Create a new case record synchronously."""
    cid = case_id or str(uuid.uuid4())
    now = get_utc_now_iso()
    with get_sync_connection() as conn:
        conn.execute(
            """
            INSERT INTO cases (case_id, created_at, investigator_name, filename, file_type, input_sha256, status, operator_notes)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (cid, now, investigator_name, filename, file_type, input_sha256, operator_notes)
        )
        conn.commit()
    log_audit_event_sync(
        case_id=cid,
        action="CASE_CREATED",
        input_sha256=input_sha256,
        operator_notes=operator_notes,
        details={"filename": filename, "file_type": file_type, "investigator": investigator_name}
    )
    return cid


def log_audit_event_sync(
    case_id: str,
    action: str,
    input_sha256: Optional[str] = None,
    output_sha256: Optional[str] = None,
    exif_data: Optional[Dict[str, Any]] = None,
    confidence_scores: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    operator_notes: Optional[str] = None
) -> int:
    """Append an immutable audit log entry."""
    now = get_utc_now_iso()
    with get_sync_connection() as conn:
        cur = conn.cursor()
        # Ensure parent case exists to satisfy foreign key constraint
        cur.execute("SELECT 1 FROM cases WHERE case_id = ?", (case_id,))
        if not cur.fetchone():
            conn.execute(
                """
                INSERT OR IGNORE INTO cases (case_id, created_at, filename, file_type, input_sha256, status)
                VALUES (?, ?, 'mock_evidence.jpg', 'image', ?, 'PENDING')
                """,
                (case_id, now, input_sha256 or "0000000000000000000000000000000000000000000000000000000000000000")
            )
            conn.commit()

        cur.execute(
            """
            INSERT INTO audit_log (case_id, timestamp, action, input_sha256, output_sha256, exif_data, confidence_scores, details_json, operator_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                now,
                action,
                input_sha256,
                output_sha256,
                json.dumps(exif_data) if exif_data is not None else None,
                json.dumps(confidence_scores) if confidence_scores is not None else None,
                json.dumps(details) if details is not None else None,
                operator_notes
            )
        )
        conn.commit()
        return cur.lastrowid


def update_case_results_sync(
    case_id: str,
    status: str,
    verdict: str,
    summary: Dict[str, Any],
    output_sha256: Optional[str] = None
) -> None:
    """Update case status, verdict, and final summary synchronously."""
    with get_sync_connection() as conn:
        conn.execute(
            """
            UPDATE cases
            SET status = ?, verdict = ?, summary_json = ?, output_sha256 = ?
            WHERE case_id = ?
            """,
            (status, verdict, json.dumps(summary), output_sha256, case_id)
        )
        conn.commit()


def get_case_sync(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full case record synchronously."""
    with get_sync_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("summary_json"):
            try:
                res["summary"] = json.loads(res["summary_json"])
            except Exception:
                res["summary"] = {}
        return res


def get_audit_trail_sync(case_id: str) -> List[Dict[str, Any]]:
    """Retrieve all audit logs for a case."""
    with get_sync_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_log WHERE case_id = ? ORDER BY timestamp ASC", (case_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def list_cases_sync(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent cases."""
    with get_sync_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cases ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_suspect_profiles_sync() -> List[Dict[str, Any]]:
    """Retrieve all suspect gallery profiles."""
    with get_sync_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT suspect_id, name, embedding_json, image_path, notes, created_at FROM suspect_profiles")
        rows = cur.fetchall()
        suspects = []
        for r in rows:
            d = dict(r)
            d["embedding"] = json.loads(d["embedding_json"])
            suspects.append(d)
        return suspects
