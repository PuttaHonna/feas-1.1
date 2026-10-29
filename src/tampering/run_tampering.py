"""
Command-Line Interface for Module 1: Image Tampering Detection
Supports:
1. audit: Audits dataset directory, removes corruptions, clusters duplicates, and generates splits.
2. train: Trains ResNet18/EfficientNet-B0 with validation F1 checkpointing.
3. evaluate: Runs single-pass test evaluation and robustness stress testing.
4. predict: Runs inference on a single image with quality gate and Grad-CAM.
"""

import argparse
import json
from pathlib import Path

from src.tampering.dataset_audit import DatasetAuditor
from src.tampering.train import train_tampering_classifier
from src.tampering.evaluate import evaluate_test_set
from src.tampering.predict import TamperingPredictor
from src.common.config import FORENSIC_CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="Module 1: Image Tampering Detection Pipeline (Forensic & Research Protocol)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Audit
    audit_parser = subparsers.add_parser("audit", help="Audit dataset directory and create clean splits")
    audit_parser.add_argument("--dataset-dir", type=str, required=True, help="Path to raw dataset with authentic/ and manipulated/ folders")
    audit_parser.add_argument("--output-manifest", type=str, default="data/splits_manifest.json", help="Path to save output split manifest")

    # 2. Train
    train_parser = subparsers.add_parser("train", help="Train tampering detection model")
    train_parser.add_argument("--manifest", type=str, required=True, help="Path to splits manifest JSON")
    train_parser.add_argument("--output-dir", type=str, default="data/checkpoints/tampering", help="Output directory for checkpoints")
    train_parser.add_argument("--arch", type=str, default="resnet18", choices=["resnet18", "efficientnet_b0"], help="Model backbone")
    train_parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    train_parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    train_parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    train_parser.add_argument("--seed", type=int, default=FORENSIC_CONFIG.DEFAULT_RANDOM_SEED, help="Random seed")

    # 3. Evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate model on untouched test data with robustness tests")
    eval_parser.add_argument("--checkpoint", type=str, required=True, help="Path to model checkpoint .pt")
    eval_parser.add_argument("--manifest", type=str, required=True, help="Path to splits manifest JSON")
    eval_parser.add_argument("--output-report", type=str, default="data/evaluation/tampering_test_report.json", help="Path to save test metrics JSON")

    # 4. Predict
    pred_parser = subparsers.add_parser("predict", help="Predict tampering status on a single image")
    pred_parser.add_argument("--checkpoint", type=str, required=True, help="Path to model checkpoint .pt")
    pred_parser.add_argument("--image", type=str, required=True, help="Path to image file")
    pred_parser.add_argument("--eval-meta", type=str, default=None, help="Optional path to saved evaluation test metrics JSON")
    pred_parser.add_argument("--gradcam-out", type=str, default=None, help="Optional output path for Grad-CAM overlay")
    pred_parser.add_argument("--uncertainty-thresh", type=float, default=0.65, help="Uncertainty rejection threshold")

    args = parser.parse_args()

    if args.command == "audit":
        auditor = DatasetAuditor(Path(args.dataset_dir))
        print("[*] Running dataset audit...")
        report = auditor.audit()
        print(f"[*] Valid images: {report['total_valid_images']} | Corrupted: {report['corrupted_files_count']} | Exact duplicates: {report['exact_duplicate_groups_count']}")
        manifest = auditor.create_clean_splits(Path(args.output_manifest))
        print(f"[+] Clean split manifest saved to {args.output_manifest}")
        print(f"    Train: {len(manifest['train'])} | Val: {len(manifest['val'])} | Test: {len(manifest['test'])}")

    elif args.command == "train":
        print(f"[*] Training {args.arch} for {args.epochs} epochs with seed={args.seed}...")
        meta = train_tampering_classifier(
            manifest_path=Path(args.manifest),
            output_dir=Path(args.output_dir),
            arch=args.arch,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            seed=args.seed,
        )
        print(f"[+] Training complete. Best Val F1: {meta['best_val_f1']} at epoch {meta['best_epoch']}.")
        print(f"[+] Saved checkpoint to: {meta['checkpoint_path']}")

    elif args.command == "evaluate":
        print(f"[*] Evaluating checkpoint {args.checkpoint} on untouched test data...")
        results = evaluate_test_set(
            checkpoint_path=Path(args.checkpoint),
            manifest_path=Path(args.manifest),
            output_report_path=Path(args.output_report),
        )
        print("[+] Test Evaluation Metrics:")
        print(json.dumps(results["clean_test_metrics"], indent=2))
        print(f"[+] Full evaluation and robustness report saved to: {args.output_report}")

    elif args.command == "predict":
        predictor = TamperingPredictor(
            checkpoint_path=Path(args.checkpoint),
            evaluation_meta_path=Path(args.eval_meta) if args.eval_meta else None,
            uncertainty_threshold=args.uncertainty_thresh,
        )
        res = predictor.predict(
            image_path=Path(args.image),
            generate_gradcam=True,
            gradcam_output_path=Path(args.gradcam_out) if args.gradcam_out else None,
        )
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
