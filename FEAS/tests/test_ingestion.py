"""
Unit Tests for FEAS Ingestion, SHA-256 Hashing, Metadata, and Keyframe Extraction
"""

import hashlib
import json
from pathlib import Path
import pytest
from PIL import Image

from src.config import FIXTURES_DIR, TEMP_DIR
from src.pipeline.ingestion import (
    compute_sha256_bytes,
    compute_sha256_file,
    extract_video_keyframes,
    process_uploaded_media,
    validate_file
)
from src.pipeline.metadata import extract_metadata


def test_sha256_computation():
    """Verify SHA-256 calculation matches hashlib directly."""
    test_data = b"FORENSIC_INTEGRITY_TEST_PAYLOAD"
    expected = hashlib.sha256(test_data).hexdigest()
    assert compute_sha256_bytes(test_data) == expected


def test_file_validation():
    """Verify file format and size constraints."""
    # Valid
    ok, err = validate_file("evidence.jpg", 1024)
    assert ok is True
    assert err is None
    
    ok, err = validate_file("surveillance.mp4", 1024*1024)
    assert ok is True
    
    # Invalid extension
    ok, err = validate_file("payload.exe", 1024)
    assert ok is False
    assert "Unsupported file extension" in err

    # Oversized file (>500MB)
    ok, err = validate_file("massive.avi", 501 * 1024 * 1024)
    assert ok is False
    assert "exceeds 500 MB limit" in err


def test_exif_metadata_extraction():
    """Verify EXIF and GPS extraction from test fixture."""
    sample_path = FIXTURES_DIR / "sample.jpg"
    assert sample_path.exists()
    
    meta = extract_metadata(sample_path)
    assert meta["has_exif"] is True
    assert meta["device_make"] == "Nikon"
    assert meta["device_model"] == "D850-Forensic"
    assert meta["gps"] is not None
    assert pytest.approx(meta["gps"]["latitude"], 0.01) == 37.77
    assert pytest.approx(meta["gps"]["longitude"], 0.01) == -122.41


def test_video_keyframe_extraction():
    """Verify 1 frame per second (1fps) extraction for a 3-second video."""
    video_path = FIXTURES_DIR / "sample_video.mp4"
    assert video_path.exists()
    
    out_dir = TEMP_DIR / "test_keyframes_video"
    keyframes = extract_video_keyframes(video_path, out_dir)
    
    # 3 second video at 1fps yields ~3 keyframes
    assert len(keyframes) == 3
    for kf in keyframes:
        assert Path(kf).exists()
        with Image.open(kf) as img:
            assert img.size == (320, 240)


def test_full_media_ingestion():
    """Test full upload ingestion workflow for images and videos."""
    sample_path = FIXTURES_DIR / "sample.jpg"
    with open(sample_path, "rb") as f:
        bytes_data = f.read()

    res = process_uploaded_media(bytes_data, "sample.jpg")
    assert res["file_type"] == "image"
    assert res["is_video"] is False
    assert res["input_sha256"] == hashlib.sha256(bytes_data).hexdigest()
    assert Path(res["stored_path"]).exists()
    assert res["metadata"]["has_exif"] is True
