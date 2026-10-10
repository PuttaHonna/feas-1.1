"""
Forensic Evidence Analysis System (FEAS) - Audio Spectrogram & Waveform Renderer
Generates calibrated Short-Time Fourier Transform (STFT) spectral heatmaps and oscillograms.
"""

from pathlib import Path
from typing import Tuple
import cv2
import numpy as np
from scipy import signal


def render_audio_spectrogram(
    samples: np.ndarray,
    sample_rate: int,
    output_path: Path,
    target_size: Tuple[int, int] = (800, 400)
) -> str:
    """
    Render a calibrated STFT audio spectrogram saved as an image file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Compute STFT
    nperseg = min(1024, len(samples))
    if nperseg < 64:
        # Create minimal blank spectrogram for extremely short audio
        img = np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
        cv2.imwrite(str(output_path), img)
        return str(output_path)

    frequencies, times, sxx = signal.spectrogram(
        samples,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2,
        mode="magnitude"
    )

    # Convert to log-magnitude (dB scale)
    sxx_db = 20 * np.log10(np.maximum(sxx, 1e-6))
    
    # Normalize dB to 0-255 range
    min_db = -80.0
    max_db = np.max(sxx_db)
    sxx_norm = np.clip((sxx_db - min_db) / (max_db - min_db + 1e-6) * 255.0, 0, 255).astype(np.uint8)

    # Invert frequency axis so 0Hz is at the bottom
    sxx_norm = np.flipud(sxx_norm)

    # Resize to target display dimensions
    w, h = target_size
    resized = cv2.resize(sxx_norm, (w, h), interpolation=cv2.INTER_LINEAR)
    spectrogram_bgr = cv2.applyColorMap(resized, cv2.COLORMAP_INFERNO)

    # Overlay forensic frequency markings & time markers
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(spectrogram_bgr, f"FS: {sample_rate} Hz | MAX FREQ: {sample_rate//2} Hz", (15, 25), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(spectrogram_bgr, "0.0s", (15, h - 10), font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    duration_str = f"{len(samples) / sample_rate:.2f}s"
    cv2.putText(spectrogram_bgr, duration_str, (w - 70, h - 10), font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    # Horizontal guide lines
    cv2.line(spectrogram_bgr, (0, h // 4), (w, h // 4), (50, 50, 50), 1)
    cv2.line(spectrogram_bgr, (0, h // 2), (w, h // 2), (50, 50, 50), 1)
    cv2.line(spectrogram_bgr, (0, 3 * h // 4), (w, 3 * h // 4), (50, 50, 50), 1)

    cv2.imwrite(str(output_path), spectrogram_bgr)
    return str(output_path)


def render_waveform_plot(
    samples: np.ndarray,
    sample_rate: int,
    output_path: Path,
    target_size: Tuple[int, int] = (800, 240)
) -> str:
    """
    Render time-domain oscillogram waveform.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = target_size

    canvas = np.full((h, w, 3), 15, dtype=np.uint8) # Dark forensic background
    
    if len(samples) == 0:
        cv2.imwrite(str(output_path), canvas)
        return str(output_path)

    # Subsample to fit width
    stride = max(1, len(samples) // w)
    sub_samples = samples[::stride][:w]

    # Normalize samples to canvas height with margin
    center_y = h // 2
    max_amp = np.max(np.abs(sub_samples)) + 1e-6
    scale = (h // 2 - 20) / max_amp

    # Center zero line
    cv2.line(canvas, (0, center_y), (w, center_y), (60, 70, 80), 1)

    pts = []
    for x, amp in enumerate(sub_samples):
        y = int(center_y - amp * scale)
        pts.append((x, np.clip(y, 0, h - 1)))

    # Draw continuous waveform in bright cyan
    for i in range(1, len(pts)):
        cv2.line(canvas, pts[i - 1], pts[i], (255, 240, 0), 1, cv2.LINE_AA)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(canvas, f"PEAK: {max_amp:.3f} | SAMPLES: {len(samples)}", (15, 20), font, 0.45, (0, 240, 255), 1, cv2.LINE_AA)

    cv2.imwrite(str(output_path), canvas)
    return str(output_path)
