"""
Single-Pass Test Evaluation & Robustness Stress Testing
Evaluates final model checkpoint strictly once on untouched test data.
Executes robustness perturbations:
- JPEG recompression
- Gaussian blur
- Brightness shifts
- Scaling/resizing artifacts
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import io
import torch
from torchvision import transforms
from PIL import Image, ImageEnhance, ImageFilter

from src.tampering.train import get_model, compute_binary_metrics
from src.common.utils import get_optimal_device


def _load_model_for_eval(checkpoint_path: Path, device: torch.device) -> Tuple[torch.nn.Module, Dict[str, int]]:
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    arch = ckpt.get("arch", "resnet18")
    class_to_idx = ckpt.get("class_to_idx", {"authentic": 0, "manipulated": 1})
    model = get_model(arch=arch, num_classes=len(class_to_idx))
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model, class_to_idx


def evaluate_test_set(
    checkpoint_path: Path,
    manifest_path: Path,
    output_report_path: Path,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates the model once on untouched test data and runs robustness tests.
    """
    target_device = torch.device(device) if device else get_optimal_device()
    checkpoint_path = Path(checkpoint_path)
    model, class_to_idx = _load_model_for_eval(checkpoint_path, target_device)

    with open(manifest_path, "r", encoding="utf-8") as f:
        splits = json.load(f)

    test_samples = splits.get("test", [])
    if not test_samples:
        raise ValueError("No test samples found in split manifest.")

    base_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    def run_inference(image_loader_func) -> Dict[str, Any]:
        y_true: List[int] = []
        y_pred: List[int] = []

        with torch.no_grad():
            for item in test_samples:
                p = Path(item["path"])
                label = class_to_idx[item["class"]]
                try:
                    with Image.open(p) as img:
                        pil_img = img.convert("RGB")
                    pil_img = image_loader_func(pil_img)
                    tensor = base_transform(pil_img).unsqueeze(0).to(target_device)
                    outputs = model(tensor)
                    pred = int(torch.argmax(outputs, dim=1).item())
                    y_true.append(label)
                    y_pred.append(pred)
                except Exception:
                    continue

        metrics = compute_binary_metrics(y_true, y_pred)
        # Confusion matrix
        tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)

        metrics["confusion_matrix"] = {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
        }
        metrics["evaluated_samples"] = len(y_true)
        return metrics

    # 1. Standard untouched test evaluation
    clean_metrics = run_inference(lambda img: img)

    # 2. Robustness Stress Tests
    # A. JPEG Recompression (Quality 60)
    def apply_jpeg_recomp(img: Image.Image) -> Image.Image:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    jpeg_metrics = run_inference(apply_jpeg_recomp)

    # B. Gaussian Blur (radius=1.5)
    def apply_blur(img: Image.Image) -> Image.Image:
        return img.filter(ImageFilter.GaussianBlur(radius=1.5))

    blur_metrics = run_inference(apply_blur)

    # C. Brightness Shift (+25%)
    def apply_brightness(img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(1.25)

    brightness_metrics = run_inference(apply_brightness)

    # D. Downscaling & Upscaling (0.5x)
    def apply_rescale(img: Image.Image) -> Image.Image:
        w, h = img.size
        small = img.resize((max(1, w // 2), max(1, h // 2)), Image.Resampling.BILINEAR)
        return small.resize((w, h), Image.Resampling.BILINEAR)

    rescale_metrics = run_inference(apply_rescale)

    full_evaluation = {
        "checkpoint_path": str(checkpoint_path),
        "manifest_path": str(manifest_path),
        "clean_test_metrics": clean_metrics,
        "robustness_tests": {
            "jpeg_recompression_q60": jpeg_metrics,
            "gaussian_blur_r1_5": blur_metrics,
            "brightness_boost_25pct": brightness_metrics,
            "downscale_upscale_0_5x": rescale_metrics,
        },
    }

    out_p = Path(output_report_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(full_evaluation, f, indent=2)

    return full_evaluation
