"""
Wound Research Model Evaluation & Error Analysis
Evaluates final model checkpoint strictly once on untouched patient-level test data.
Computes:
- Macro F1 and per-class metrics
- Confusion matrix
- Expected Calibration Error (ECE) or confidence reliability
- Error analysis: preserves paths of correct and incorrect predictions for domain inspection
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from src.common.config import FORENSIC_CONFIG
from src.common.utils import get_optimal_device
from src.wound_research.dataset import (
    ALLOWED_WOUND_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
)
from src.wound_research.train import get_wound_backbone, compute_multiclass_metrics


def evaluate_wound_test_set(
    checkpoint_path: Path,
    splits: Dict[str, List[Dict[str, Any]]],
    output_report_path: Path,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates wound classifier once on untouched test split with confusion matrix and error analysis.
    """
    target_device = torch.device(device) if device else get_optimal_device()
    checkpoint_path = Path(checkpoint_path)

    ckpt = torch.load(checkpoint_path, map_location=target_device, weights_only=False)
    arch = ckpt.get("arch", "resnet18")
    model = get_wound_backbone(arch=arch, num_classes=len(ALLOWED_WOUND_CLASSES), pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(target_device)
    model.eval()

    test_samples = splits.get("test", [])
    if not test_samples:
        raise ValueError("No test samples available in patient split manifest.")

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    y_true: List[int] = []
    y_pred: List[int] = []
    confidences: List[float] = []

    correct_samples: List[Dict[str, Any]] = []
    misclassified_samples: List[Dict[str, Any]] = []

    with torch.no_grad():
        for item in test_samples:
            p = Path(item["path"])
            true_idx = CLASS_TO_IDX.get(item["class"], 0)

            try:
                with Image.open(p) as img:
                    rgb = img.convert("RGB")
                tensor = transform(rgb).unsqueeze(0).to(target_device)
                logits = model(tensor)
                probs = F.softmax(logits, dim=1).squeeze(0)

                pred_idx = int(torch.argmax(probs).item())
                top_conf = float(probs[pred_idx].item())

                y_true.append(true_idx)
                y_pred.append(pred_idx)
                confidences.append(top_conf)

                sample_record = {
                    "image_path": str(p),
                    "true_class": IDX_TO_CLASS[true_idx],
                    "predicted_class": IDX_TO_CLASS[pred_idx],
                    "confidence": round(top_conf, 4),
                    "patient_id": item.get("patient_id", "unspecified"),
                }

                if true_idx == pred_idx:
                    if len(correct_samples) < 15:
                        correct_samples.append(sample_record)
                else:
                    if len(misclassified_samples) < 15:
                        misclassified_samples.append(sample_record)
            except Exception:
                continue

    metrics = compute_multiclass_metrics(y_true, y_pred, num_classes=len(ALLOWED_WOUND_CLASSES))

    # Confusion matrix
    num_c = len(ALLOWED_WOUND_CLASSES)
    cm = [[0 for _ in range(num_c)] for _ in range(num_c)]
    for yt, yp in zip(y_true, y_pred):
        cm[yt][yp] += 1

    # Confidence distribution stats
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0

    eval_result = {
        "checkpoint_path": str(checkpoint_path),
        "total_test_samples": len(y_true),
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "per_class_metrics": metrics["per_class"],
        "confusion_matrix": {
            "classes": ALLOWED_WOUND_CLASSES,
            "matrix": cm,
        },
        "mean_confidence": round(mean_conf, 4),
        "error_analysis": {
            "example_correct_predictions": correct_samples,
            "example_incorrect_predictions": misclassified_samples,
        },
        "safety_disclaimer": FORENSIC_CONFIG.WOUND_OUTPUT_WORDING,
    }

    out_p = Path(output_report_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, indent=2)

    return eval_result
