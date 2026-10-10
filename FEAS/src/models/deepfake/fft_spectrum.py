"""
Forensic Evidence Analysis System (FEAS) - 2D FFT Frequency Domain Analysis
Detects periodic upsampling artifacts and spectral anomalies characteristic of GAN & Diffusion models.
"""

from pathlib import Path
from typing import Any, Dict, Tuple
import cv2
import numpy as np


def compute_fft_spectrum(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Compute 2D Fast Fourier Transform magnitude spectrum and extract spectral metrics.
    
    Returns:
        fft_vis_bgr: Visualized log-magnitude spectrum in COLORMAP_JET.
        metrics: Dictionary containing:
            - high_freq_ratio: Ratio of energy in high frequency quadrant vs low frequency
            - azimuthal_variance: Variance across radial frequency profiles
            - spectral_spike_count: Number of periodic grid peaks exceeding 3 sigma
            - spectral_anomaly_score: Composite score (0.0 to 1.0)
    """
    # Convert to grayscale float
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    # Standardize to power-of-two square crop for uniform frequency bins
    target_dim = 512
    gray_resized = cv2.resize(gray, (target_dim, target_dim), interpolation=cv2.INTER_AREA)

    # 2D Fast Fourier Transform with DC component shifted to center
    f_transform = np.fft.fft2(gray_resized)
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = np.abs(f_shift)

    # Logarithmic scaling for visualization: log(1 + |F|)
    log_magnitude = np.log1p(magnitude_spectrum)
    norm_log_mag = cv2.normalize(log_magnitude, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    fft_vis_bgr = cv2.applyColorMap(norm_log_mag, cv2.COLORMAP_JET)

    # Grid overlay on spectrum for court presentation
    cx, cy = target_dim // 2, target_dim // 2
    cv2.circle(fft_vis_bgr, (cx, cy), 60, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.circle(fft_vis_bgr, (cx, cy), 140, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.circle(fft_vis_bgr, (cx, cy), 220, (255, 255, 255), 1, cv2.LINE_AA)

    # --- Quantitative Spectral Metrics ---
    # 1. Low vs High Frequency Energy Partition
    y, x = np.ogrid[:target_dim, :target_dim]
    dist_from_center = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    low_freq_mask = dist_from_center <= 60
    mid_freq_mask = (dist_from_center > 60) & (dist_from_center <= 160)
    high_freq_mask = dist_from_center > 160

    total_energy = np.sum(magnitude_spectrum) + 1e-8
    low_freq_energy = np.sum(magnitude_spectrum[low_freq_mask])
    high_freq_energy = np.sum(magnitude_spectrum[high_freq_mask])

    high_freq_ratio = float(high_freq_energy / total_energy)

    # 2. Azimuthal Radial Profile Variance (Detecting directional grid peaks)
    # Natural photos have isotropic decay; GANs have distinct directional spikes at 0°, 45°, 90°
    radial_bins = 32
    max_radius = min(cx, cy)
    radial_profile = []
    
    for r in range(1, max_radius, max_radius // radial_bins):
        mask = (dist_from_center >= r) & (dist_from_center < r + (max_radius // radial_bins))
        if np.any(mask):
            radial_profile.append(np.mean(magnitude_spectrum[mask]))
        else:
            radial_profile.append(0.0)

    radial_profile = np.array(radial_profile, dtype=np.float64)
    # Normalize profile
    if np.max(radial_profile) > 0:
        norm_profile = radial_profile / np.max(radial_profile)
    else:
        norm_profile = radial_profile

    # Synthetic GAN/Diffusion images exhibit characteristic high-frequency slope deviation
    high_band_slope = float(np.mean(np.diff(norm_profile[-8:]))) if len(norm_profile) >= 8 else 0.0

    # 3. Detect discrete spectral spikes in the mid-high frequency zone
    mid_high_mag = magnitude_spectrum[mid_freq_mask | high_freq_mask]
    mean_val = np.mean(mid_high_mag)
    std_val = np.std(mid_high_mag) + 1e-8
    spikes = np.sum(mid_high_mag > (mean_val + 3.5 * std_val))
    spike_density = float(spikes / max(1, len(mid_high_mag)))

    # Composite spectral anomaly score
    # Organic photos typically have high_freq_ratio in [0.01, 0.08] and spike_density < 0.005
    score = 0.0
    if high_freq_ratio > 0.12 or high_freq_ratio < 0.005:
        score += 0.35
    if spike_density > 0.008:
        score += 0.40
    if abs(high_band_slope) > 0.05:
        score += 0.25

    spectral_score = round(float(np.clip(score, 0.01, 0.99)), 4)

    metrics = {
        "high_freq_ratio": round(high_freq_ratio, 5),
        "spike_density": round(spike_density, 5),
        "high_band_slope": round(high_band_slope, 5),
        "spectral_anomaly_score": spectral_score
    }

    return fft_vis_bgr, metrics
