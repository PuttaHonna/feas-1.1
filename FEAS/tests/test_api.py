"""
Integration Tests for FastAPI Endpoints
Tests health check, multipart analysis endpoint, video processing, case querying, and PDF report delivery.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.config import FIXTURES_DIR
from src.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health telemetry endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "cuda_available" in data
    assert "device" in data


def test_list_suspects_endpoint():
    """Verify suspect gallery endpoint returns seeded profiles."""
    response = client.get("/api/v1/suspects")
    assert response.status_code == 200
    suspects = response.json()
    assert isinstance(suspects, list)
    assert len(suspects) >= 3
    assert "suspect_id" in suspects[0]
    assert "embedding" in suspects[0]


def test_list_cases_endpoint():
    """Verify listing recent cases."""
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)


def test_analyze_endpoint_with_sample_image():
    """Verify end-to-end multipart evidence analysis for images."""
    sample_path = FIXTURES_DIR / "sample.jpg"
    assert sample_path.exists()

    with open(sample_path, "rb") as f:
        files = {"file": ("sample.jpg", f, "image/jpeg")}
        data = {
            "investigator_name": "Forensic Examiner",
            "operator_notes": "Integration test analysis run."
        }
        response = client.post("/api/v1/analyze", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert "case_id" in res
    assert "input_sha256" in res
    assert "forgery" in res
    assert "face" in res
    assert "wound" in res
    assert "ballistics" in res
    assert "verdict" in res
    assert res["status"] == "COMPLETED"

    case_id = res["case_id"]

    # Verify GET /api/v1/cases/{case_id}
    case_resp = client.get(f"/api/v1/cases/{case_id}")
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["case_id"] == case_id
    assert "audit_trail" in case_data
    assert len(case_data["audit_trail"]) > 0

    # Verify GET /api/v1/cases/{case_id}/report
    report_resp = client.get(f"/api/v1/cases/{case_id}/report")
    assert report_resp.status_code == 200
    assert report_resp.headers["content-type"] == "application/pdf"
    assert len(report_resp.content) > 1000


def test_analyze_endpoint_with_sample_video():
    """Verify end-to-end multipart evidence analysis for video media (1fps keyframes)."""
    video_path = FIXTURES_DIR / "sample_video.mp4"
    assert video_path.exists()

    with open(video_path, "rb") as f:
        files = {"file": ("sample_video.mp4", f, "video/mp4")}
        data = {
            "investigator_name": "Forensic Examiner",
            "operator_notes": "Surveillance video keyframe analysis."
        }
        response = client.post("/api/v1/analyze", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert res["is_video"] is True
    assert len(res["keyframes"]) >= 1
    assert "forgery" in res
    assert "deepfake" in res
    assert "audio" in res
    assert res["status"] == "COMPLETED"


def test_analyze_deepfake_endpoint():
    """Verify dedicated POST /api/v1/analyze/deepfake endpoint."""
    df_path = FIXTURES_DIR / "deepfake_sample.png"
    assert df_path.exists()

    with open(df_path, "rb") as f:
        files = {"file": ("deepfake_sample.png", f, "image/png")}
        response = client.post("/api/v1/analyze/deepfake", files=files)

    assert response.status_code == 200
    res = response.json()
    assert "deepfake_score" in res
    assert "model_attribution" in res
    assert "fft_metrics" in res


def test_analyze_audio_endpoint():
    """Verify dedicated POST /api/v1/analyze/audio endpoint."""
    audio_path = FIXTURES_DIR / "sample_audio.wav"
    assert audio_path.exists()

    with open(audio_path, "rb") as f:
        files = {"file": ("sample_audio.wav", f, "audio/wav")}
        response = client.post("/api/v1/analyze/audio", files=files)

    assert response.status_code == 200
    res = response.json()
    assert res["has_audio"] is True
    assert "synthetic_voice_score" in res
    assert "snr_db" in res


def test_analyze_metadata_endpoint():
    """Verify dedicated POST /api/v1/analyze/metadata endpoint."""
    df_path = FIXTURES_DIR / "deepfake_sample.png"
    assert df_path.exists()

    with open(df_path, "rb") as f:
        files = {"file": ("deepfake_sample.png", f, "image/png")}
        response = client.post("/api/v1/analyze/metadata", files=files)

    assert response.status_code == 200
    res = response.json()
    assert res["valid_file"] is True
    assert res["ai_generation_detected"] is True

