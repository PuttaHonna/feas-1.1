"""
Unit & Integration Tests for Audio & Voice Authenticity Forensics
"""

from pathlib import Path
import numpy as np
import pytest

from src.config import FIXTURES_DIR, TEMP_DIR
from src.models.audio.spectrogram import render_audio_spectrogram, render_waveform_plot
from src.models.audio.voice_forensics import analyze_audio_forensics, get_audio_analyzer


def test_spectrogram_and_waveform_rendering():
    """Verify STFT spectrogram and oscillogram rendering to file."""
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    samples = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    out_dir = TEMP_DIR / "test_audio_render"
    spec_path = out_dir / "test_spec.jpg"
    wave_path = out_dir / "test_wave.jpg"

    render_audio_spectrogram(samples, sr, spec_path)
    render_waveform_plot(samples, sr, wave_path)

    assert spec_path.exists()
    assert wave_path.exists()
    assert spec_path.stat().st_size > 500
    assert wave_path.stat().st_size > 500


def test_audio_forensics_on_fixture():
    """Verify end-to-end voice forensics on synthetic WAV fixture."""
    fixture_path = FIXTURES_DIR / "sample_audio.wav"
    assert fixture_path.exists()

    out_dir = TEMP_DIR / "test_audio_output"
    results = analyze_audio_forensics(fixture_path, out_dir)

    assert results["has_audio"] is True
    assert results["duration_seconds"] > 0
    assert results["sample_rate_hz"] == 16000
    assert "synthetic_voice_score" in results
    assert 0.0 <= results["synthetic_voice_score"] <= 1.0
    assert "snr_db" in results
    assert "pitch_mean_hz" in results
    assert results["spectrogram_image_path"] is not None
    assert Path(results["spectrogram_image_path"]).exists()
    assert Path(results["waveform_image_path"]).exists()


def test_audio_forensics_on_image_fallback():
    """Verify safe fallback when run on a non-audio file."""
    img_path = FIXTURES_DIR / "sample.jpg"
    assert img_path.exists()

    results = analyze_audio_forensics(img_path)
    assert results["has_audio"] is False
    assert results["synthetic_voice_score"] == 0.0
    assert results["spectrogram_image_path"] is None
