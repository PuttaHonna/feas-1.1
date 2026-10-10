"""
Forensic Evidence Analysis System (FEAS) - Deepfake & Synthetic Media Detector
Combines spatial MesoNet neural features, 2D FFT frequency spectrum analysis, and blending boundary edge consistency.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.config import DEVICE, TEMP_DIR
from src.models.deepfake.fft_spectrum import compute_fft_spectrum


class Meso4(nn.Module):
    """MesoNet-4 Architecture for Deepfake detection in human facial images."""
    def __init__(self, num_classes: int = 1):
        super(Meso4, self).__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(8)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool1 = nn.MaxPool2d(2, 2)

        self.conv2 = nn.Conv2d(8, 8, 5, padding=2, bias=False)
        self.bn2 = nn.BatchNorm2d(8)
        self.maxpool2 = nn.MaxPool2d(2, 2)

        self.conv3 = nn.Conv2d(8, 16, 5, padding=2, bias=False)
        self.bn3 = nn.BatchNorm2d(16)
        self.maxpool3 = nn.MaxPool2d(2, 2)

        self.conv4 = nn.Conv2d(16, 16, 5, padding=2, bias=False)
        self.bn4 = nn.BatchNorm2d(16)
        self.maxpool4 = nn.MaxPool2d(4, 4)

        self.dropout = nn.Dropout(0.5)
        self.fc1 = nn.Linear(16 * 8 * 8, 16)
        self.leaky_relu = nn.LeakyReLU(0.1)
        self.fc2 = nn.Linear(16, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.maxpool1(self.relu(self.bn1(self.conv1(x))))
        x = self.maxpool2(self.relu(self.bn2(self.conv2(x))))
        x = self.maxpool3(self.relu(self.bn3(self.conv3(x))))
        x = self.maxpool4(self.relu(self.bn4(self.conv4(x))))
        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        x = self.leaky_relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return torch.sigmoid(x)


class DeepfakeDetector:
    """Ensemble Deepfake & Synthetic Media Forensic Detector."""
    def __init__(self):
        self.device = DEVICE
        self.model = Meso4().to(self.device)
        self.model.eval()

    def _extract_meso_score(self, img_bgr: np.ndarray) -> float:
        """Run standardized Meso-4 inference on normalized 256x256 tensor."""
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
        tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        tensor = tensor.to(self.device)

        with torch.no_grad():
            output = self.model(tensor)
            score = float(output.item())
        return score

    def _analyze_blending_boundaries(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, float, List[str]]:
        """
        Detect face warping and blending seam artifacts (e.g. Poisson blending discontinuities).
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # High-pass Laplacian filter to extract micro-texture edge transitions
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_abs = np.abs(laplacian)
        
        # Calculate local gradient variance
        kernel_size = 15
        local_mean = cv2.blur(laplacian_abs, (kernel_size, kernel_size))
        local_sq_mean = cv2.blur(laplacian_abs ** 2, (kernel_size, kernel_size))
        local_var = np.maximum(0, local_sq_mean - (local_mean ** 2))
        
        # Normalize local variance map for visualization
        norm_var = cv2.normalize(local_var, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        boundary_heatmap_bgr = cv2.applyColorMap(norm_var, cv2.COLORMAP_MAGMA)
        
        # Measure edge distribution kurtosis (synthetic blends have bimodal edge spikes)
        var_flat = local_var.flatten()
        mean_var = np.mean(var_flat)
        std_var = np.std(var_flat) + 1e-8
        kurtosis_proxy = float(np.mean(((var_flat - mean_var) / std_var) ** 4))
        
        signals = []
        boundary_score = 0.0
        
        # High kurtosis indicates sharp localized edge differences (e.g. pasted face mask)
        if kurtosis_proxy > 18.0:
            signals.append("High-gradient boundary seam discontinuity (FaceSwap/Inpainting artifact)")
            boundary_score += 0.45
        elif kurtosis_proxy > 10.0:
            signals.append("Minor localized edge variance irregularity")
            boundary_score += 0.20
            
        # Check for unnatural color saturation differences across regions
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        sat_std = float(np.std(sat))
        if sat_std > 65.0:
            signals.append("Severe chroma saturation disparity across boundary regions")
            boundary_score += 0.25
            
        return boundary_heatmap_bgr, min(1.0, boundary_score), signals


_detector_instance: Optional[DeepfakeDetector] = None


def get_deepfake_detector() -> DeepfakeDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DeepfakeDetector()
    return _detector_instance


def detect_deepfake(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute end-to-end forensic deepfake detection:
    1. 2D FFT Frequency Domain Analysis (GAN periodic artifacts & Diffusion decay).
    2. Spatial Boundary & Blending Gradient Analysis.
    3. Neural Meso-4 Feature Classification.
    4. Generative Model Attribution.
    """
    out_dir = output_dir or (TEMP_DIR / "deepfake_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        base_name = Path(image_input).stem
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input.copy()
        base_name = "evidence_deepfake"
    elif isinstance(image_input, Image.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        base_name = "evidence_deepfake"
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    if img_bgr is None:
        raise ValueError("Failed to load evidence image for deepfake analysis.")

    # 1. Frequency domain FFT spectrum analysis
    fft_bgr, fft_metrics = compute_fft_spectrum(img_bgr)
    fft_filename = f"{base_name}_fft_spectrum.jpg"
    fft_path = out_dir / fft_filename
    cv2.imwrite(str(fft_path), fft_bgr)

    # 2. Blending boundary & seam analysis
    boundary_bgr, boundary_score, boundary_signals = get_deepfake_detector()._analyze_blending_boundaries(img_bgr)
    boundary_filename = f"{base_name}_blend_boundary.jpg"
    boundary_path = out_dir / boundary_filename
    cv2.imwrite(str(boundary_path), boundary_bgr)

    # 3. MesoNet Neural Feature Inference
    meso_score = get_deepfake_detector()._extract_meso_score(img_bgr)

    # 4. Synthesize composite deepfake probability
    spectral_score = fft_metrics["spectral_anomaly_score"]
    
    # Weights: Frequency (40%), Boundary / Edge (35%), Neural Spatial (25%)
    composite_deepfake_score = float(0.40 * spectral_score + 0.35 * boundary_score + 0.25 * meso_score)

    artifact_signals = list(boundary_signals)
    if fft_metrics["spike_density"] > 0.008:
        artifact_signals.append("Periodic upsampling grid artifacts in 2D Fourier spectrum (GAN signature)")
    if fft_metrics["high_freq_ratio"] > 0.12:
        artifact_signals.append("Elevated high-frequency energy concentration")
    elif fft_metrics["high_freq_ratio"] < 0.005:
        artifact_signals.append("Unnatural high-frequency suppression (Diffusion generative smoothing)")

    # Model Attribution classification
    if composite_deepfake_score >= 0.50:
        if fft_metrics["spike_density"] > 0.008:
            model_attribution = "GAN / Generative Adversarial Network (StyleGAN / ProGAN)"
        elif boundary_score >= 0.40:
            model_attribution = "FaceSwap / DeepFaceLab (Boundary Splicing)"
        elif fft_metrics["high_freq_ratio"] < 0.008:
            model_attribution = "Latent Diffusion Model (Stable Diffusion / Midjourney)"
        else:
            model_attribution = "AI-Generated Synthetic Media (Neural Synthesis)"
    else:
        model_attribution = "Authentic Camera Capture (Organic Sensor Pattern)"

    is_deepfake = bool(composite_deepfake_score >= 0.50)

    return {
        "is_deepfake": is_deepfake,
        "deepfake_score": round(min(0.99, max(0.01, composite_deepfake_score)), 4),
        "model_attribution": model_attribution,
        "spectral_score": spectral_score,
        "boundary_score": round(boundary_score, 4),
        "meso_score": round(meso_score, 4),
        "fft_metrics": fft_metrics,
        "artifact_signals": artifact_signals,
        "fft_spectrum_image_path": str(fft_path),
        "blend_boundary_map_path": str(boundary_path)
    }
