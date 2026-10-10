"""
Unit Tests for High-Graphics UI Components and Visualizers
Tests CCTV Matrix, 3D Face Mesh, 3D FFT Surface, Audio Radar, and Ballistics 3D.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.ui.components import (
    apply_forensic_theme,
    render_cctv_surveillance_matrix,
    render_3d_face_mesh,
    render_3d_fft_surface,
    render_audio_telemetry_radar,
    render_ballistics_striation_3d,
    render_header,
    render_metric_card,
    render_suspect_card,
    render_verdict_card
)


@patch("src.ui.components.st")
def test_apply_forensic_theme(mock_st):
    apply_forensic_theme()
    mock_st.markdown.assert_called_once()
    args = mock_st.markdown.call_args[0][0]
    assert "cctv-monitor-frame" in args
    assert "cctv-scanlines" in args


@patch("src.ui.components.st")
def test_render_3d_face_mesh(mock_st):
    dummy_emb = [0.1 * i for i in range(64)]
    render_3d_face_mesh(dummy_emb, "Test Subject")
    mock_st.plotly_chart.assert_called_once()


@patch("src.ui.components.st")
def test_render_3d_fft_surface(mock_st):
    render_3d_fft_surface(None)
    mock_st.plotly_chart.assert_called_once()


@patch("src.ui.components.st")
def test_render_audio_telemetry_radar(mock_st):
    dummy_audio = {
        "duration_seconds": 3.0,
        "sample_rate_hz": 44100,
        "snr_db": 22.0,
        "pitch_jitter": 0.012,
        "synthetic_voice_score": 0.15
    }
    render_audio_telemetry_radar(dummy_audio)
    mock_st.plotly_chart.assert_called_once()


@patch("src.ui.components.st")
def test_render_ballistics_striation_3d(mock_st):
    render_ballistics_striation_3d(None)
    mock_st.plotly_chart.assert_called_once()


@patch("src.ui.components.st")
def test_render_cctv_surveillance_matrix(mock_st):
    mock_st.columns.side_effect = lambda spec: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    mock_st.selectbox.return_value = "Quad Matrix (4-Angle Split)"
    mock_st.slider.return_value = 0
    render_cctv_surveillance_matrix(keyframes=["mock_frame.jpg"], media_info={"fps": 30.0})
    assert mock_st.markdown.called
