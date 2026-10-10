"""
Forensic Evidence Analysis System (FEAS) - Batch Triage Test Suite
Tests multi-file batch execution, batch reporting, and PDF integrity.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.config import FIXTURES_DIR, REPORTS_DIR
from src.main import app
from src.reports.batch_report import build_batch_pdf

client = TestClient(app)


def test_batch_analyze_endpoint():
    """Test POST /api/v1/analyze/batch with multiple images."""
    f1 = FIXTURES_DIR / "sample.jpg"
    f2 = FIXTURES_DIR / "cctv_crop.jpg"
    
    assert f1.exists() and f2.exists()
    
    files = [
        ("files", ("sample.jpg", open(f1, "rb"), "image/jpeg")),
        ("files", ("cctv_crop.jpg", open(f2, "rb"), "image/jpeg")),
    ]
    
    data = {
        "investigator_name": "Senior Batch Examiner",
        "operator_notes": "Batch test multi-evidence intake"
    }
    
    response = client.post("/api/v1/analyze/batch", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    
    assert "batch_id" in res_json
    assert res_json["batch_id"].startswith("BATCH-")
    assert "summary" in res_json
    assert res_json["summary"]["total_files"] == 2
    assert len(res_json["items"]) == 2
    assert "pdf_path" in res_json
    assert "pdf_sha256" in res_json
    assert len(res_json["pdf_sha256"]) == 64


def test_batch_pdf_generation_direct():
    """Test direct programmatic batch PDF creation."""
    mock_batch = {
        "batch_id": "BATCH-TEST-001",
        "investigator_name": "Test Examiner",
        "summary": {
            "total_files": 2,
            "tampered_count": 1,
            "tamper_rate": 0.5,
            "suspect_hits_count": 1,
            "wound_alerts_count": 0,
            "ballistics_alerts_count": 0,
            "average_seconds_per_file": 1.2
        },
        "items": [
            {
                "case_id": "FEAS-CASE-001",
                "filename": "sample_tampered.jpg",
                "input_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "forgery": {"is_tampered": True, "tamper_score": 0.88},
                "face": {"face_detected": False},
                "wound": {"wound_detected": False},
                "ballistics": {"striae_detected": False},
                "verdict": "TAMPERED"
            },
            {
                "case_id": "FEAS-CASE-002",
                "filename": "cctv_crop.jpg",
                "input_sha256": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "forgery": {"is_tampered": False, "tamper_score": 0.05},
                "face": {"face_detected": True, "top_match": {"name": "Marcus Vance", "similarity": 0.82}},
                "wound": {"wound_detected": False},
                "ballistics": {"striae_detected": False},
                "verdict": "AUTHENTIC"
            }
        ]
    }
    
    out_pdf = REPORTS_DIR / "FEAS_Batch_Triage_BATCH-TEST-001.pdf"
    res = build_batch_pdf(mock_batch, str(out_pdf))
    
    assert Path(res["pdf_path"]).exists()
    assert len(res["pdf_sha256"]) == 64
    assert res["batch_id"] == "BATCH-TEST-001"
