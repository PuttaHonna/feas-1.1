"""
FEAS 2.0 - Train Image Tampering Detection Model on CASIA 2.0 Dataset
======================================================================
1. Audits dataset images for corruption and duplicates using pHash.
2. Creates strict 70/15/15 train/val/test splits.
3. Trains PyTorch ResNet-18 with ImageNet transfer learning and data augmentation.
4. Selects checkpoint by best validation F1 score.
5. Runs test set evaluation and adversarial stress-testing.
6. Saves model weights to models/tampering_resnet18_best.pt and reports to models/tampering_test_evaluation_report.json.
"""

import json
import os
import sys
import time
from pathlib import Path

# Fix OpenMP runtime duplicate error on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.common.config import FORENSIC_CONFIG
from src.common.utils import set_random_seed, get_optimal_device
from src.tampering.dataset_audit import DatasetAuditor
from src.tampering.train import train_tampering_classifier
from src.tampering.evaluate import evaluate_test_set as evaluate_tampering_test_set


def main():
    set_random_seed(42)
    device = get_optimal_device()
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    data_dir = BASE_DIR / "data"

    print("=" * 70)
    print("STEP 1: AUDITING & SPLITTING CASIA 2.0 TAMPERING DATASET")
    print("=" * 70)

    tamper_dataset_dir = data_dir / "open_datasets" / "tampering"
    auditor = DatasetAuditor(
        dataset_dir=tamper_dataset_dir,
        classes=("authentic", "tampered"),
        near_duplicate_hamming_thresh=3,
        random_seed=42,
    )

    print("Auditing images, computing SHA-256 and pHash perceptual signatures...")
    audit_results = auditor.audit()
    print(f"  • Valid images verified:   {audit_results.get('total_valid_images', 0)}")
    print(f"  • Corrupted files removed: {len(audit_results.get('corrupted_files', []))}")
    print(f"  • Exact duplicates:        {len(audit_results.get('exact_duplicates', []))}")
    print(f"  • Near-duplicates pruned:  {len(audit_results.get('near_duplicates', []))}")

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

    print(f"  • Train split : {len(manifest_data['train'])} samples")
    print(f"  • Val split   : {len(manifest_data['val'])} samples")
    print(f"  • Test split  : {len(manifest_data['test'])} samples")

    print("\n" + "=" * 70)
    print("STEP 2: TRAINING RESNET-18 ON CASIA 2.0 BENCHMARK")
    print("=" * 70)
    print(f"Using Compute Device: {device}")
    print("Optimizing parameters via AdamW + ReduceLROnPlateau with Class-Weighted Loss...")

    tamper_history = train_tampering_classifier(
        manifest_path=tamper_manifest,
        output_dir=models_dir,
        arch="resnet18",
        epochs=10,
        batch_size=16,
        lr=1e-4,
        patience=6,
        pretrained=True,
    )

    tamper_best_ckpt = models_dir / "tampering_resnet18_best.pt"
    ckpt_size_mb = round(tamper_best_ckpt.stat().st_size / (1024 * 1024), 2)
    print(f"\n[OK] Model Checkpoint successfully saved: {tamper_best_ckpt} ({ckpt_size_mb} MB)")

    # Sync to FEAS models directory
    feas_ckpt = BASE_DIR / "FEAS" / "models" / "tampering_resnet18_best.pt"
    feas_ckpt.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(tamper_best_ckpt, feas_ckpt)
    print(f"[OK] Synced weights to FEAS: {feas_ckpt}")

    print("\n" + "=" * 70)
    print("STEP 3: TEST SET EVALUATION & ADVERSARIAL STRESS TESTING")
    print("=" * 70)

    tamper_report_path = models_dir / "tampering_test_evaluation_report.json"
    tamper_eval = evaluate_tampering_test_set(
        checkpoint_path=tamper_best_ckpt,
        manifest_path=tamper_manifest,
        output_report_path=tamper_report_path,
    )
    clean = tamper_eval.get("clean_test_metrics", {})
    print("CASIA 2.0 Test Set Performance Metrics:")
    print(f"  • Accuracy  : {clean.get('accuracy', 0):.4f}")
    print(f"  • Precision : {clean.get('precision', 0):.4f}")
    print(f"  • Recall    : {clean.get('recall', 0):.4f}")
    print(f"  • F1-Score  : {clean.get('f1', 0):.4f}")
    print(f"  • Evaluated : {clean.get('evaluated_samples', 0)} samples")

    print("\nPerturbation & Stress Robustness:")
    for attack, res in tamper_eval.get("robustness_stress_tests", {}).items():
        print(f"  • Attack [{attack:15s}] -> F1: {res.get('f1', 0):.4f} (Accuracy: {res.get('accuracy', 0):.4f})")

    print("\n" + "=" * 70)
    print("TRAINING & EVALUATION COMPLETE!")
    print(f"Report saved: {tamper_report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
