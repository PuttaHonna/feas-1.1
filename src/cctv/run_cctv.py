"""
Command-Line Interface for Module 2: CCTV Video Enhancement, Detection, and Tracking
"""

import argparse
import json
from pathlib import Path

from src.cctv.pipeline import run_cctv_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Module 2: CCTV Video Forensic Analysis Pipeline"
    )
    parser.add_argument("--video", type=str, required=True, help="Path to input CCTV video file")
    parser.add_argument("--output-dir", type=str, default="data/cctv_output", help="Directory to save exported artifacts")
    parser.add_argument("--conf-threshold", type=float, default=0.35, help="Confidence threshold for COCO detections")
    parser.add_argument("--duration-threshold", type=float, default=5.0, help="Seconds threshold for duration exceeded event")
    parser.add_argument("--gamma", type=float, default=1.0, help="Gamma correction factor")
    parser.add_argument("--no-clahe", action="store_true", help="Disable CLAHE contrast enhancement")
    parser.add_argument("--no-denoise", action="store_true", help="Disable bilateral denoising")
    parser.add_argument("--no-sharpen", action="store_true", help="Disable unsharp mask sharpening")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional frame limit for processing")

    args = parser.parse_args()

    print(f"[*] Starting CCTV forensic pipeline on: {args.video}")
    result = run_cctv_pipeline(
        video_path=Path(args.video),
        output_dir=Path(args.output_dir),
        conf_threshold=args.conf_threshold,
        duration_threshold_sec=args.duration_threshold,
        gamma=args.gamma,
        enable_clahe=not args.no_clahe,
        enable_denoise=not args.no_denoise,
        enable_sharpen=not args.no_sharpen,
        max_frames_to_process=args.max_frames,
    )

    print("\n[+] Processing Completed Successfully!")
    print(f"    Evidence ID: {result['evidence_id']}")
    print(f"    Original SHA-256: {result['original_sha256']}")
    print(f"    Working Copy SHA-256: {result['working_copy_sha256']}")
    print("\n[+] Exported Artifacts:")
    for k, v in result["artifacts"].items():
        print(f"    {k}: {v}")
    print("\n[+] Measured Metrics:")
    print(json.dumps(result["metrics"], indent=2))
    print(f"\n[!] Disclaimer: {result['disclaimer']}")


if __name__ == "__main__":
    main()
