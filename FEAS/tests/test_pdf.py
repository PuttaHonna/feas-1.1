"""
Unit and Validation Tests for Court-Ready ReportLab PDF Generator
"""

import hashlib
from pathlib import Path
import pytest

from src.config import FIXTURES_DIR, REPORTS_DIR
from src.reports.pdf_generator import build_pdf


def test_build_court_pdf():
    """Verify PDF report generation, non-empty binary payload, and valid SHA-256 hash."""
    mock_case_path = FIXTURES_DIR / "mock_case_data.json"
    assert mock_case_path.exists()

    output_pdf = REPORTS_DIR / "test_verification_report.pdf"
    res = build_pdf(mock_case_path, output_pdf)

    assert "pdf_path" in res
    assert "pdf_sha256" in res
    assert Path(res["pdf_path"]).exists()

    # Verify SHA-256 matches actual generated file bytes
    with open(res["pdf_path"], "rb") as f:
        file_bytes = f.read()
    
    assert len(file_bytes) > 2000
    actual_hash = hashlib.sha256(file_bytes).hexdigest()
    assert res["pdf_sha256"] == actual_hash
