"""
CCTV Forensic Enhancement Dataset Setup & Verification Orchestrator.
=====================================================================
Configures directory layout and provides reference instructions for:
1. LOL-v2 (Frame Enhancement): Low-light / normal-light image pairs
   GitHub: https://github.com/JIA-Lab-research/SNR-Aware-Low-Light-Enhance
2. SDSD (Video Enhancement): 70 indoor / 80 outdoor dynamic video sequences
   GitHub: https://github.com/JIA-Lab-research/SDSD
   Code:   https://github.com/lingyzhu0101/low-light-video-enhancement
3. REDS (Video Super-Resolution Experiment): RealBasicVSR restoration
   GitHub: https://github.com/ckkelvinchan/RealBasicVSR

Generates initial benchmark verification pairs so training and evaluation
can be tested immediately out of the box.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import cv2
import numpy as np

FEAS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FEAS_ROOT))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DATA_DIR = FEAS_ROOT / "data" / "cctv_enhancement"
LOL_DIR = DATA_DIR / "lol_v2"
SDSD_DIR = DATA_DIR / "sdsd"
REDS_DIR = DATA_DIR / "reds"


def setup_lol_v2_structure(create_sample_pairs: bool = True):
    """
    Creates standard SNR-Aware-Low-Light-Enhance folder hierarchy for LOL-v2.
    Expected:
      lol_v2/
        Real_captured/
          Train/{Low,Normal}
          Test/{Low,Normal}
        Synthetic/
          Train/{Low,Normal}
          Test/{Low,Normal}
    """
    print("\n[1/3] Configuring LOL-v2 Frame Enhancement Dataset...")
    splits = ["Train", "Test"]
    categories = ["Real_captured", "Synthetic"]

    for cat in categories:
        for split in splits:
            for sub in ["Low", "Normal"]:
                folder = LOL_DIR / cat / split / sub
                folder.mkdir(parents=True, exist_ok=True)

    if create_sample_pairs:
        # Generate starter reference pairs in Real_captured/Train and Test
        for split in splits:
            low_dir = LOL_DIR / "Real_captured" / split / "Low"
            norm_dir = LOL_DIR / "Real_captured" / split / "Normal"
            count = 6 if split == "Train" else 2

            for i in range(count):
                lp = low_dir / f"cctv_lol_{split.lower()}_{i:03d}.png"
                np_path = norm_dir / f"cctv_lol_{split.lower()}_{i:03d}.png"
                if not lp.exists() or not np_path.exists():
                    # Normal reference
                    normal_canvas = np.full((320, 320, 3), 170, dtype=np.uint8)
                    cv2.rectangle(normal_canvas, (30, 30), (290, 290), (100, 140, 200), -1)
                    cv2.rectangle(normal_canvas, (60, 60), (160, 160), (240, 180, 50), -1)
                    cv2.putText(normal_canvas, f"LOL-V2 REAL {split} #{i}", (40, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    # Paired underexposed dark frame
                    dark_canvas = (normal_canvas.astype(np.float32) * 0.20)
                    noise = np.random.normal(0, 8.0, dark_canvas.shape)
                    dark_canvas = np.clip(dark_canvas + noise, 0, 255).astype(np.uint8)

                    cv2.imwrite(str(np_path), normal_canvas)
                    cv2.imwrite(str(lp), dark_canvas)

    print(f"  [OK] LOL-v2 directory established at: {LOL_DIR}")
    print(f"  • Upstream Repository : https://github.com/JIA-Lab-research/SNR-Aware-Low-Light-Enhance")


def setup_sdsd_structure(create_sample_sequences: bool = True):
    """
    Creates dynamic video sequence hierarchy for SDSD.
    Expected:
      sdsd/
        indoor/
          <sequence_id>/low/*.png
          <sequence_id>/normal/*.png
        outdoor/
          <sequence_id>/low/*.png
          <sequence_id>/normal/*.png
    """
    print("\n[2/3] Configuring SDSD Video Enhancement Dataset...")
    for scene in ["indoor", "outdoor"]:
        for seq_idx in range(1, 3):
            seq_dir = SDSD_DIR / scene / f"pair_{seq_idx:02d}"
            (seq_dir / "low").mkdir(parents=True, exist_ok=True)
            (seq_dir / "normal").mkdir(parents=True, exist_ok=True)

            if create_sample_sequences:
                # Create a 10-frame dynamic sequence
                for t in range(10):
                    lf = seq_dir / "low" / f"frame_{t:04d}.png"
                    nf = seq_dir / "normal" / f"frame_{t:04d}.png"
                    if not lf.exists() or not nf.exists():
                        gt = np.full((256, 256, 3), 160, dtype=np.uint8)
                        # Moving car/pedestrian
                        pos_x = 20 + t * 15
                        cv2.rectangle(gt, (pos_x, 100), (pos_x + 50, 140), (50, 180, 220), -1)
                        cv2.circle(gt, (pos_x + 12, 140), 8, (30, 30, 30), -1)
                        cv2.circle(gt, (pos_x + 38, 140), 8, (30, 30, 30), -1)
                        cv2.putText(gt, f"SDSD {scene.upper()} T={t}", (15, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                        # Paired low-light dynamic frame
                        dark = (gt.astype(np.float32) * (0.22 + 0.02 * np.sin(t * 0.5)))
                        noise = np.random.normal(0, 10.0, dark.shape)
                        dark = np.clip(dark + noise, 0, 255).astype(np.uint8)

                        cv2.imwrite(str(nf), gt)
                        cv2.imwrite(str(lf), dark)

    print(f"  [OK] SDSD directory established at: {SDSD_DIR}")
    print(f"  * Upstream Repository : https://github.com/JIA-Lab-research/SDSD")
    print(f"  * Video Enhancement   : https://github.com/lingyzhu0101/low-light-video-enhancement")


def setup_reds_structure(create_sample_pairs: bool = True):
    """
    Creates REDS super-resolution experiment hierarchy.
    Expected:
      reds/
        train_sharp/<sequence_id>/*.png
        train_sharp_bicubic/X4/<sequence_id>/*.png
    """
    print("\n[3/3] Configuring REDS Super-Resolution Experiment Dataset...")
    sharp_dir = REDS_DIR / "train_sharp" / "seq_000"
    lr_dir = REDS_DIR / "train_sharp_bicubic" / "X4" / "seq_000"
    sharp_dir.mkdir(parents=True, exist_ok=True)
    lr_dir.mkdir(parents=True, exist_ok=True)

    if create_sample_pairs:
        for t in range(6):
            hf_path = sharp_dir / f"{t:08d}.png"
            lf_path = lr_dir / f"{t:08d}.png"
            if not hf_path.exists() or not lf_path.exists():
                hr = np.full((256, 256, 3), 150, dtype=np.uint8)
                cv2.putText(hr, f"REDS HR FRAME {t}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 240), 2)
                cv2.rectangle(hr, (30, 120), (220, 220), (50, 150, 50), 2)
                lr = cv2.resize(hr, (64, 64), interpolation=cv2.INTER_CUBIC)

                cv2.imwrite(str(hf_path), hr)
                cv2.imwrite(str(lf_path), lr)

    print(f"  [OK] REDS directory established at: {REDS_DIR}")
    print(f"  * Upstream Repository : https://github.com/ckkelvinchan/RealBasicVSR")
    print(f"  * Forensic Notice     : Super-resolution generates synthetic high-frequency details")
    print(f"                          and must NOT be submitted as unverified proof in court.")


def main():
    parser = argparse.ArgumentParser(description="Setup CCTV Enhancement Datasets (LOL-v2, SDSD, REDS)")
    parser.add_argument("--skip-samples", action="store_true", help="Do not generate initial starter sample pairs")
    args = parser.parse_args()

    print("======================================================================")
    print("  FEAS 2.0 - CCTV Enhancement Dataset Initializer")
    print("======================================================================")
    print(f"Target Root: {DATA_DIR}")

    create_samples = not args.skip_samples
    setup_lol_v2_structure(create_sample_pairs=create_samples)
    setup_sdsd_structure(create_sample_sequences=create_samples)
    setup_reds_structure(create_sample_pairs=create_samples)

    print("\n----------------------------------------------------------------------")
    print("[OK] Dataset environment successfully configured for CCTV Enhancement.")
    print("Run 'python scripts/train_cctv_enhancer.py --dataset lol-v2' to begin training.")
    print("======================================================================\n")


if __name__ == "__main__":
    main()
