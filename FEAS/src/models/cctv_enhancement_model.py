"""
Forensic CCTV Video & Frame Deep Learning Enhancement Neural Network Suite.
=============================================================================
Architectures:
1. CCTVEnhanceNet: Multi-Scale Residual Attention Network with Adaptive Illumination
   and Edge Refinement (trained on LOL-v2 paired frame dataset).
2. CCTVTemporalVideoEnhanceNet: Multi-Frame Temporal Attention Network with Inter-Frame
   Consistency and Anti-Flicker suppression (trained on SDSD dynamic video dataset).
3. CCTVRealBasicVSRExperiment: Resolution Restoration Module (REDS RealBasicVSR).

FORENSIC INTEGRITY RULE:
All enhanced frames are derived working copies. Original footage is immutable.
Generated fine textures from Super-Resolution (REDS/RealBasicVSR) are investigative
hypotheses and must NOT be introduced as authenticated evidence in legal proceedings.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Device detection (Cross-platform: CUDA for NVIDIA, MPS for Apple Silicon, CPU fallback)
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")


# ==============================================================================
# Building Blocks: Channel Attention & Residual Blocks
# ==============================================================================
class ChannelAttention(nn.Module):
    """Squeeze-and-Excitation Channel Attention."""
    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, max(channels // reduction, 8), 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(max(channels // reduction, 8), channels, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        return x * self.sigmoid(avg_out + max_out)


class ResidualAttentionBlock(nn.Module):
    """Residual block with channel attention and edge preservation."""
    def __init__(self, channels: int = 48):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.norm1 = nn.BatchNorm2d(channels)
        self.act1 = nn.PReLU()
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.norm2 = nn.BatchNorm2d(channels)
        self.ca = ChannelAttention(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = self.act1(self.norm1(self.conv1(x)))
        res = self.norm2(self.conv2(res))
        res = self.ca(res)
        return x + res


# ==============================================================================
# Model 1: LOL-v2 Single-Frame Deep Enhancer (CCTVEnhanceNet)
# ==============================================================================
class CCTVEnhanceNet(nn.Module):
    """
    Forensic Surveillance Frame Enhancement & Denoising Deep Network.
    Trained on LOL-v2 (Real & Synthetic) paired dark/normal-light imagery.
    Maps degraded CCTV RGB frames [B, 3, H, W] -> Enhanced High-Fidelity [B, 3, H, W].
    """
    def __init__(self, in_channels: int = 3, num_features: int = 48, num_blocks: int = 5):
        super().__init__()
        # 1. Multi-scale intake convs
        self.shallow1 = nn.Conv2d(in_channels, num_features, kernel_size=3, padding=1)
        self.shallow2 = nn.Conv2d(in_channels, num_features, kernel_size=5, padding=2)
        self.fuse_shallow = nn.Sequential(
            nn.Conv2d(num_features * 2, num_features, kernel_size=1),
            nn.PReLU()
        )

        # 2. Residual Attention Backbone
        self.blocks = nn.ModuleList([ResidualAttentionBlock(num_features) for _ in range(num_blocks)])

        # 3. Low-Light Illumination Estimator Subnet
        self.illum_net = nn.Sequential(
            nn.Conv2d(num_features, 24, 3, padding=1),
            nn.PReLU(),
            nn.Conv2d(24, 1, 1),
            nn.Sigmoid()
        )

        # 4. High-frequency Edge Fusion & Reconstruction
        self.mid_conv = nn.Sequential(
            nn.Conv2d(num_features, num_features, 3, padding=1),
            nn.PReLU()
        )
        self.recon = nn.Sequential(
            nn.Conv2d(num_features, 24, 3, padding=1),
            nn.PReLU(),
            nn.Conv2d(24, 3, 3, padding=1),
            nn.Tanh()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x is normalized [0, 1] tensor of shape [B, 3, H, W]
        feat1 = self.shallow1(x)
        feat2 = self.shallow2(x)
        feat = self.fuse_shallow(torch.cat([feat1, feat2], dim=1))

        # Pass through residual attention blocks
        curr = feat
        for blk in self.blocks:
            curr = blk(curr)

        # Illumination adjustment
        illum = self.illum_net(curr)  # [B, 1, H, W]
        illum_boosted = x * (1.0 + illum * 0.50)

        # High-frequency reconstruction residual
        curr = self.mid_conv(curr)
        residual = self.recon(curr)

        # Output bounded in [0, 1]
        out = torch.clamp(illum_boosted + residual * 0.35, 0.0, 1.0)
        return out


# ==============================================================================
# Model 2: SDSD Multi-Frame Dynamic Video Enhancer (CCTVTemporalVideoEnhanceNet)
# ==============================================================================
class CCTVTemporalVideoEnhanceNet(nn.Module):
    """
    Temporal Multi-Frame Surveillance Video Enhancer.
    Trained on SDSD (Indoor & Outdoor dynamic pairs).
    Learns from neighbouring frames [Frame_t-1, Frame_t, Frame_t+1] to restore Frame_t
    while actively enforcing temporal consistency and suppressing inter-frame flicker.
    """
    def __init__(self, window_size: int = 3, num_features: int = 48, num_blocks: int = 4):
        super().__init__()
        self.window_size = window_size
        in_channels = 3 * window_size

        # Temporal intake conv with cross-frame receptive field
        self.temporal_in = nn.Sequential(
            nn.Conv2d(in_channels, num_features, kernel_size=3, padding=1),
            nn.PReLU(),
            nn.Conv2d(num_features, num_features, kernel_size=3, padding=1),
            nn.PReLU()
        )

        # Temporal attention module: aligns features across time
        self.temporal_attention = nn.Sequential(
            nn.Conv2d(num_features, num_features // 2, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_features // 2, num_features, kernel_size=1),
            nn.Sigmoid()
        )

        # Residual backbone
        self.blocks = nn.ModuleList([ResidualAttentionBlock(num_features) for _ in range(num_blocks)])

        # Illumination & Color Consistency head
        self.illum_head = nn.Sequential(
            nn.Conv2d(num_features, 24, 3, padding=1),
            nn.PReLU(),
            nn.Conv2d(24, 3, 1),
            nn.Sigmoid()
        )

        # Output reconstruction
        self.recon = nn.Sequential(
            nn.Conv2d(num_features, 24, 3, padding=1),
            nn.PReLU(),
            nn.Conv2d(24, 3, 3, padding=1),
            nn.Tanh()
        )

    def forward(self, x_seq: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x_seq: [B, window_size * 3, H, W] - concatenated neighbouring frames.
                   Center frame is at channels 3:6 when window_size=3.
        Returns:
            Enhanced center frame: [B, 3, H, W] in [0, 1].
        """
        # Center frame extraction
        center_idx = self.window_size // 2
        center_frame = x_seq[:, center_idx * 3:(center_idx + 1) * 3, :, :]

        feat = self.temporal_in(x_seq)
        att = self.temporal_attention(feat)
        feat = feat * att

        curr = feat
        for blk in self.blocks:
            curr = blk(curr)

        illum = self.illum_head(curr)
        boosted = center_frame * (1.0 + illum * 0.55)

        residual = self.recon(curr)
        out = torch.clamp(boosted + residual * 0.30, 0.0, 1.0)
        return out


# ==============================================================================
# Model 3: REDS Video Super-Resolution Experiment (RealBasicVSR)
# ==============================================================================
class CCTVRealBasicVSRExperiment(nn.Module):
    """
    Video Super-Resolution Architecture (RealBasicVSR reference on REDS).
    FORENSIC WARNING: Reconstructs high-frequency textures via statistical inference.
    Not to be presented as authenticated evidence.
    """
    def __init__(self, scale: int = 4, num_features: int = 36):
        super().__init__()
        self.scale = scale
        self.conv_in = nn.Conv2d(3, num_features, 3, padding=1)
        self.blocks = nn.ModuleList([ResidualAttentionBlock(num_features) for _ in range(4)])
        self.upsample = nn.Sequential(
            nn.Conv2d(num_features, num_features * (scale ** 2), 3, padding=1),
            nn.PixelShuffle(scale),
            nn.PReLU(),
            nn.Conv2d(num_features, 3, 3, padding=1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = F.prelu(self.conv_in(x), torch.tensor(0.2, device=x.device))
        for blk in self.blocks:
            feat = blk(feat)
        return self.upsample(feat)


# ==============================================================================
# Unified CCTV Forensic Enhancer Engine
# ==============================================================================
class CCTVForensicEnhancer:
    """
    Production inference engine supporting:
    - lol_v2: Single-frame illumination enhancement (LOL-v2 paired training).
    - sdsd_temporal: Multi-frame temporal video enhancement (SDSD paired dynamic training).
    - reds_sr: Experimental video super-resolution (RealBasicVSR / REDS).
    - basic / low_light: Deterministic OpenCV baseline.
    """
    _instance = None

    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device) if device else DEVICE

        # Initialize network architectures
        self.frame_model = CCTVEnhanceNet().to(self.device)
        self.video_model = CCTVTemporalVideoEnhanceNet().to(self.device)
        self.sr_model = CCTVRealBasicVSRExperiment(scale=2).to(self.device)

        self.weights_loaded: Dict[str, bool] = {
            "lol_v2": False,
            "sdsd": False,
            "sr": False
        }

        self._load_all_weights()
        self.frame_model.eval()
        self.video_model.eval()
        self.sr_model.eval()

    def _load_all_weights(self):
        """Loads available trained checkpoints from storage or models directories."""
        base_dirs = [
            Path(__file__).parent,
            Path(__file__).parent.parent.parent / "storage",
            Path(__file__).parent.parent.parent / "models",
            Path(__file__).parent.parent.parent / "deep_learning_forensic_investigator"
        ]

        # 1. LOL-v2 single-frame weights
        for d in base_dirs:
            for fname in ["cctv_enhancer_lol_v2.pt", "cctv_enhancer_weights.pt"]:
                p = d / fname
                if p.exists():
                    try:
                        sd = torch.load(str(p), map_location=self.device)
                        self.frame_model.load_state_dict(sd, strict=False)
                        self.weights_loaded["lol_v2"] = True
                        break
                    except Exception:
                        pass
            if self.weights_loaded["lol_v2"]:
                break

        # 2. SDSD temporal video weights
        for d in base_dirs:
            p = d / "cctv_enhancer_sdsd.pt"
            if p.exists():
                try:
                    sd = torch.load(str(p), map_location=self.device)
                    self.video_model.load_state_dict(sd, strict=False)
                    self.weights_loaded["sdsd"] = True
                    break
                except Exception:
                    pass
            if self.weights_loaded["sdsd"]:
                break

        # 3. REDS super-resolution experiment weights
        for d in base_dirs:
            p = d / "cctv_enhancer_reds_sr.pt"
            if p.exists():
                try:
                    sd = torch.load(str(p), map_location=self.device)
                    self.sr_model.load_state_dict(sd, strict=False)
                    self.weights_loaded["sr"] = True
                    break
                except Exception:
                    pass
            if self.weights_loaded["sr"]:
                break

    @torch.no_grad()
    def enhance_frame(
        self,
        frame_bgr: np.ndarray,
        mode: str = "lol_v2",
        scale: int = 1,
        denoise_level: int = 70,
        low_light_boost: bool = True
    ) -> np.ndarray:
        """
        Enhance a single CCTV video frame with the requested model mode.

        Args:
            frame_bgr: Input BGR frame.
            mode: 'lol_v2', 'sdsd_temporal', 'reds_sr', 'deep_learning', or 'basic'.
            scale: Resolution upscale factor (1 or 2).
            denoise_level: Edge-preserving denoising strength (0-100).
            low_light_boost: Enable adaptive gamma/illumination expansion.

        Returns:
            Enhanced BGR frame.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr

        mode_clean = str(mode).lower().replace("-", "_")
        h, w = frame_bgr.shape[:2]

        # Convert to RGB normalized float tensor
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb.transpose((2, 0, 1))).float().div(255.0).unsqueeze(0).to(self.device)

        # Deep learning enhancement selection
        try:
            if "reds" in mode_clean or "sr" in mode_clean or "super" in mode_clean:
                # Video super-resolution experiment
                out_tensor = self.sr_model(tensor)
                out_arr = (out_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                enhanced_bgr = cv2.cvtColor(out_arr, cv2.COLOR_RGB2BGR)

            elif "sdsd" in mode_clean:
                # Simulated single-frame inference through temporal net (repeat frame for 3-window)
                seq_tensor = torch.cat([tensor, tensor, tensor], dim=1)
                out_tensor = self.video_model(seq_tensor)
                out_arr = (out_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                enhanced_bgr = cv2.cvtColor(out_arr, cv2.COLOR_RGB2BGR)

            else:
                # LOL-v2 single-frame enhancement
                out_tensor = self.frame_model(tensor)
                out_arr = (out_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                enhanced_bgr = cv2.cvtColor(out_arr, cv2.COLOR_RGB2BGR)
        except Exception:
            enhanced_bgr = frame_bgr.copy()

        # Optional upscale if requested and not in SR mode
        if scale > 1 and "reds" not in mode_clean and "sr" not in mode_clean:
            enhanced_bgr = cv2.resize(enhanced_bgr, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)

        # Contrast enhancement (CLAHE on L-channel)
        lab = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2LAB)
        l, a, b_ch = cv2.split(lab)
        clahe_limit = 2.4 if low_light_boost else 1.8
        clahe = cv2.createCLAHE(clipLimit=clahe_limit, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l)
        enhanced_bgr = cv2.cvtColor(cv2.merge((l_clahe, a, b_ch)), cv2.COLOR_LAB2BGR)

        # Edge-preserving denoising
        if denoise_level > 0:
            sigma = float(denoise_level * 0.6)
            d_size = 5 if denoise_level < 80 else 7
            enhanced_bgr = cv2.bilateralFilter(enhanced_bgr, d=d_size, sigmaColor=sigma, sigmaSpace=sigma)

        # Mild sharpening
        gaussian = cv2.GaussianBlur(enhanced_bgr, (0, 0), sigmaX=1.5)
        sharp_strength = 0.35 + (0.15 if scale > 1 else 0.0)
        sharpened = cv2.addWeighted(enhanced_bgr, 1.0 + sharp_strength, gaussian, -sharp_strength, 0)
        out_bgr = np.clip(sharpened, 0, 255).astype(np.uint8)

        # If Super-Resolution experiment was used, overlay clear forensic disclaimer
        if "reds" in mode_clean or "sr" in mode_clean:
            out_bgr = self._add_sr_forensic_banner(out_bgr)

        return out_bgr

    @torch.no_grad()
    def enhance_video_sequence(
        self,
        frames_bgr: List[np.ndarray],
        mode: str = "sdsd_temporal",
        temporal_smoothing: float = 0.85
    ) -> List[np.ndarray]:
        """
        Enhance an entire sequence of CCTV frames with temporal consistency and anti-flicker.
        Uses SDSD 3-frame sliding window [t-1, t, t+1] when mode='sdsd_temporal'.
        Applies exponential temporal filtering to stabilize luminance across time.
        """
        if not frames_bgr:
            return []

        if len(frames_bgr) == 1:
            return [self.enhance_frame(frames_bgr[0], mode=mode)]

        enhanced_frames: List[np.ndarray] = []
        prev_enhanced = None

        for t in range(len(frames_bgr)):
            # Form 3-frame temporal window for SDSD
            f_curr = frames_bgr[t]
            f_prev = frames_bgr[max(0, t - 1)]
            f_next = frames_bgr[min(len(frames_bgr) - 1, t + 1)]

            if "sdsd" in str(mode).lower():
                try:
                    # Multi-frame tensor [1, 9, H, W]
                    t_prev = torch.from_numpy(cv2.cvtColor(f_prev, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)).float().div(255.0)
                    t_curr = torch.from_numpy(cv2.cvtColor(f_curr, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)).float().div(255.0)
                    t_next = torch.from_numpy(cv2.cvtColor(f_next, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)).float().div(255.0)
                    seq_t = torch.cat([t_prev, t_curr, t_next], dim=0).unsqueeze(0).to(self.device)

                    out_t = self.video_model(seq_t)
                    out_arr = (out_t.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                    enh_bgr = cv2.cvtColor(out_arr, cv2.COLOR_RGB2BGR)
                except Exception:
                    enh_bgr = self.enhance_frame(f_curr, mode="lol_v2")
            else:
                enh_bgr = self.enhance_frame(f_curr, mode=mode)

            # Temporal flicker filter (IIR filter on luminance)
            if prev_enhanced is not None and temporal_smoothing > 0.0:
                lab_curr = cv2.cvtColor(enh_bgr, cv2.COLOR_BGR2LAB)
                lab_prev = cv2.cvtColor(prev_enhanced, cv2.COLOR_BGR2LAB)
                l_c, a_c, b_c = cv2.split(lab_curr)
                l_p, _, _ = cv2.split(lab_prev)

                # Smooth Luminance channel
                l_smooth = cv2.addWeighted(l_c, 1.0 - (temporal_smoothing * 0.25), l_p, (temporal_smoothing * 0.25), 0)
                enh_bgr = cv2.cvtColor(cv2.merge((l_smooth, a_c, b_c)), cv2.COLOR_LAB2BGR)

            prev_enhanced = enh_bgr
            enhanced_frames.append(enh_bgr)

        return enhanced_frames

    def _add_sr_forensic_banner(self, img: np.ndarray) -> np.ndarray:
        """Adds forensic non-evidence disclaimer banner to super-resolution outputs."""
        h, w = img.shape[:2]
        banner_h = max(24, int(h * 0.04))
        banner = np.zeros((banner_h, w, 3), dtype=np.uint8)
        banner[:] = (15, 15, 60)  # Dark red/burgundy alert bar
        text = "REDS/RealBasicVSR EXPERIMENTAL ARTIFACT: Inferred textures not verified evidence."
        font_scale = max(0.35, min(0.65, w / 1200.0))
        cv2.putText(banner, text, (12, int(banner_h * 0.68)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)
        return np.vstack([img, banner])


def get_cctv_enhancer() -> CCTVForensicEnhancer:
    """Singleton getter for CCTVForensicEnhancer."""
    if CCTVForensicEnhancer._instance is None:
        CCTVForensicEnhancer._instance = CCTVForensicEnhancer()
    return CCTVForensicEnhancer._instance
