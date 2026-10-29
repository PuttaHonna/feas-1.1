"""
Unit tests for pre-inference forensic quality gate.
"""

from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

from src.common.quality_gate import evaluate_image_quality


def test_quality_gate_passes_sharp_image(tmp_path: Path):
    # Sharp high-contrast checkerboard image
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    arr[::20, :] = 255
    arr[:, ::20] = 255
    arr[arr == 0] = 50

    img = Image.fromarray(arr)
    path = tmp_path / "sharp.png"
    img.save(path)

    assessment = evaluate_image_quality(path)
    assert assessment.passed is True
    assert assessment.blur_score > 25.0
    assert len(assessment.reasons) == 0
    assert "meets minimum" in assessment.summary_message


def test_quality_gate_fails_heavily_blurred_image(tmp_path: Path):
    # Create smooth image with very low edge variance
    arr = np.full((200, 200, 3), 128, dtype=np.uint8)
    img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=10))
    path = tmp_path / "blurred.png"
    img.save(path)

    assessment = evaluate_image_quality(path)
    assert assessment.passed is False
    assert any("too blurred" in r for r in assessment.reasons)
    assert "Unable to provide a reliable" in assessment.summary_message


def test_quality_gate_fails_pitch_black_image(tmp_path: Path):
    img = Image.new("RGB", (200, 200), color=(2, 2, 2))
    path = tmp_path / "black.png"
    img.save(path)

    assessment = evaluate_image_quality(path)
    assert assessment.passed is False
    assert any("underexposed" in r for r in assessment.reasons)


def test_quality_gate_fails_blown_out_image(tmp_path: Path):
    img = Image.new("RGB", (200, 200), color=(250, 250, 250))
    path = tmp_path / "blown_out.png"
    img.save(path)

    assessment = evaluate_image_quality(path)
    assert assessment.passed is False
    assert any("overexposed" in r for r in assessment.reasons)


def test_quality_gate_fails_low_resolution(tmp_path: Path):
    img = Image.new("RGB", (32, 32), color=(128, 128, 128))
    path = tmp_path / "tiny.png"
    img.save(path)

    assessment = evaluate_image_quality(path)
    assert assessment.passed is False
    assert any("Resolution too low" in r for r in assessment.reasons)
