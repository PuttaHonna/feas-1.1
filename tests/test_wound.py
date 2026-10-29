"""
Unit and integration tests for Module 3: Wound Image Research Classification.
"""

from pathlib import Path
import pytest
from PIL import Image
import numpy as np

from src.wound_research.dataset import (
    verify_research_provenance,
    create_patient_level_splits,
    ALLOWED_WOUND_CLASSES,
)
from src.wound_research.train import train_wound_classifier
from src.wound_research.evaluate import evaluate_wound_test_set
from src.wound_research.predict import WoundResearchPredictor
from src.common.config import FORENSIC_CONFIG


def test_research_provenance_gate():
    # 1. Unconsented upload must be rejected
    valid, reason = verify_research_provenance({})
    assert valid is False
    assert "rejected by policy" in reason

    # 2. Incomplete metadata rejected
    valid, reason = verify_research_provenance({"research_dataset_id": "DS_101"})
    assert valid is False
    assert "ethical_consent_documented" in reason

    # 3. Fully documented research metadata passes
    valid, _ = verify_research_provenance({
        "research_dataset_id": "WOUND_BENCHMARK_2023",
        "ethical_consent_documented": True,
        "research_license": "Academic Research Use Agreement",
    })
    assert valid is True


def test_patient_level_splits():
    # 10 samples from 4 patients
    samples = [
        {"path": "/tmp/img1.png", "class": "abrasion", "patient_id": "P_001"},
        {"path": "/tmp/img2.png", "class": "abrasion", "patient_id": "P_001"},
        {"path": "/tmp/img3.png", "class": "burn", "patient_id": "P_002"},
        {"path": "/tmp/img4.png", "class": "burn", "patient_id": "P_002"},
        {"path": "/tmp/img5.png", "class": "laceration", "patient_id": "P_003"},
        {"path": "/tmp/img6.png", "class": "laceration", "patient_id": "P_003"},
        {"path": "/tmp/img7.png", "class": "incision", "patient_id": "P_004"},
        {"path": "/tmp/img8.png", "class": "incision", "patient_id": "P_004"},
    ]

    splits = create_patient_level_splits(samples, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)

    train_pids = {s["patient_id"] for s in splits["train"]}
    val_pids = {s["patient_id"] for s in splits["val"]}
    test_pids = {s["patient_id"] for s in splits["test"]}

    # Crucial guarantee: no patient ID spans multiple splits
    assert len(train_pids.intersection(val_pids)) == 0
    assert len(train_pids.intersection(test_pids)) == 0
    assert len(val_pids.intersection(test_pids)) == 0


def test_wound_train_eval_and_predict(tmp_path: Path):
    # Create synthetic images for 3 patients
    img_dir = tmp_path / "wound_images"
    img_dir.mkdir()

    samples = []
    classes = ["abrasion", "burn", "laceration"]
    for i in range(6):
        cls_name = classes[i % len(classes)]
        img_p = img_dir / f"img_{i}.png"
        arr = np.full((128, 128, 3), 100 + i * 20, dtype=np.uint8)
        arr[::15, :] = 255
        Image.fromarray(arr).save(img_p)

        samples.append({
            "path": str(img_p),
            "class": cls_name,
            "patient_id": f"PATIENT_{(i % 3) + 1}",
        })

    splits = create_patient_level_splits(samples, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)

    out_dir = tmp_path / "wound_models"
    meta = train_wound_classifier(
        splits=splits,
        output_dir=out_dir,
        arch="resnet18",
        epochs=1,
        batch_size=2,
        device="cpu",
        pretrained=False,
    )

    ckpt_path = Path(meta["checkpoint_path"])
    assert ckpt_path.exists()

    # Evaluate
    eval_rep = out_dir / "eval.json"
    eval_res = evaluate_wound_test_set(ckpt_path, splits, eval_rep, device="cpu")
    assert eval_rep.exists()
    assert "macro_f1" in eval_res
    assert "confusion_matrix" in eval_res

    # Predict with policy gate enforcement
    predictor = WoundResearchPredictor(ckpt_path, enforce_research_consent=True, device="cpu")

    # A. Rejection when unconsented
    unconsented_out = predictor.predict(Path(samples[0]["path"]))
    assert unconsented_out["status"] == "rejected_by_policy"
    assert "rejected by policy" in unconsented_out["rejection_reason"]

    # B. Approved with documented consent
    consented_meta = {
        "research_dataset_id": "ETHICS_PROT_99",
        "ethical_consent_documented": True,
        "research_license": "Research Use Only",
    }
    approved_out = predictor.predict(Path(samples[0]["path"]), research_metadata=consented_meta)
    assert approved_out["status"] == "completed"
    assert "predicted_category" in approved_out
    assert approved_out["disclaimer"] == FORENSIC_CONFIG.WOUND_OUTPUT_WORDING
