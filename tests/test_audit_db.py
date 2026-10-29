"""
Unit tests for append-only SQLite WAL forensic audit database.
"""

from pathlib import Path
from src.common.audit_db import AuditDatabase


def test_audit_db_workflow(tmp_path: Path):
    db_file = tmp_path / "test_audit.db"
    db = AuditDatabase(db_path=db_file)

    # 1. Register evidence
    eid = db.register_evidence(
        original_filename="cctv_sample_01.mp4",
        original_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_type="video",
        file_size_bytes=1048576,
        original_path=str(tmp_path / "cctv_sample_01.mp4"),
        working_copy_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        working_copy_path=str(tmp_path / "working_cctv.mp4"),
        metadata={"fps": 30.0, "duration": 10.0},
    )
    assert eid is not None

    # 2. Start processing run
    rid = db.start_processing_run(
        evidence_id=eid,
        module_name="cctv_object_tracking",
        model_name="yolov8n",
        model_version="8.1.0",
        config={"conf_thresh": 0.35},
        seed=42,
    )
    assert rid is not None

    # 3. Append audit events
    event_id1 = db.log_event(
        run_id=rid,
        evidence_id=eid,
        stage_name="frame_extraction",
        action="extracted_300_frames",
        details={"extracted_count": 300},
    )
    assert event_id1 > 0

    event_id2 = db.log_event(
        run_id=rid,
        evidence_id=eid,
        stage_name="enhancement",
        action="applied_clahe_contrast",
        output_sha256="abcd1234abcd1234",
    )
    assert event_id2 > event_id1

    # 4. Complete run with metrics
    db.complete_run(
        run_id=rid,
        metrics={"total_detections": 15, "unique_tracks": 3},
    )

    # 5. Verify run history and audit trail
    runs = db.get_run_history(eid)
    assert len(runs) == 1
    assert runs[0]["status"] == "COMPLETED"
    assert runs[0]["seed"] == 42

    trail = db.get_audit_trail(rid)
    assert len(trail) == 2
    assert trail[0]["stage_name"] == "frame_extraction"
    assert trail[1]["stage_name"] == "enhancement"


def test_audit_db_failure_logging(tmp_path: Path):
    db_file = tmp_path / "test_fail_audit.db"
    db = AuditDatabase(db_path=db_file)

    eid = db.register_evidence(
        original_filename="corrupt.jpg",
        original_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        file_type="image",
        file_size_bytes=100,
        original_path="/tmp/corrupt.jpg",
    )

    rid = db.start_processing_run(
        evidence_id=eid,
        module_name="image_tampering",
        model_name="resnet18",
    )

    db.fail_run(rid, error_message="Image header corrupted; OpenCV decode returned None")

    runs = db.get_run_history(eid)
    assert len(runs) == 1
    assert runs[0]["status"] == "FAILED"
    assert "Image header corrupted" in runs[0]["error_message"]
