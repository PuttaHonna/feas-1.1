"""
Unit tests for FEAS Firebase Cloud & Air-Gapped Integration Service
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.services.firebase_service import firebase_forensics, FirebaseForensicService

client = TestClient(app)


def test_firebase_service_status():
    """Test telemetry and Spark free-tier quota reporting."""
    status = firebase_forensics.get_status()
    assert "status" in status
    assert "mode" in status
    assert "free_tier" in status
    assert status["free_tier"]["plan"] == "Firebase Spark (Free)"
    assert status["auth_ready"] is True
    assert status["firestore_ready"] is True
    assert status["storage_ready"] is True


def test_firebase_token_verification():
    """Test token verification for offline / dev / mock tokens."""
    # Test valid dev token
    user = firebase_forensics.verify_token("demo-examiner-token")
    assert user["uid"] == "examiner_001"
    assert user["role"] == "lead_investigator"
    assert "email" in user

    # Test empty token raises error
    with pytest.raises(ValueError):
        firebase_forensics.verify_token("")


def test_firestore_case_and_audit():
    """Test Firestore case creation, retrieval, and immutable audit logs."""
    case_id = "CASE-TEST-FB-001"
    case_data = {
        "title": "CCTV Evidence Tamper Investigation",
        "investigator": "Forensic Officer Alice",
        "status": "OPEN",
    }
    saved = firebase_forensics.save_case(case_id, case_data)
    assert saved["case_id"] == case_id
    assert saved["title"] == case_data["title"]

    retrieved = firebase_forensics.get_case(case_id)
    assert retrieved is not None
    assert retrieved["case_id"] == case_id

    # Audit event
    event = firebase_forensics.log_audit_event(
        case_id=case_id,
        event_type="HASH_VERIFIED",
        details={"sha256": "abcdef1234567890"},
        user="Officer Alice",
    )
    assert event["event_type"] == "HASH_VERIFIED"
    assert event["case_id"] == case_id

    trail = firebase_forensics.get_audit_trail(case_id)
    assert len(trail) >= 1
    assert any(e["event_type"] == "HASH_VERIFIED" for e in trail)


def test_storage_upload_bytes():
    """Test binary upload to Cloud / Mock storage."""
    dummy_pdf = b"%PDF-1.4 Mock Court Admissible Report"
    upload_res = firebase_forensics.upload_bytes(
        data=dummy_pdf,
        destination_blob="cases/CASE-TEST-FB-001/reports/test_summary.pdf",
        content_type="application/pdf",
    )
    assert "url" in upload_res
    assert upload_res["size_bytes"] == len(dummy_pdf)
    assert upload_res["content_type"] == "application/pdf"


def test_api_firebase_status_endpoint():
    """Test FastAPI /api/v1/firebase/status endpoint."""
    resp = client.get("/api/v1/firebase/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_ready"] is True
    assert "free_tier" in data


def test_api_firebase_auth_verify_endpoint():
    """Test FastAPI /api/v1/firebase/auth/verify endpoint."""
    resp = client.post("/api/v1/firebase/auth/verify", json={"token": "demo-examiner-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "AUTHENTICATED"
    assert body["user"]["uid"] == "examiner_001"


def test_api_firebase_case_lifecycle():
    """Test case creation and audit retrieval via REST API."""
    case_payload = {
        "case_id": "CASE-REST-001",
        "title": "REST API Forensic Case",
        "investigator": "Analyst Bob",
        "status": "OPEN",
    }
    resp = client.post("/api/v1/firebase/cases", json=case_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "CASE-REST-001"

    # Get Case
    resp_get = client.get("/api/v1/firebase/cases/CASE-REST-001")
    assert resp_get.status_code == 200
    assert resp_get.json()["title"] == "REST API Forensic Case"

    # Add audit log
    resp_audit = client.post(
        "/api/v1/firebase/cases/CASE-REST-001/audit",
        json={
            "event_type": "CCTV_KEYFRAME_EXTRACTED",
            "details": {"frame_count": 240, "fps": 30},
            "user": "Analyst Bob",
        },
    )
    assert resp_audit.status_code == 200

    # Get audit trail
    resp_trail = client.get("/api/v1/firebase/cases/CASE-REST-001/audit")
    assert resp_trail.status_code == 200
    assert len(resp_trail.json()) >= 1


def test_user_profile_and_analysis_history():
    """Test creating user profile and recording per-user analyses."""
    user_id = "agent_007"
    profile = {
        "user_id": user_id,
        "display_name": "Special Agent Bond",
        "email": "agent007@mi6.gov",
        "role": "lead_investigator",
        "badge_number": "MI6-007",
        "clearance": "Top Secret",
    }
    saved_prof = firebase_forensics.save_user_profile(user_id, profile)
    assert saved_prof["user_id"] == user_id
    assert saved_prof["display_name"] == "Special Agent Bond"

    fetched_prof = firebase_forensics.get_user_profile(user_id)
    assert fetched_prof["badge_number"] == "MI6-007"

    # Save Analysis to User's History
    analysis_record = {
        "module": "Tampering",
        "verdict": "INTEGRITY VERIFIED",
        "confidence": 99.2,
        "evidence_name": "cctv_frame_042.jpg",
        "findings": {"tamper_score": 0.01},
    }
    saved_anl = firebase_forensics.save_user_analysis(user_id, analysis_record)
    assert "analysis_id" in saved_anl
    assert saved_anl["user_id"] == user_id

    # Retrieve User's History
    history = firebase_forensics.get_user_analyses(user_id)
    assert len(history) >= 1
    assert any(h["verdict"] == "INTEGRITY VERIFIED" for h in history)


def test_api_user_history_endpoints():
    """Test user profile and history endpoints over FastAPI REST."""
    user_id = "examiner_sarah"
    
    # Create profile
    resp_prof = client.post(
        f"/api/v1/firebase/users/{user_id}/profile",
        json={
            "user_id": user_id,
            "display_name": "Sarah Connor",
            "email": "sconnor@forensics.local",
            "role": "ballistics_specialist",
            "badge_number": "FEAS-9921",
            "clearance": "Judicial Specialist",
        },
    )
    assert resp_prof.status_code == 200
    assert resp_prof.json()["display_name"] == "Sarah Connor"

    # Record analysis
    resp_anl = client.post(
        f"/api/v1/firebase/users/{user_id}/history",
        json={
            "module": "Bullet",
            "verdict": "9mm Parabellum Match",
            "confidence": 94.5,
            "evidence_name": "spent_casing_01.png",
            "findings": {"caliber": "9mm", "rifling": "6R"},
        },
    )
    assert resp_anl.status_code == 200
    anl_id = resp_anl.json()["analysis_id"]

    # Fetch History
    resp_hist = client.get(f"/api/v1/firebase/users/{user_id}/history")
    assert resp_hist.status_code == 200
    history_items = resp_hist.json()
    assert len(history_items) >= 1
    assert any(h["analysis_id"] == anl_id for h in history_items)

    # Delete History Entry
    resp_del = client.delete(f"/api/v1/firebase/users/{user_id}/history/{anl_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "DELETED"


def test_court_pdf_affidavit_generation():
    """Test generating official court-admissible PDF affidavit for analysis record."""
    from pathlib import Path
    from fastapi.testclient import TestClient
    from src.main import app
    from src.reports.pdf_generator import build_user_analysis_affidavit

    # 1. Direct function test
    sample_record = {
        "analysis_id": "TEST-AFFIDAVIT-001",
        "case_id": "CASE-TEST-2026",
        "module": "tampering",
        "verdict": "FORGED",
        "confidence": 0.97,
        "evidence_name": "forged_check.png",
        "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "findings": {"ela_anomaly": "High error rate", "spliced_regions": 2}
    }
    sample_profile = {
        "user_id": "examiner_001",
        "display_name": "Special Agent Alice Vance",
        "role": "Lead Forensic Investigator",
        "badge_number": "FEAS-8842",
        "clearance_level": "Level 5"
    }

    res = build_user_analysis_affidavit(sample_record, sample_profile)
    assert res is not None
    assert Path(res["pdf_path"]).exists()
    assert len(res["pdf_sha256"]) == 64
    assert res["analysis_id"] == "TEST-AFFIDAVIT-001"

    # 2. Test endpoint GET
    client = TestClient(app)
    get_res = client.get("/api/v1/firebase/users/examiner_001/history/TEST-AFFIDAVIT-001/pdf")
    assert get_res.status_code == 200
    assert get_res.headers["content-type"] == "application/pdf"
    assert "X-PDF-SHA256" in get_res.headers
    assert get_res.headers["X-Court-Compliance"] == "FRE-702-Daubert-ISO17025"
    assert len(get_res.content) > 1000  # Non-empty PDF binary

    # 3. Test endpoint POST
    post_res = client.post(
        "/api/v1/firebase/reports/generate-affidavit",
        json={
            "analysis_record": sample_record,
            "user_profile": sample_profile,
            "upload_to_cloud": False
        }
    )
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["status"] == "GENERATED"
    assert post_data["analysis_id"] == "TEST-AFFIDAVIT-001"
    assert len(post_data["pdf_sha256"]) == 64


