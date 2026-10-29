"""
Unit and integration tests for FastAPI backend and ReportLab factual PDF generator.
"""

from pathlib import Path
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from src.api.main import app, audit_db
from src.common.report_generator import ForensicReportGenerator
from src.common.hashing import calculate_sha256
from src.common.config import FORENSIC_CONFIG

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "disclaimer" in data
    assert data["disclaimer"] == FORENSIC_CONFIG.MANDATORY_DISCLAIMER


def test_upload_evidence_endpoint(tmp_path: Path):
    # Create test JPEG in memory
    img = Image.new("RGB", (120, 120), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("test_upload_sample.jpg", buf, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "evidence_id" in data
    assert len(data["original_sha256"]) == 64
    assert len(data["working_copy_sha256"]) == 64
    assert data["status"] == "preserved_read_only"

    # Query audit trail
    trail_res = client.get(f"/api/v1/evidence/{data['evidence_id']}/audit-trail")
    assert trail_res.status_code == 200
    trail_data = trail_res.json()
    assert trail_data["evidence_id"] == data["evidence_id"]


def test_factual_pdf_report_generator(tmp_path: Path):
    report_gen = ForensicReportGenerator()
    out_pdf = tmp_path / "test_technical_report.pdf"

    pdf_path = report_gen.generate_pdf_report(
        output_path=out_pdf,
        case_id="CASE_TEST_2026",
        evidence_id="EV_TEST_123456",
        original_filename="source_sample.jpg",
        original_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        working_copy_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        timestamps_utc={"ingested_at": "2026-10-12T16:00:00Z"},
        actual_metadata={"width": 1920, "height": 1080, "channels": 3},
        module_results={
            "cctv": {
                "status": "completed",
                "model_version": "yolov8n",
                "metrics": {"frames_processed": 100, "total_detections": 25},
            },
            # "tampering" omitted to test "Module not run." handling
        },
        audit_events=[
            {
                "timestamp_utc": "2026-10-12T16:01:00Z",
                "stage_name": "evidence_intake",
                "action": "preserved_in_vault",
                "output_sha256": "e3b0c44298fc",
            }
        ],
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000  # Generated valid PDF
    pdf_sha = calculate_sha256(pdf_path)
    assert len(pdf_sha) == 64
