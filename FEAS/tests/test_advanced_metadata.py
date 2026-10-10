"""
Unit & Integration Tests for Advanced Binary & Provenance Metadata Examiner
"""

from pathlib import Path
import pytest

from src.config import FIXTURES_DIR
from src.pipeline.advanced_metadata import inspect_advanced_binary_metadata


def test_inspect_advanced_metadata_on_deepfake():
    """Verify detection of AI generation parameters and magic bytes on synthetic fixture."""
    fixture_path = FIXTURES_DIR / "deepfake_sample.png"
    assert fixture_path.exists()

    res = inspect_advanced_binary_metadata(fixture_path)

    assert res["valid_file"] is True
    assert res["magic_valid"] is True
    assert "PNG" in res["format_identified"]
    assert res["ai_generation_detected"] is True
    assert any("Stable Diffusion" in tool or "Prompt" in tool for tool in res["ai_tools"])


def test_inspect_advanced_metadata_on_standard_sample():
    """Verify standard JPEG inspection with clean bitstream."""
    sample_path = FIXTURES_DIR / "sample.jpg"
    assert sample_path.exists()

    res = inspect_advanced_binary_metadata(sample_path)

    assert res["valid_file"] is True
    assert res["magic_valid"] is True
    assert "JPEG" in res["format_identified"]
    assert "double_compression_risk" in res
    assert "steganography_overlay_risk" in res
