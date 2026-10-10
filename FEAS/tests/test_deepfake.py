"""
Unit & Integration Tests for AI Deepfake & Synthetic Media Forensics
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from src.config import FIXTURES_DIR, TEMP_DIR
from src.models.deepfake.detector import detect_deepfake, get_deepfake_detector
from src.models.deepfake.fft_spectrum import compute_fft_spectrum


def test_fft_spectrum_calculation():
    """Verify 2D Fast Fourier Transform power spectrum generation and metric extraction."""
    img = np.zeros((256, 256, 3), dtype=np.uint8) + 120
    # Add high-frequency checkerboard pattern
    y, x = np.mgrid[:256, :256]
    pattern = (np.sin(2 * np.pi * x / 16.0) * np.sin(2 * np.pi * y / 16.0) * 40.0).astype(np.int16)
    img = np.clip(img.astype(np.int16) + pattern[:, :, None], 0, 255).astype(np.uint8)

    fft_vis, metrics = compute_fft_spectrum(img)

    assert fft_vis is not None
    assert fft_vis.shape == (512, 512, 3)
    assert "high_freq_ratio" in metrics
    assert "spike_density" in metrics
    assert "spectral_anomaly_score" in metrics
    assert 0.0 <= metrics["spectral_anomaly_score"] <= 1.0


def test_deepfake_detector_on_fixture():
    """Verify deepfake detector on generated fixture asset."""
    fixture_path = FIXTURES_DIR / "deepfake_sample.png"
    assert fixture_path.exists()

    out_dir = TEMP_DIR / "test_deepfake_output"
    results = detect_deepfake(fixture_path, out_dir)

    assert "is_deepfake" in results
    assert "deepfake_score" in results
    assert 0.0 <= results["deepfake_score"] <= 1.0
    assert "model_attribution" in results
    assert "fft_spectrum_image_path" in results
    assert "blend_boundary_map_path" in results
    assert Path(results["fft_spectrum_image_path"]).exists()
    assert Path(results["blend_boundary_map_path"]).exists()
