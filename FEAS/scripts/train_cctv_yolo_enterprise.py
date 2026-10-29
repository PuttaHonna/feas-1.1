#!/usr/bin/env python3
"""
FEAS Enterprise CCTV - YOLO Surveillance Transfer Learning & Fine-Tuning Pipeline.
===================================================================================
Fine-tunes YOLO (v8 / v11 / YOLO-NAS) specifically for surveillance camera angles, small object resolution,
and diverse day/night illumination conditions.

Target Surveillance Classes:
  0: Person
  1: Car
  2: Motorcycle
  3: Bicycle
  4: Bus
  5: Truck
  6: Backpack_Bag
  7: Helmet
  8: License_Plate

Usage:
  python train_cctv_yolo_enterprise.py --data-dir data/cctv_surveillance --epochs 50 --imgsz 1280 --batch 8
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import yaml
from ultralytics import YOLO
import torch


SURVEILLANCE_CLASSES = [
    "Person",
    "Car",
    "Motorcycle",
    "Bicycle",
    "Bus",
    "Truck",
    "Backpack_Bag",
    "Helmet",
    "License_Plate"
]


def create_dataset_yaml(data_dir: Path, output_yaml: Path) -> Path:
    """Generate YOLO dataset configuration YAML for the 9 surveillance classes."""
    data_cfg = {
        "path": str(data_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {i: name for i, name in enumerate(SURVEILLANCE_CLASSES)}
    }
    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_yaml, "w") as f:
        yaml.safe_dump(data_cfg, f, sort_keys=False)
    print(f"✓ Generated surveillance dataset configuration at: {output_yaml}")
    return output_yaml


def train_surveillance_model(
    base_model: str = "yolov8m.pt",
    data_yaml: str = "data/cctv_surveillance.yaml",
    imgsz: int = 1280,
    epochs: int = 50,
    batch_size: int = 8,
    freeze_backbone_layers: int = 10,
    device: str = "0" if torch.cuda.is_available() else "cpu",
    output_dir: str = "runs/surveillance_train"
) -> Path:
    """
    Execute transfer learning with hyperparameter optimizations for CCTV surveillance:
    - imgsz=1280 to maximize mAP on small objects (backpacks, helmets, license plates, distant people).
    - Mosaic + MixUp + HSV augmentation for robust day-to-night lighting invariance.
    - Freezes first N backbone layers to preserve foundational visual primitives while adapting head to surveillance angles.
    """
    print(f"\n=======================================================")
    print(f"  FEAS Enterprise CCTV Surveillance Model Fine-Tuning  ")
    print(f"=======================================================")
    print(f"  Base Architecture     : {base_model}")
    print(f"  Target Resolution     : {imgsz}px (Small object optimized)")
    print(f"  Target Classes ({len(SURVEILLANCE_CLASSES)}) : {', '.join(SURVEILLANCE_CLASSES)}")
    print(f"  Backbone Freeze       : Layers 0 to {freeze_backbone_layers}")
    print(f"  Compute Device        : {device}")
    print(f"=======================================================\n")

    model = YOLO(base_model)

    # Launch Ultralytics training with surveillance augmentations
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        device=device,
        project=output_dir,
        name="cctv_enterprise_yolo",
        freeze=freeze_backbone_layers,
        # Surveillance augmentations
        mosaic=1.0,               # High mosaic for multi-scale crowd awareness
        mixup=0.15,               # MixUp for occlusion handling
        hsv_h=0.015,              # Hue shift for camera color grading variations
        hsv_s=0.7,                # Saturation shift for night vs day
        hsv_v=0.4,                # Value shift for shadows and glare
        fliplr=0.5,               # Horizontal flips
        cos_lr=True,              # Cosine learning rate decay
        lr0=0.01,                 # Initial learning rate
        lrf=0.01,                 # Final learning rate fraction
        workers=4,
        save=True,
        save_period=5
    )

    best_weights = Path(output_dir) / "cctv_enterprise_yolo" / "weights" / "best.pt"
    print(f"\n✓ Training completed successfully!")
    print(f"✓ Best model weights saved to: {best_weights}")
    return best_weights


def main():
    parser = argparse.ArgumentParser(description="FEAS Enterprise CCTV YOLO Model Trainer")
    parser.add_argument("--base-model", type=str, default="yolov8m.pt", help="Base model weights (yolov8n.pt, yolov8s.pt, yolov8m.pt)")
    parser.add_argument("--data-dir", type=str, default="data/cctv_surveillance", help="Directory containing images/ and labels/")
    parser.add_argument("--yaml-config", type=str, default="data/cctv_surveillance.yaml", help="Path to write/read dataset YAML")
    parser.add_argument("--imgsz", type=int, default=1280, help="Input image size (640 or 1280)")
    parser.add_argument("--epochs", type=int, default=40, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--freeze", type=int, default=10, help="Backbone layers to freeze")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    yaml_path = Path(args.yaml_config)
    if not yaml_path.exists() and data_dir.exists():
        create_dataset_yaml(data_dir, yaml_path)

    train_surveillance_model(
        base_model=args.base_model,
        data_yaml=str(yaml_path),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch_size=args.batch,
        freeze_backbone_layers=args.freeze
    )


if __name__ == "__main__":
    main()

