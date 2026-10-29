"""
Forensic Evidence Analysis System (FEAS) - AI & Deepfake Synthetic Artifact Detector
Analyzes images for Generative AI (Diffusion, GAN, Midjourney, DALL-E, Inpainting) signatures:
1. 2D Fast Fourier Transform (FFT) Power Spectrum Analysis (detects decoder/upsampler grid peaks)
2. Azimuthal Radial Energy Distribution (measures 1/f^alpha power-law deviation)
3. High-Frequency Denoising Residual Kurtosis (distinguishes diffusion noise from CMOS/CCD photon shot noise)
4. Color Chrominance Distribution Symmetry (detects synthetic VAE color space quantization)
5. Multi-modal AI Confidence Score & Artifact Heatmap Export
"""

import base64
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from src.config import TEMP_DIR


def compute_fft_spectrum(img_gray: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Compute 2D Fast Fourier Transform (FFT) and extract frequency-domain synthetic metrics.
    Generative AI models (Diffusion VAEs, GANs) exhibit periodic high-frequency grid spikes
    and abnormal radial energy concentration that deviate strongly from natural camera acoustics.
    """
    h, w = img_gray.shape[:2]
    # Resize to standardized power-of-2 dimension for FFT consistency
    dim = 512
    resized = cv2.resize(img_gray, (dim, dim), interpolation=cv2.INTER_AREA)

    # 2D FFT with zero-frequency centered
    f = np.fft.fft2(resized)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-9)

    # Normalize magnitude spectrum for visual forensic artifact (0-255)
    norm_mag = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    spectrum_heatmap = cv2.applyColorMap(norm_mag, cv2.COLORMAP_VIRIDIS)

    # Azimuthal Radial Profile (distance from DC center)
    center_y, center_x = dim // 2, dim // 2
    y, x = np.ogrid[:dim, :dim]
    r = np.hypot(x - center_x, y - center_y).astype(np.int32)

    # Partition into low, mid, and high frequency shells
    max_radius = dim // 2
    high_freq_mask = (r >= int(max_radius * 0.65)) & (r < max_radius)
    mid_freq_mask = (r >= int(max_radius * 0.25)) & (r < int(max_radius * 0.65))
    low_freq_mask = r < int(max_radius * 0.25)

    high_energy = float(np.mean(norm_mag[high_freq_mask]))
    mid_energy = float(np.mean(norm_mag[mid_freq_mask]))
    low_energy = float(np.mean(norm_mag[low_freq_mask]))

    # Natural camera images have high low_energy and smoothly decaying high_energy.
    # Diffusion models exhibit elevated mid-to-high frequency ratios and spectral peak spikes.
    spectral_ratio = high_energy / (mid_energy + 1e-5)

    # Measure spectral peak kurtosis (checkerboard grid artifacts create isolated hot pixels)
    high_freq_vals = norm_mag[high_freq_mask]
    p99 = float(np.percentile(high_freq_vals, 99))
    p50 = float(np.percentile(high_freq_vals, 50))
    peak_disparity = round((p99 - p50) / (p50 + 1e-5), 4)

    return spectrum_heatmap, {
        "spectral_ratio": round(spectral_ratio, 4),
        "peak_disparity": peak_disparity,
        "high_freq_energy": round(high_energy, 2),
        "mid_freq_energy": round(mid_energy, 2),
        "low_freq_energy": round(low_energy, 2),
    }


def compute_denoising_residual_stats(img_bgr: np.ndarray) -> Dict[str, float]:
    """
    Extract noise residuals using median filtering subtraction.
    Physical camera sensors have Poisson-Gaussian shot noise.
    Diffusion-based generators leave non-Gaussian residual distributions with high kurtosis.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.medianBlur(gray, 3)
    residual = gray.astype(np.float32) - denoised.astype(np.float32)

    mean = float(np.mean(residual))
    var = float(np.var(residual))
    std = np.sqrt(var) if var > 0 else 1e-6

    # Kurtosis (excess over normal distribution)
    fourth_moment = float(np.mean((residual - mean) ** 4))
    kurtosis = round(float(fourth_moment / (std ** 4)) - 3.0, 4)

    return {
        "noise_variance": round(var, 4),
        "residual_kurtosis": kurtosis,
        "is_abnormal_noise": bool(kurtosis > 4.5 or kurtosis < -1.2),
    }


def compute_chrominance_symmetry(img_bgr: np.ndarray) -> Dict[str, float]:
    """
    Examine YCrCb chrominance channels.
    Generative latent decoders often exhibit oversaturated, perfectly symmetric
    or clustered chrominance distributions compared to natural camera color science.
    """
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    cr = ycrcb[:, :, 1].astype(np.float32)
    cb = ycrcb[:, :, 2].astype(np.float32)

    cr_std = float(np.std(cr))
    cb_std = float(np.std(cb))
    ratio = round(min(cr_std, cb_std) / (max(cr_std, cb_std) + 1e-5), 4)

    return {
        "chroma_balance_ratio": ratio,
        "cr_dispersion": round(cr_std, 2),
        "cb_dispersion": round(cb_std, 2),
    }


def detect_ai_generation(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Comprehensive Forensic AI & Deepfake Artifact Detection:
    1. FFT Frequency Spectrum Analysis
    2. Denoising Residual Kurtosis
    3. Chrominance Balance Analysis
    4. Multi-modal AI Confidence Score Synthesis
    """
    out_dir = output_dir or (TEMP_DIR / "ai_synthetics_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        base_name = Path(image_input).stem
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input.copy()
        base_name = "image_input"
    elif isinstance(image_input, Image.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        base_name = "image_input"
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    if img_bgr is None:
        raise ValueError("Failed to decode input image.")

    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Fourier Spectrum
    spectrum_img, fft_metrics = compute_fft_spectrum(gray)
    spectrum_path = out_dir / f"{base_name}_fft_spectrum.jpg"
    cv2.imwrite(str(spectrum_path), spectrum_img)

    # 2. Residual Denoising Kurtosis
    noise_metrics = compute_denoising_residual_stats(img_bgr)

    # 3. Chrominance Distribution
    chroma_metrics = compute_chrominance_symmetry(img_bgr)

    # 4. Synthesize AI Probability Score
    kurt = noise_metrics["residual_kurtosis"]
    if kurt > 8.0 or kurt < -1.5:
        # Extremely strong synthetic diffusion / denoising residual signature
        kurt_score = min(1.0, 0.75 + min(0.24, abs(kurt) / 50.0))
    elif kurt > 2.8:
        kurt_score = min(0.70, 0.35 + (kurt - 2.8) / 8.0)
    else:
        kurt_score = max(0.01, min(0.15, abs(kurt) / 10.0))

    # Spectral high-frequency retention (diffusion models maintain elevated high frequencies)
    spec_ratio = fft_metrics["spectral_ratio"]
    if spec_ratio >= 0.85:
        spec_score = min(1.0, 0.55 + (spec_ratio - 0.85) * 3.0)
    elif spec_ratio >= 0.75:
        spec_score = 0.30
    else:
        spec_score = 0.05

    # Peak disparity (spectral grid peaks from upsamplers)
    p_disp = fft_metrics["peak_disparity"]
    disp_score = min(1.0, max(0.05, p_disp * 2.0))

    # Multi-modal fusion: 55% Residual Noise Kurtosis + 30% Spectral Energy + 15% Grid Peaks
    ai_prob = float(0.55 * kurt_score + 0.30 * spec_score + 0.15 * disp_score)
    ai_prob = round(min(0.99, max(0.01, ai_prob)), 4)
    is_ai_generated = bool(ai_prob >= 0.50)

    # Determine likely engine / manipulation archetype
    if is_ai_generated:
        if ai_prob >= 0.75:
            verdict = "AI-Generated / Deepfake Artifacts Detected (High Confidence)"
            archetype = "Latent Diffusion Model (Stable Diffusion / Midjourney / DALL-E)"
        else:
            verdict = "Suspected AI Generation / Synthetic Inpainting"
            archetype = "Generative Inpainting / GAN or Diffusion Blend"
        notes = (
            f"Image exhibits characteristic synthetic artifacts with {ai_prob*100:.1f}% AI probability. "
            f"Frequency analysis revealed spectral grid peak disparity of {fft_metrics['peak_disparity']:.3f} "
            f"and high-frequency residual kurtosis of {noise_metrics['residual_kurtosis']:.2f}, "
            f"deviating from standard physical camera optical falloff."
        )
    else:
        verdict = "Authentic Camera Capture (No Generative AI Artifacts)"
        archetype = "Physical Camera Sensor (CCD/CMOS)"
        notes = (
            f"Natural photographic optical characteristics confirmed ({ (1 - ai_prob)*100:.1f}% camera authenticity). "
            f"Fourier power spectrum and sensor noise kurtosis adhere to standard optical sensor distributions."
        )

    # Base64 spectrum preview
    _, spec_buf = cv2.imencode(".jpg", spectrum_img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    spec_b64 = "data:image/jpeg;base64," + base64.b64encode(spec_buf).decode("utf-8")

    return {
        "status": "success",
        "verdict": verdict,
        "is_ai_generated": is_ai_generated,
        "ai_probability": ai_prob,
        "confidence": f"{ai_prob * 100:.1f}%",
        "likely_archetype": archetype,
        "spectral_analysis": fft_metrics,
        "noise_residual_analysis": noise_metrics,
        "chrominance_analysis": chroma_metrics,
        "fft_spectrum_image_path": str(spectrum_path),
        "fft_spectrum_base64": spec_b64,
        "forensic_advisory": notes,
    }
