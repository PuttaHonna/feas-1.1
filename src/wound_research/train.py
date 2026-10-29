"""
Wound Research Model Training Pipeline
Trains ResNet18 / EfficientNet-B0 baseline with:
- Patient-level split validation
- Class-weighted multi-class CrossEntropyLoss
- Validation Macro-F1 checkpoint selection
- Early stopping
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models, transforms
from collections import Counter

from src.common.config import FORENSIC_CONFIG
from src.common.utils import set_random_seed, get_optimal_device
from src.wound_research.dataset import (
    WoundResearchDataset,
    ALLOWED_WOUND_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
)


def compute_multiclass_metrics(
    y_true: List[int],
    y_pred: List[int],
    num_classes: int = len(ALLOWED_WOUND_CLASSES),
) -> Dict[str, Any]:
    """Computes exact accuracy, per-class precision/recall/F1, and macro F1."""
    total = len(y_true)
    if total == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}}

    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / total

    per_class = {}
    f1_list = []

    for c in range(num_classes):
        c_name = IDX_TO_CLASS.get(c, str(c))
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class[c_name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": sum(1 for yt in y_true if yt == c),
        }
        f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
    }


def get_wound_backbone(arch: str = "resnet18", num_classes: int = len(ALLOWED_WOUND_CLASSES), pretrained: bool = True) -> nn.Module:
    """Instantiate classification backbone."""
    if arch == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        model = models.resnet18(weights=weights)
        in_f = model.fc.in_features
        model.fc = nn.Linear(in_f, num_classes)
    elif arch == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        in_f = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_f, num_classes)
    else:
        raise ValueError(f"Unsupported backbone: {arch}")
    return model


def train_wound_classifier(
    splits: Dict[str, List[Dict[str, Any]]],
    output_dir: Path,
    arch: str = "resnet18",
    epochs: int = 10,
    batch_size: int = 8,
    lr: float = 1e-4,
    patience: int = 4,
    seed: int = FORENSIC_CONFIG.DEFAULT_RANDOM_SEED,
    device: Optional[str] = None,
    pretrained: bool = True,
) -> Dict[str, Any]:
    """
    Executes training on patient-split research dataset.
    """
    set_random_seed(seed)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target_device = torch.device(device) if device else get_optimal_device()

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_ds = WoundResearchDataset(splits["train"], transform=train_transform)
    val_ds = WoundResearchDataset(splits["val"] if splits.get("val") else splits["train"], transform=eval_transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    # Calculate class weights for imbalance
    train_labels = [CLASS_TO_IDX.get(s["class"], 0) for s in splits["train"]]
    counts = Counter(train_labels)
    total_n = len(train_labels)
    weights = []
    for c in range(len(ALLOWED_WOUND_CLASSES)):
        c_count = counts.get(c, 0)
        w = (total_n / (len(ALLOWED_WOUND_CLASSES) * c_count)) if c_count > 0 else 1.0
        weights.append(w)

    weights_tensor = torch.tensor(weights, dtype=torch.float32).to(target_device)
    criterion = nn.CrossEntropyLoss(weight=weights_tensor)

    model = get_wound_backbone(arch=arch, num_classes=len(ALLOWED_WOUND_CLASSES), pretrained=pretrained).to(target_device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    best_macro_f1 = -1.0
    best_epoch = 0
    epochs_no_improve = 0
    history = []
    ckpt_path = out_dir / f"wound_{arch}_best.pt"

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        y_true, y_pred = [], []

        for images, labels, _ in train_loader:
            images, labels = images.to(target_device), labels.to(target_device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            y_true.extend(labels.cpu().tolist())
            y_pred.extend(preds.cpu().tolist())

        epoch_loss = running_loss / len(train_ds) if len(train_ds) > 0 else 0.0
        train_metrics = compute_multiclass_metrics(y_true, y_pred)

        # Validation
        model.eval()
        val_loss = 0.0
        val_true, val_pred = [], []

        with torch.no_grad():
            for images, labels, _ in val_loader:
                images, labels = images.to(target_device), labels.to(target_device)
                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                preds = torch.argmax(outputs, dim=1)
                val_true.extend(labels.cpu().tolist())
                val_pred.extend(preds.cpu().tolist())

        val_epoch_loss = val_loss / len(val_ds) if len(val_ds) > 0 else 0.0
        val_metrics = compute_multiclass_metrics(val_true, val_pred)

        scheduler.step(val_metrics["macro_f1"])

        history.append({
            "epoch": epoch,
            "train_loss": round(epoch_loss, 4),
            "train_macro_f1": train_metrics["macro_f1"],
            "val_loss": round(val_epoch_loss, 4),
            "val_macro_f1": val_metrics["macro_f1"],
        })

        if val_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = val_metrics["macro_f1"]
            best_epoch = epoch
            epochs_no_improve = 0
            torch.save({
                "epoch": epoch,
                "arch": arch,
                "model_state_dict": model.state_dict(),
                "class_to_idx": CLASS_TO_IDX,
                "val_metrics": val_metrics,
                "seed": seed,
            }, ckpt_path)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                break

    duration = round(time.time() - start_time, 2)

    summary = {
        "model_architecture": arch,
        "best_epoch": best_epoch,
        "best_macro_f1": best_macro_f1,
        "checkpoint_path": str(ckpt_path),
        "duration_seconds": duration,
        "classes": ALLOWED_WOUND_CLASSES,
        "history": history,
        "safety_disclaimer": FORENSIC_CONFIG.WOUND_OUTPUT_WORDING,
    }

    with open(out_dir / f"wound_{arch}_training_meta.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary
