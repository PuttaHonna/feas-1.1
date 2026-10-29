"""
FEAS 2.0 - End-to-End Real Model Training & Evaluation Runner
Audits real downloaded datasets, executes PyTorch transfer learning training,
saves actual checkpoint weights, and measures real test evaluation metrics.
"""

import sys
import os
import json
import time
from pathlib import Path

# OpenMP CPU Thread contention fix on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.common.config import FORENSIC_CONFIG
from src.common.utils import set_random_seed
from src.tampering.dataset_audit import DatasetAuditor
from src.tampering.train import train_tampering_classifier
from src.tampering.evaluate import evaluate_test_set as evaluate_tampering_test_set
from src.wound_research.dataset import create_patient_level_splits
from src.wound_research.train import train_wound_classifier
from src.wound_research.evaluate import evaluate_wound_test_set


def run_pipeline():
    set_random_seed(42)
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    data_dir = BASE_DIR / "data"

    print("=" * 70)
    print("STAGE 1: AUDITING & SPLITTING REAL IMAGE TAMPERING DATASET")
    print("=" * 70)

    tamper_dataset_dir = data_dir / "open_datasets" / "tampering"
    auditor = DatasetAuditor(
        dataset_dir=tamper_dataset_dir,
        classes=("authentic", "tampered"),
        near_duplicate_hamming_thresh=3,
        random_seed=42,
    )

    print("Scanning for corruptions, hashing, and duplicate clustering...")
    audit_results = auditor.audit()
    print(f"  • Total valid images scanned: {audit_results.get('total_valid_images', 0)}")
    print(f"  • Corrupted files found:      {len(audit_results.get('corrupted_files', []))}")
    print(f"  • Exact duplicates:           {len(audit_results.get('exact_duplicates', []))}")
    print(f"  • Near-duplicates (pHash):    {len(audit_results.get('near_duplicates', []))}")

    tamper_manifest = data_dir / "tampering_splits.json"
    splits = auditor.create_clean_splits(
        output_manifest_path=tamper_manifest,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
    )


    # Remap class names to "authentic" and "manipulated" for model loader
    with open(tamper_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    for split_key in ["train", "val", "test"]:
        for item in manifest_data[split_key]:
            if item["class"] == "tampered":
                item["class"] = "manipulated"

    with open(tamper_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"  • Train split: {len(manifest_data['train'])} samples")
    print(f"  • Val split:   {len(manifest_data['val'])} samples")
    print(f"  • Test split:  {len(manifest_data['test'])} samples")

    print("\n" + "=" * 70)
    print("STAGE 2: TRAINING REAL RESNET-18 TAMPERING DETECTION MODEL")
    print("=" * 70)
    print("Training PyTorch ResNet-18 with ImageNet initialization (4 epochs on CPU)...")

    tamper_history = train_tampering_classifier(
        manifest_path=tamper_manifest,
        output_dir=models_dir,
        arch="resnet18",
        epochs=4,
        batch_size=16,
        lr=1e-4,
        pretrained=True,
    )

    tamper_best_ckpt = models_dir / "tampering_resnet18_best.pt"
    print(f"[OK] Checkpoint saved: {tamper_best_ckpt} (Size: {round(tamper_best_ckpt.stat().st_size / (1024*1024), 2)} MB)")

    print("\n" + "=" * 70)
    print("STAGE 3: EVALUATING REAL TAMPERING MODEL & STRESS TESTING")
    print("=" * 70)

    tamper_report_path = models_dir / "tampering_test_evaluation_report.json"
    tamper_eval = evaluate_tampering_test_set(
        checkpoint_path=tamper_best_ckpt,
        manifest_path=tamper_manifest,
        output_report_path=tamper_report_path,
    )
    clean = tamper_eval.get("clean_test_metrics", {})
    print(f"Test Set Evaluation Metrics:")
    print(f"  • Accuracy:  {clean.get('accuracy', 0):.4f}")
    print(f"  • Precision: {clean.get('precision', 0):.4f}")
    print(f"  • Recall:    {clean.get('recall', 0):.4f}")
    print(f"  • F1-Score:  {clean.get('f1', 0):.4f}")
    print(f"  • Evaluated: {clean.get('evaluated_samples', 0)} samples")

    print("\nRobustness Stress Testing (Perturbations):")
    for attack, res in tamper_eval.get("robustness_stress_tests", {}).items():
        print(f"  • Attack [{attack:15s}] -> F1: {res.get('f1', 0):.4f} (Accuracy: {res.get('accuracy', 0):.4f})")

    print("\n" + "=" * 70)
    print("STAGE 4: AUDITING & SPLITTING REAL ISIC WOUND/LESION DATASET")
    print("=" * 70)

    wound_meta_file = data_dir / "open_datasets" / "wound" / "metadata.json"
    wound_img_dir = data_dir / "open_datasets" / "wound" / "images"

    with open(wound_meta_file, "r", encoding="utf-8") as f:
        raw_wound_meta = json.load(f)

    wound_samples = []
    for item in raw_wound_meta:
        img_p = wound_img_dir / item["image_filename"]
        if img_p.exists():
            wound_samples.append({
                "path": str(img_p),
                "class": item["label"],
                "patient_id": item["patient_id"],
                "research_provenance": True,
            })

    print(f"Loaded {len(wound_samples)} consented clinical samples.")
    wound_splits = create_patient_level_splits(
        samples=wound_samples,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    )

    wound_manifest = data_dir / "wound_splits.json"
    with open(wound_manifest, "w", encoding="utf-8") as f:
        json.dump(wound_splits, f, indent=2)

    print(f"  • Patient-Disjoint Train: {len(wound_splits['train'])} samples")
    print(f"  • Patient-Disjoint Val:   {len(wound_splits['val'])} samples")
    print(f"  • Patient-Disjoint Test:  {len(wound_splits['test'])} samples")

    print("\n" + "=" * 70)
    print("STAGE 5: TRAINING REAL RESNET-18 WOUND RESEARCH CLASSIFIER")
    print("=" * 70)
    print("Training PyTorch ResNet-18 with patient-level isolation & class weighting...")

    wound_history = train_wound_classifier(
        splits=wound_splits,
        output_dir=models_dir,
        arch="resnet18",
        epochs=4,
        batch_size=16,
        lr=1e-4,
        pretrained=True,
    )

    wound_best_ckpt = models_dir / "wound_resnet18_best.pt"
    print(f"[OK] Checkpoint saved: {wound_best_ckpt} (Size: {round(wound_best_ckpt.stat().st_size / (1024*1024), 2)} MB)")

    print("\n" + "=" * 70)
    print("STAGE 6: EVALUATING REAL WOUND RESEARCH CLASSIFIER")
    print("=" * 70)

    wound_report_path = models_dir / "wound_test_evaluation_report.json"
    wound_eval = evaluate_wound_test_set(
        checkpoint_path=wound_best_ckpt,
        splits=wound_splits,
        output_report_path=wound_report_path,
    )
    print(f"Wound Classifier Test Metrics:")
    print(f"  • Accuracy: {wound_eval['accuracy']:.4f}")
    print(f"  • Macro F1: {wound_eval['macro_f1']:.4f}")
    print(f"  • Per-Class Performance:")
    for cname, cstats in wound_eval.get("per_class", {}).items():
        if cstats.get("support", 0) > 0:
            print(f"    - {cname:15s} -> F1: {cstats['f1']:.4f} | Prec: {cstats['precision']:.4f} | Rec: {cstats['recall']:.4f} (N={cstats['support']})")

    # Save complete run summary report to artifacts
    summary_report = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tampering_model": {
            "checkpoint": str(tamper_best_ckpt),
            "architecture": "resnet18",
            "epochs": 4,
            "test_accuracy": clean.get("accuracy", 0),
            "test_f1": clean.get("f1", 0),
            "confusion_matrix": clean.get("confusion_matrix", {}),
            "robustness": tamper_eval.get("robustness_stress_tests", {}),
        },
        "wound_model": {
            "checkpoint": str(wound_best_ckpt),
            "architecture": "resnet18",
            "epochs": 4,
            "test_accuracy": wound_eval["accuracy"],
            "test_macro_f1": wound_eval["macro_f1"],
            "per_class": wound_eval.get("per_class", {}),
        },
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }

    report_path = BASE_DIR / "data" / "training_summary_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print("\n" + "=" * 70)
    print(f"ALL TRAINING & BENCHMARKING COMPLETE!")
    print(f"Summary report written to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
