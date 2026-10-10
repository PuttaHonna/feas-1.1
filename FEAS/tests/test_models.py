"""
Comprehensive Unit Tests for Wave 2 Forensic AI Models:
1. Forgery Detection (ELA, VGG16, YOLO Localization)
2. Face Super-Resolution & 512-d FaceNet Matching
3. Multi-Head Wound Triage (EfficientNet)
4. Ballistics Striae Feature Matching (CNN)
"""

from pathlib import Path
import pytest
import numpy as np

from src.config import FIXTURES_DIR
from src.models.forgery.pipeline import run_forgery_check
from src.models.face.pipeline import process_face
from src.models.wound.efficientnet_triage import predict_wound
from src.models.ballistics.striae_cnn import analyze_striae


def test_forgery_pipeline():
    """Verify forgery detection returns valid tamper score, bboxes, and ELA image."""
    sample_img = FIXTURES_DIR / "sample.jpg"
    assert sample_img.exists()
    
    res = run_forgery_check(sample_img)
    assert "tamper_score" in res
    assert 0.0 <= res["tamper_score"] <= 1.0
    assert "bboxes" in res
    assert isinstance(res["bboxes"], list)
    assert "ela_metrics" in res
    assert Path(res["annotated_image_path"]).exists()
    assert Path(res["ela_image_path"]).exists()


def test_face_pipeline():
    """Verify face enhancement, 512-d embeddings, and suspect database matching."""
    cctv_img = FIXTURES_DIR / "cctv_crop.jpg"
    assert cctv_img.exists()

    res = process_face(cctv_img)
    assert res["face_detected"] is True
    assert res["restored_img"].shape == (1024, 1024, 3)
    assert len(res["embedding"]) == 512
    assert "matches" in res
    assert isinstance(res["matches"], list)
    assert Path(res["restored_image_path"]).exists()
    assert Path(res["comparison_image_path"]).exists()


def test_wound_pipeline():
    """Verify 4-head wound triage classifier."""
    wound_img = FIXTURES_DIR / "wound_sample.jpg"
    assert wound_img.exists()

    res = predict_wound(wound_img)
    assert res["wound_type"] in ["gunshot", "stab", "blunt", "burn"]
    assert 0.0 <= res["wound_type_confidence"] <= 1.0
    assert res["severity"] in ["minor", "moderate", "severe"]
    assert res["age"] in ["fresh", "1-day", "week old"]
    assert res["location"] in ["head", "torso", "limb"]
    assert Path(res["annotated_image_path"]).exists()


def test_ballistics_pipeline():
    """Verify ballistics striation texture classification."""
    bullet_img = FIXTURES_DIR / "bullet_sample.jpg"
    assert bullet_img.exists()

    res = analyze_striae(bullet_img)
    assert res["caliber"] in [".45ACP", "9mm", "5.56mm"]
    assert res["rifling"] in ["6R", "5L", "Polygonal"]
    assert res["manufacturer"] in ["Glock", "Beretta", "Colt", "Smith & Wesson", "SIG Sauer", "Unknown"]
    assert Path(res["striation_map_path"]).exists()
