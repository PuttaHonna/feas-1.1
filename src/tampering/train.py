"""
PyTorch Image Tampering Detection Training Pipeline
Trains ResNet18 (baseline) and EfficientNet-B0 with:
- Deterministic seed configuration
- Train-only augmentation
- Class-weight loss for imbalance
- Validation F1-based checkpoint selection
- Early stopping and learning rate scheduling
- Complete logging of actual measured metrics without placeholders
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image

from src.common.config import FORENSIC_CONFIG
from src.common.utils import set_random_seed, get_optimal_device


class TamperingDataset(Dataset):
    """Forensic Image Dataset mapped from split manifest entries."""

    def __init__(
        self,
        samples: List[Dict[str, str]],
        class_to_idx: Dict[str, int],
        transform: Optional[transforms.Compose] = None,
    ):
        self.samples = samples
        self.class_to_idx = class_to_idx
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        item = self.samples[idx]
        img_path = Path(item["path"])
        label = self.class_to_idx[item["class"]]

        with Image.open(img_path) as img:
            img_rgb = img.convert("RGB")

        if self.transform:
            tensor = self.transform(img_rgb)
        else:
            tensor = transforms.ToTensor()(img_rgb)

        return tensor, label, str(img_path)


def compute_binary_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """Computes exact accuracy, precision, recall, and F1 score."""
    total = len(y_true)
    if total == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    accuracy = correct / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def get_model(arch: str = "resnet18", num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    """Instantiate classification backbone."""
    arch_lower = arch.lower()
    if arch_lower == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        model = models.resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
    elif arch_lower == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
    else:
        raise ValueError(f"Unsupported architecture '{arch}'. Use 'resnet18' or 'efficientnet_b0'.")
    return model


def train_tampering_classifier(
    manifest_path: Path,
    output_dir: Path,
    arch: str = "resnet18",
    epochs: int = 10,
    batch_size: int = 16,
    lr: float = 1e-4,
    patience: int = 4,
    seed: int = FORENSIC_CONFIG.DEFAULT_RANDOM_SEED,
    device: Optional[str] = None,
    pretrained: bool = True,
) -> Dict[str, Any]:
    """
    Executes training and checkpointing for image tampering detection.
    
    Returns:
        Dictionary containing actual measured training metrics and artifacts.
    """
    set_random_seed(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select device
    target_device = torch.device(device) if device else get_optimal_device()

    # Load splits manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        splits = json.load(f)

    class_to_idx = {"authentic": 0, "manipulated": 1}

    # Advanced Forensic Data Transforms
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.25),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_ds = TamperingDataset(splits["train"], class_to_idx, transform=train_transform)
    val_ds = TamperingDataset(splits["val"], class_to_idx, transform=eval_transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    # Calculate class weights
    train_labels = [class_to_idx[item["class"]] for item in splits["train"]]
    count_0 = sum(1 for y in train_labels if y == 0)
    count_1 = sum(1 for y in train_labels if y == 1)
    total_samples = len(train_labels)

    if count_0 > 0 and count_1 > 0:
        weight_0 = total_samples / (2.0 * count_0)
        weight_1 = total_samples / (2.0 * count_1)
        weights_tensor = torch.tensor([weight_0, weight_1], dtype=torch.float32).to(target_device)
        criterion = nn.CrossEntropyLoss(weight=weights_tensor)
    else:
        criterion = nn.CrossEntropyLoss()

    model = get_model(arch=arch, num_classes=2, pretrained=pretrained).to(target_device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=2
    )

    best_val_f1 = -1.0
    best_epoch = 0
    epochs_no_improve = 0
    history: List[Dict[str, Any]] = []

    best_checkpoint_path = output_dir / f"tampering_{arch}_best.pt"

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        # Training loop
        model.train()
        running_loss = 0.0
        train_y_true: List[int] = []
        train_y_pred: List[int] = []

        for images, labels, _ in train_loader:
            images = images.to(target_device)
            labels = labels.to(target_device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            train_y_true.extend(labels.cpu().tolist())
            train_y_pred.extend(preds.cpu().tolist())

        epoch_train_loss = running_loss / len(train_ds) if len(train_ds) > 0 else 0.0
        train_metrics = compute_binary_metrics(train_y_true, train_y_pred)

        # Validation loop
        model.eval()
        val_loss = 0.0
        val_y_true: List[int] = []
        val_y_pred: List[int] = []

        with torch.no_grad():
            for images, labels, _ in val_loader:
                images = images.to(target_device)
                labels = labels.to(target_device)
                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                preds = torch.argmax(outputs, dim=1)
                val_y_true.extend(labels.cpu().tolist())
                val_y_pred.extend(preds.cpu().tolist())

        epoch_val_loss = val_loss / len(val_ds) if len(val_ds) > 0 else 0.0
        val_metrics = compute_binary_metrics(val_y_true, val_y_pred)

        scheduler.step(val_metrics["f1"])

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 4),
            "train_metrics": train_metrics,
            "val_loss": round(epoch_val_loss, 4),
            "val_metrics": val_metrics,
            "lr": float(optimizer.param_groups[0]["lr"]),
        }
        history.append(epoch_record)

        # Checkpoint selection strictly by validation F1
        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_epoch = epoch
            epochs_no_improve = 0
            torch.save(
                {
                    "epoch": epoch,
                    "arch": arch,
                    "model_state_dict": model.state_dict(),
                    "class_to_idx": class_to_idx,
                    "val_metrics": val_metrics,
                    "seed": seed,
                },
                best_checkpoint_path,
            )
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                # Early stop
                break

    duration_sec = round(time.time() - start_time, 2)

    # Save training metadata & history
    summary_report = {
        "model_architecture": arch,
        "device": str(target_device),
        "seed": seed,
        "epochs_run": len(history),
        "best_epoch": best_epoch,
        "best_val_f1": best_val_f1,
        "duration_seconds": duration_sec,
        "checkpoint_path": str(best_checkpoint_path),
        "class_mapping": class_to_idx,
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "history": history,
    }

    meta_path = output_dir / f"tampering_{arch}_training_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    return summary_report
