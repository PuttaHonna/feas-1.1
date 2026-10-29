"""
Command-Line Interface for Module 3: Wound Research Classification (Research Protocol Only)
"""

import argparse
import json
from pathlib import Path

from src.wound_research.dataset import create_patient_level_splits
from src.wound_research.train import train_wound_classifier
from src.wound_research.evaluate import evaluate_wound_test_set
from src.wound_research.predict import WoundResearchPredictor


def main():
    parser = argparse.ArgumentParser(
        description="Module 3: Wound Image Research Classification (Educational & Research Prototype Only)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train
    train_p = subparsers.add_parser("train", help="Train on consented patient-level dataset manifest")
    train_p.add_argument("--manifest", type=str, required=True, help="Path to patient dataset manifest JSON")
    train_p.add_argument("--output-dir", type=str, default="data/checkpoints/wound_research", help="Output directory")
    train_p.add_argument("--arch", type=str, default="resnet18", choices=["resnet18", "efficientnet_b0"])
    train_p.add_argument("--epochs", type=int, default=10)
    train_p.add_argument("--batch-size", type=int, default=8)

    # Evaluate
    eval_p = subparsers.add_parser("evaluate", help="Evaluate model on patient-level test split")
    eval_p.add_argument("--checkpoint", type=str, required=True)
    eval_p.add_argument("--manifest", type=str, required=True)
    eval_p.add_argument("--output-report", type=str, default="data/evaluation/wound_eval_report.json")

    # Predict
    pred_p = subparsers.add_parser("predict", help="Predict on a single image with research consent metadata")
    pred_p.add_argument("--checkpoint", type=str, required=True)
    pred_p.add_argument("--image", type=str, required=True)
    pred_p.add_argument("--research-metadata", type=str, default=None, help="JSON file containing research dataset credentials and consent")
    pred_p.add_argument("--uncertainty-thresh", type=float, default=0.60)

    args = parser.parse_args()

    if args.command == "train":
        with open(args.manifest, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        splits = raw_data if ("train" in raw_data and "test" in raw_data) else create_patient_level_splits(raw_data)
        meta = train_wound_classifier(splits=splits, output_dir=Path(args.output_dir), arch=args.arch, epochs=args.epochs, batch_size=args.batch_size)
        print(f"[+] Wound training complete. Best Macro F1: {meta['best_macro_f1']} at epoch {meta['best_epoch']}.")

    elif args.command == "evaluate":
        with open(args.manifest, "r", encoding="utf-8") as f:
            splits = json.load(f)
        res = evaluate_wound_test_set(Path(args.checkpoint), splits, Path(args.output_report))
        print("[+] Evaluation Results:")
        print(json.dumps(res["per_class_metrics"], indent=2))
        print(f"    Macro F1: {res['macro_f1']} | Accuracy: {res['accuracy']}")

    elif args.command == "predict":
        meta = {}
        if args.research_metadata and Path(args.research_metadata).exists():
            with open(args.research_metadata, "r", encoding="utf-8") as f:
                meta = json.load(f)
        predictor = WoundResearchPredictor(Path(args.checkpoint), uncertainty_threshold=args.uncertainty_thresh)
        out = predictor.predict(Path(args.image), research_metadata=meta)
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
