"""
Unit and integration tests for Module 1: Image Tampering Detection.
"""

import json
from pathlib import Path
import pytest
from PIL import Image
import torch
import numpy as np

from src.tampering.dataset_audit import DatasetAuditor
from src.tampering.train import train_tampering_classifier, compute_binary_metrics
from src.tampering.evaluate import evaluate_test_set
from src.tampering.predict import TamperingPredictor
from src.common.config import FORENSIC_CONFIG


@pytest.fixture
def dummy_dataset_dir(tmp_path: Path) -> Path:
    """Creates a small mock dataset directory for testing audit and splits."""
    ds_dir = tmp_path / "mock_dataset"
    auth_dir = ds_dir / "authentic"
    man_dir = ds_dir / "manipulated"
    auth_dir.mkdir(parents=True)
    man_dir.mkdir(parents=True)

    # 4 Authentic images
    for i in range(4):
        arr = np.full((128, 128, 3), 50 + i * 20, dtype=np.uint8)
        arr[::10, :] = 255
        Image.fromarray(arr).save(auth_dir / f"auth_{i}.png")

    # 4 Manipulated images
    for i in range(4):
        arr = np.full((128, 128, 3), 100 + i * 20, dtype=np.uint8)
        arr[:, ::10] = 255
        Image.fromarray(arr).save(man_dir / f"man_{i}.png")

    # 1 exact duplicate in manipulated
    img_dup = Image.open(man_dir / "man_0.png")
    img_dup.save(man_dir / "man_0_dup.png")

    # 1 corrupted file
    corrupt_file = man_dir / "corrupted.jpg"
    corrupt_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)

    return ds_dir


def test_dataset_audit_and_splitting(dummy_dataset_dir: Path, tmp_path: Path):
    auditor = DatasetAuditor(dummy_dataset_dir)
    report = auditor.audit()

    assert report["corrupted_files_count"] == 1
    assert report["exact_duplicate_groups_count"] >= 1
    assert report["total_valid_images"] == 9  # 4 auth + 5 man (4 orig + 1 dup)

    manifest_path = tmp_path / "manifest.json"
    splits = auditor.create_clean_splits(manifest_path, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)

    assert "train" in splits
    assert "val" in splits
    assert "test" in splits

    # Ensure no duplicates cross splits
    train_shas = {s["sha256"] for s in splits["train"]}
    val_shas = {s["sha256"] for s in splits["val"]}
    test_shas = {s["sha256"] for s in splits["test"]}

    assert len(train_shas.intersection(val_shas)) == 0
    assert len(train_shas.intersection(test_shas)) == 0
    assert len(val_shas.intersection(test_shas)) == 0


def test_train_and_evaluate_pipeline(dummy_dataset_dir: Path, tmp_path: Path):
    auditor = DatasetAuditor(dummy_dataset_dir)
    manifest_path = tmp_path / "splits.json"
    auditor.create_clean_splits(manifest_path, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)

    output_dir = tmp_path / "models"
    # Fast 1-epoch training on CPU with random weights for speed
    train_meta = train_tampering_classifier(
        manifest_path=manifest_path,
        output_dir=output_dir,
        arch="resnet18",
        epochs=1,
        batch_size=4,
        device="cpu",
        pretrained=False,
    )

    ckpt_path = Path(train_meta["checkpoint_path"])
    assert ckpt_path.exists()
    assert train_meta["model_architecture"] == "resnet18"
    assert "history" in train_meta

    # Test single-pass evaluation
    eval_report_path = output_dir / "eval_report.json"
    eval_meta = evaluate_test_set(
        checkpoint_path=ckpt_path,
        manifest_path=manifest_path,
        output_report_path=eval_report_path,
        device="cpu",
    )

    assert eval_report_path.exists()
    assert "clean_test_metrics" in eval_meta
    assert "robustness_tests" in eval_meta
    assert "jpeg_recompression_q60" in eval_meta["robustness_tests"]


def test_tampering_predictor_and_quality_gate(dummy_dataset_dir: Path, tmp_path: Path):
    auditor = DatasetAuditor(dummy_dataset_dir)
    manifest_path = tmp_path / "splits.json"
    auditor.create_clean_splits(manifest_path, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25)

    output_dir = tmp_path / "models"
    train_meta = train_tampering_classifier(
        manifest_path=manifest_path,
        output_dir=output_dir,
        arch="resnet18",
        epochs=1,
        batch_size=4,
        device="cpu",
        pretrained=False,
    )
    ckpt_path = Path(train_meta["checkpoint_path"])

    predictor = TamperingPredictor(checkpoint_path=ckpt_path, device="cpu")

    # 1. Valid sharp image inference
    test_img = dummy_dataset_dir / "authentic" / "auth_0.png"
    cam_out = tmp_path / "test_cam.png"
    result = predictor.predict(test_img, generate_gradcam=True, gradcam_output_path=cam_out)

    assert result["status"] == "completed"
    assert "disclaimer" in result
    assert result["disclaimer"] == FORENSIC_CONFIG.MANDATORY_DISCLAIMER
    assert cam_out.exists()
    assert "definitely forged" not in result["explanation_wording"]

    # 2. Blurred image failure
    blurred_img_path = tmp_path / "blurred.png"
    arr = np.full((128, 128, 3), 128, dtype=np.uint8)
    Image.fromarray(arr).save(blurred_img_path)

    blur_result = predictor.predict(blurred_img_path)
    assert blur_result["status"] == "failed_quality_gate"
    assert blur_result["predicted_label"] == "uncertain / unsupported"
    assert any("too blurred" in r for r in blur_result["rejection_reasons"])
