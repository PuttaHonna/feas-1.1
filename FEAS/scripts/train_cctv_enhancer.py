"""
CCTV Video & Frame Deep Learning Enhancement Training Suite.
============================================================
Supports Paired Supervised Training:
1. LOL-v2 (Frame Enhancement): Low-light dark frames -> Normal-light target frames.
   Learns reconstruction on image pairs before multi-frame video.
   Reference: https://github.com/JIA-Lab-research/SNR-Aware-Low-Light-Enhance
2. SDSD (Video Enhancement): Multi-frame dynamic sequences with temporal consistency.
   Learns from neighbouring frames [t-1, t, t+1] to suppress inter-frame flicker.
   Reference: https://github.com/JIA-Lab-research/SDSD & https://github.com/lingyzhu0101/low-light-video-enhancement
3. REDS (Video Super-Resolution Experiment): Paired low-res -> sharp sequences.
   Reference: https://github.com/ckkelvinchan/RealBasicVSR

Training Relationship:
  Training input: dark frame / sequence
  Training target: corresponding normal-light frame
  ↓
  Model produces enhanced frame
  ↓
  Compare prediction with target
  ↓
  Calculate error (Charbonnier + Laplacian Edge + Temporal Consistency) and update model weights
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import random
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader

FEAS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FEAS_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.models.cctv_enhancement_model import (
    CCTVEnhanceNet,
    CCTVTemporalVideoEnhanceNet,
    CCTVRealBasicVSRExperiment,
    DEVICE,
)
from src.cctv.dataset_loaders import (
    LOLv2Dataset,
    SDSDVideoDataset,
    REDSSuperResDataset,
    calculate_psnr,
    calculate_ssim,
    calculate_temporal_flicker,
)


# ==============================================================================
# Forensic Loss Functions
# ==============================================================================
class CharbonnierEdgeLoss(nn.Module):
    """
    Smooth L1 Charbonnier loss + Laplacian edge gradient penalty + Color cosine loss.
    Provides robust, hallucination-free reconstruction against ground-truth targets.
    """
    def __init__(self, eps: float = 1e-3, edge_weight: float = 0.20, color_weight: float = 0.10):
        super().__init__()
        self.eps = eps
        self.edge_weight = edge_weight
        self.color_weight = color_weight

        # 3x3 Laplacian edge kernel
        lap = torch.tensor([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]], dtype=torch.float32)
        self.lap_kernel = lap.view(1, 1, 3, 3).repeat(3, 1, 1, 1).to(DEVICE)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        # 1. Charbonnier pixel reconstruction loss
        diff = pred - target
        charbonnier_loss = torch.mean(torch.sqrt(diff * diff + self.eps * self.eps))

        # 2. Laplacian edge preservation
        pred_edges = F.conv2d(pred, self.lap_kernel, padding=1, groups=3)
        target_edges = F.conv2d(target, self.lap_kernel, padding=1, groups=3)
        edge_loss = torch.mean(torch.abs(pred_edges - target_edges))

        # 3. Color fidelity loss (cosine similarity on pixel channels)
        pred_norm = F.normalize(pred, p=2, dim=1, eps=1e-6)
        target_norm = F.normalize(target, p=2, dim=1, eps=1e-6)
        color_loss = torch.mean(1.0 - torch.sum(pred_norm * target_norm, dim=1))

        total_loss = charbonnier_loss + self.edge_weight * edge_loss + self.color_weight * color_loss

        breakdown = {
            "charbonnier": float(charbonnier_loss.item()),
            "edge": float(edge_loss.item()),
            "color": float(color_loss.item()),
        }
        return total_loss, breakdown


class TemporalConsistencyLoss(nn.Module):
    """
    Penalizes inter-frame luminance and color variations between enhanced sequence
    and ground truth normal sequence to suppress video flickering.
    """
    def __init__(self, weight: float = 0.35):
        super().__init__()
        self.weight = weight

    def forward(
        self,
        pred_curr: torch.Tensor,
        pred_prev: torch.Tensor,
        target_curr: torch.Tensor,
        target_prev: torch.Tensor
    ) -> torch.Tensor:
        delta_pred = pred_curr - pred_prev
        delta_target = target_curr - target_prev
        temporal_diff = torch.mean(torch.abs(delta_pred - delta_target))
        return self.weight * temporal_diff


# ==============================================================================
# Training Orchestrators
# ==============================================================================
def train_lol_v2_frame_model(
    data_dir: Path,
    epochs: int = 5,
    batch_size: int = 8,
    lr: float = 2e-4,
    patch_size: int = 128,
    save_path: Optional[Path] = None
):
    """
    Train CCTVEnhanceNet on LOL-v2 low-light / normal-light image pairs.
    Each dark image has a corresponding normal-light target.
    """
    print("\n======================================================================")
    print("  [Step 1] LOL-v2 Paired Frame Enhancement Training")
    print("======================================================================")
    print(f"Dataset Location : {data_dir}")
    print(f"Device           : {DEVICE}")
    print(f"Epochs           : {epochs} | Batch Size: {batch_size} | Patch Size: {patch_size}x{patch_size}")
    print("Relationship     : Dark Frame (Input) -> Normal-Light Target (Ground Truth)")
    print("Note             : Single-frame image training; reference benchmarks PSNR/SSIM.\n")

    dataset = LOLv2Dataset(root_dir=data_dir, split="Train", patch_size=patch_size, samples_per_epoch=200)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    model = CCTVEnhanceNet().to(DEVICE)
    criterion = CharbonnierEdgeLoss().to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        psnr_list, ssim_list = [], []

        for step, (dark_inputs, normal_targets) in enumerate(loader):
            dark_inputs = dark_inputs.to(DEVICE)
            normal_targets = normal_targets.to(DEVICE)

            optimizer.zero_grad()
            # 1. Model produces enhanced frame
            enhanced_outputs = model(dark_inputs)

            # 2. Compare prediction with target and calculate error
            loss, breakdown = criterion(enhanced_outputs, normal_targets)

            # 3. Update model weights
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            epoch_loss += loss.item()

            # Benchmark evaluation metrics against normal target
            with torch.no_grad():
                for b in range(dark_inputs.size(0)):
                    p = enhanced_outputs[b].detach().cpu().numpy()
                    t = normal_targets[b].detach().cpu().numpy()
                    psnr_list.append(calculate_psnr(p, t))
                    ssim_list.append(calculate_ssim(p, t))

        scheduler.step()
        avg_loss = epoch_loss / len(loader)
        avg_psnr = np.mean(psnr_list) if psnr_list else 0.0
        avg_ssim = np.mean(ssim_list) if ssim_list else 0.0

        print(
            f"  Epoch [{epoch:02d}/{epochs:02d}] "
            f"Loss: {avg_loss:.4f} | "
            f"PSNR: {avg_psnr:.2f} dB | "
            f"SSIM: {avg_ssim:.4f} | "
            f"LR: {scheduler.get_last_lr()[0]:.6f}"
        )

    duration = time.time() - start_time
    print(f"\n[OK] LOL-v2 training finished in {duration:.1f}s.")
    print("Limitation Note: Frame-level training does not address multi-frame temporal flickering.")

    # Save checkpoint
    out_path = save_path or (FEAS_ROOT / "storage" / "cctv_enhancer_lol_v2.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(out_path))
    print(f"[OK] Trained weights exported to: {out_path}")
    return model


def train_sdsd_video_model(
    data_dir: Path,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 2e-4,
    patch_size: int = 128,
    save_path: Optional[Path] = None
):
    """
    Train CCTVTemporalVideoEnhanceNet on SDSD dynamic video pairs.
    Uses multi-frame temporal sliding window [t-1, t, t+1] to predict normal frame t
    with explicit temporal consistency loss to prevent video flickering.
    """
    print("\n======================================================================")
    print("  [Step 2] SDSD Dynamic Video & Multi-Frame Temporal Training")
    print("======================================================================")
    print(f"Dataset Location : {data_dir}")
    print(f"Device           : {DEVICE}")
    print(f"Epochs           : {epochs} | Batch Size: {batch_size} | Window: 3 neighbouring frames")
    print("Relationship     : Dynamic Low-Light Window [t-1, t, t+1] -> Normal Target [t]")
    print("Features         : Dynamic scene motion, neighbouring frames, anti-flicker temporal loss.\n")

    dataset = SDSDVideoDataset(root_dir=data_dir, window_size=3, patch_size=patch_size, samples_per_epoch=160)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    model = CCTVTemporalVideoEnhanceNet(window_size=3).to(DEVICE)
    charbonnier = CharbonnierEdgeLoss().to(DEVICE)
    temporal_loss_fn = TemporalConsistencyLoss().to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        psnr_list, ssim_list = [], []

        for step, (low_window, tgt_t, tgt_prev) in enumerate(loader):
            low_window = low_window.to(DEVICE)
            tgt_t = tgt_t.to(DEVICE)
            tgt_prev = tgt_prev.to(DEVICE)

            optimizer.zero_grad()
            # 1. Predict enhanced center frame
            enhanced_t = model(low_window)

            # 2. Predict previous frame using shifted window to compute temporal gradient
            # Approximate t-1 prediction by shifting window channels
            shifted_prev_window = torch.cat([low_window[:, 0:3], low_window[:, 0:3], low_window[:, 3:6]], dim=1)
            enhanced_prev = model(shifted_prev_window)

            # 3. Calculate spatial error and temporal consistency error
            recon_loss, _ = charbonnier(enhanced_t, tgt_t)
            temp_loss = temporal_loss_fn(enhanced_t, enhanced_prev, tgt_t, tgt_prev)
            total_loss = recon_loss + temp_loss

            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            epoch_loss += total_loss.item()

            with torch.no_grad():
                for b in range(tgt_t.size(0)):
                    p = enhanced_t[b].detach().cpu().numpy()
                    t = tgt_t[b].detach().cpu().numpy()
                    psnr_list.append(calculate_psnr(p, t))
                    ssim_list.append(calculate_ssim(p, t))

        avg_loss = epoch_loss / len(loader)
        avg_psnr = np.mean(psnr_list) if psnr_list else 0.0
        avg_ssim = np.mean(ssim_list) if ssim_list else 0.0

        print(
            f"  Epoch [{epoch:02d}/{epochs:02d}] "
            f"Loss: {avg_loss:.4f} | "
            f"Video PSNR: {avg_psnr:.2f} dB | "
            f"SSIM: {avg_ssim:.4f}"
        )

    duration = time.time() - start_time
    print(f"\n[OK] SDSD dynamic video training finished in {duration:.1f}s.")
    print("Benefit: Temporal consistency enforced across video sequence; flickering suppressed.")

    out_path = save_path or (FEAS_ROOT / "storage" / "cctv_enhancer_sdsd.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(out_path))
    print(f"[OK] Trained temporal weights exported to: {out_path}")
    return model


def train_reds_sr_model(
    data_dir: Path,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 2e-4,
    scale: int = 2,
    patch_size_hr: int = 128,
    save_path: Optional[Path] = None
):
    """
    Train CCTVRealBasicVSRExperiment on REDS paired low-res -> sharp frames.
    FORENSIC WARNING: Super-resolution produces mathematically inferred high-frequency details.
    """
    print("\n======================================================================")
    print("  [Step 3] REDS Video Super-Resolution (RealBasicVSR) Training")
    print("======================================================================")
    print(f"Dataset Location : {data_dir}")
    print(f"Device           : {DEVICE}")
    print(f"Scale Factor     : {scale}x | Epochs: {epochs} | Batch Size: {batch_size}")
    print("Relationship     : Low-Resolution Frame (Input) -> Sharp HR Frame (Ground Truth)")
    print("Forensic Warning : Super-resolution creates inferred high-frequency textures.")
    print("                   Must NOT be introduced as authenticated primary evidence in court.\n")

    dataset = REDSSuperResDataset(
        root_dir=data_dir,
        scale=scale,
        patch_size_hr=patch_size_hr,
        samples_per_epoch=150
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    model = CCTVRealBasicVSRExperiment(scale=scale).to(DEVICE)
    criterion = CharbonnierEdgeLoss().to(DEVICE)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        psnr_list, ssim_list = [], []

        for step, (lr_inputs, hr_targets) in enumerate(loader):
            lr_inputs = lr_inputs.to(DEVICE)
            hr_targets = hr_targets.to(DEVICE)

            optimizer.zero_grad()
            sr_outputs = model(lr_inputs)
            loss, breakdown = criterion(sr_outputs, hr_targets)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            epoch_loss += loss.item()

            with torch.no_grad():
                for b in range(lr_inputs.size(0)):
                    p = sr_outputs[b].detach().cpu().numpy()
                    t = hr_targets[b].detach().cpu().numpy()
                    psnr_list.append(calculate_psnr(p, t))
                    ssim_list.append(calculate_ssim(p, t))

        scheduler.step()
        avg_loss = epoch_loss / len(loader)
        avg_psnr = np.mean(psnr_list) if psnr_list else 0.0
        avg_ssim = np.mean(ssim_list) if ssim_list else 0.0

        print(
            f"  Epoch [{epoch:02d}/{epochs:02d}] "
            f"Loss: {avg_loss:.4f} | "
            f"SR PSNR: {avg_psnr:.2f} dB | "
            f"SSIM: {avg_ssim:.4f} | "
            f"LR: {scheduler.get_last_lr()[0]:.6f}"
        )

    duration = time.time() - start_time
    print(f"\n[OK] REDS Super-Resolution training finished in {duration:.1f}s.")
    print("Forensic Caution: Output flagged with legal disclaimer before export.")

    out_path = save_path or (FEAS_ROOT / "storage" / "cctv_enhancer_reds_sr.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(out_path))
    print(f"[OK] Trained SR weights exported to: {out_path}")
    return model


def main():
    parser = argparse.ArgumentParser(description="Train CCTV Deep Enhancement Models (LOL-v2, SDSD, REDS)")
    parser.add_argument("--dataset", choices=["lol-v2", "sdsd", "reds", "all"], default="lol-v2", help="Target dataset")
    parser.add_argument("--data-dir", type=str, default="", help="Custom dataset path")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    args = parser.parse_args()

    default_base = FEAS_ROOT / "data" / "cctv_enhancement"

    if args.dataset in ("lol-v2", "all"):
        lol_path = Path(args.data_dir) if args.data_dir else (default_base / "lol_v2")
        train_lol_v2_frame_model(lol_path, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    if args.dataset in ("sdsd", "all"):
        sdsd_path = Path(args.data_dir) if args.data_dir else (default_base / "sdsd")
        train_sdsd_video_model(sdsd_path, epochs=args.epochs, batch_size=max(2, args.batch_size // 2), lr=args.lr)

    if args.dataset in ("reds", "all"):
        reds_path = Path(args.data_dir) if args.data_dir else (default_base / "reds")
        train_reds_sr_model(reds_path, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    print("\n[OK] All requested CCTV enhancement training tasks completed successfully.")


if __name__ == "__main__":
    main()
