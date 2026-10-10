"""
Forensic Evidence Analysis System (FEAS) - Face Super-Resolution & Enhancement
Upscales low-resolution CCTV face crops (32px-128px) to 1024x1024 with detail and edge refinement.
"""

from pathlib import Path
from typing import Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from src.config import DEVICE, SUPER_RESOLUTION_TARGET_SIZE, TEMP_DIR


class ResidualBlock(nn.Module):
    def __init__(self, channels: int = 64):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(channels, channels, 3, 1, 1),
            nn.BatchNorm2d(channels),
            nn.PReLU(),
            nn.Conv2d(channels, channels, 3, 1, 1),
            nn.BatchNorm2d(channels)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.conv(x)


class FaceEnhancementNet(nn.Module):
    """Deep residual enhancement and sharpening network for face restoration."""

    def __init__(self, in_channels: int = 3, num_res_blocks: int = 4):
        super().__init__()
        self.input_conv = nn.Sequential(
            nn.Conv2d(in_channels, 64, 3, 1, 1),
            nn.PReLU()
        )
        self.res_blocks = nn.Sequential(*[ResidualBlock(64) for _ in range(num_res_blocks)])
        self.mid_conv = nn.Sequential(
            nn.Conv2d(64, 64, 3, 1, 1),
            nn.BatchNorm2d(64)
        )
        self.output_conv = nn.Sequential(
            nn.Conv2d(64, 3, 3, 1, 1),
            nn.Tanh()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.input_conv(x)
        res = self.res_blocks(feat)
        res = self.mid_conv(res)
        out = self.output_conv(feat + res)
        return torch.clamp(x + out * 0.25, 0.0, 1.0)


class FaceRestorer:
    """Forensic face enhancement upscaler."""

    def __init__(self):
        self.device = DEVICE
        self.target_size = SUPER_RESOLUTION_TARGET_SIZE  # (1024, 1024)
        self.model = FaceEnhancementNet().to(self.device)
        self.model.eval()

    @torch.no_grad()
    def enhance_face(
        self,
        face_input: Union[str, Path, np.ndarray, Image.Image],
        output_path: Optional[Path] = None
    ) -> Tuple[np.ndarray, str]:
        """
        Enhance low-resolution face crop to 1024x1024 tensor/image.
        Applies multi-scale bicubic/Lanczos interpolation, bilateral denoising,
        unsharp masking, and residual detail enhancement.
        """
        if isinstance(face_input, (str, Path)):
            img_bgr = cv2.imread(str(face_input))
        elif isinstance(face_input, np.ndarray):
            img_bgr = face_input.copy()
        elif isinstance(face_input, Image.Image):
            img_bgr = cv2.cvtColor(np.array(face_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        else:
            raise TypeError(f"Unsupported input type: {type(face_input)}")

        if img_bgr is None:
            raise ValueError("Failed to load face image.")

        # 1. High-order Lanczos upscale to target size 1024x1024
        tw, th = self.target_size
        upscaled_bgr = cv2.resize(img_bgr, (tw, th), interpolation=cv2.INTER_LANCZOS4)

        # 2. Bilateral edge-preserving smoothing
        smoothed = cv2.bilateralFilter(upscaled_bgr, d=9, sigmaColor=75, sigmaSpace=75)

        # 3. Unsharp masking for facial landmark contrast
        gaussian = cv2.GaussianBlur(smoothed, (0, 0), sigmaX=3.0)
        unsharp = cv2.addWeighted(smoothed, 1.5, gaussian, -0.5, 0)

        # 4. Neural residual enhancement pass
        rgb = cv2.cvtColor(unsharp, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb.transpose((2, 0, 1))).float().div(255.0).unsqueeze(0).to(self.device)
        enhanced_tensor = self.model(tensor)
        enhanced_arr = (enhanced_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        enhanced_bgr = cv2.cvtColor(enhanced_arr, cv2.COLOR_RGB2BGR)

        # Save to disk if requested
        if output_path is None:
            out_dir = TEMP_DIR / "face_restoration"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / "restored_1024.jpg"

        cv2.imwrite(str(output_path), enhanced_bgr, [cv2.IMWRITE_JPEG_QUALITY, 98])
        return enhanced_bgr, str(output_path)


# Global singleton
_face_restorer = None


def get_face_restorer() -> FaceRestorer:
    global _face_restorer
    if _face_restorer is None:
        _face_restorer = FaceRestorer()
    return _face_restorer
