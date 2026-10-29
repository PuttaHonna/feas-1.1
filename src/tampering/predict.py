"""
Tampering Detection Inference Pipeline with Quality Gating & Uncertainty Rejection
Strictly adheres to forensic reporting rules:
- Fails safely on quality gate failure
- Never claims absolute certainty
- Labels all outputs as experimental advisory predictions
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from src.common.config import FORENSIC_CONFIG
from src.common.quality_gate import evaluate_image_quality
from src.tampering.train import get_model
from src.tampering.explain import generate_explanation_overlay
from src.tampering.ela import compute_ela
from src.common.utils import get_optimal_device


class TamperingPredictor:
    """Forensic Image Tampering Predictor with uncertainty threshold and advisory explanations."""

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        evaluation_meta_path: Optional[Path] = None,
        uncertainty_threshold: float = 0.65,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device) if device else get_optimal_device()
        if checkpoint_path is None:
            checkpoint_path = FORENSIC_CONFIG.MODELS_DIR / "tampering_resnet18_best.pt"
        self.checkpoint_path = Path(checkpoint_path)
        self.uncertainty_threshold = uncertainty_threshold


        # Load weights
        ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.arch = ckpt.get("arch", "resnet18")
        self.class_to_idx = ckpt.get("class_to_idx", {"authentic": 0, "manipulated": 1})
        self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}

        self.model = get_model(arch=self.arch, num_classes=len(self.class_to_idx))
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        # Load evaluation test metrics if available
        self.saved_test_metrics: Dict[str, Any] = {}
        if evaluation_meta_path and Path(evaluation_meta_path).exists():
            with open(evaluation_meta_path, "r", encoding="utf-8") as f:
                self.saved_test_metrics = json.load(f)

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def predict(
        self,
        image_path: Path,
        generate_gradcam: bool = True,
        gradcam_output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Executes pre-inference quality gate, classification, uncertainty assessment,
        and optional Grad-CAM generation.
        """
        path = Path(image_path)

        # 1. Run Pre-Inference Quality Gate
        quality = evaluate_image_quality(path)
        if not quality.passed:
            return {
                "status": "failed_quality_gate",
                "predicted_label": "uncertain / unsupported",
                "probabilities": {},
                "confidence": 0.0,
                "is_uncertain": True,
                "rejection_reasons": quality.reasons,
                "summary_message": quality.summary_message,
                "grad_cam_path": None,
                "model_version": f"{self.arch}_v1.0",
                "saved_test_metrics": self.saved_test_metrics.get("clean_test_metrics", {}),
                "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
            }

        # 2. Run Model Inference
        with Image.open(path) as img:
            rgb_img = img.convert("RGB")

        tensor = self.transform(rgb_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().tolist()

        prob_dict = {
            self.idx_to_class[i]: round(probs[i], 4) for i in range(len(probs))
        }

        top_idx = int(torch.argmax(logits, dim=1).item())
        top_prob = probs[top_idx]
        top_label = self.idx_to_class[top_idx]

        # 3. Check Uncertainty Threshold
        is_uncertain = top_prob < self.uncertainty_threshold
        if is_uncertain:
            predicted_label = "uncertain / unsupported"
            explanation_wording = (
                f"Confidence ({top_prob:.1%}) is below the reliability threshold ({self.uncertainty_threshold:.1%}). "
                f"Unable to provide a reliable experimental prediction for this input."
            )
        else:
            predicted_label = top_label
            if predicted_label == "manipulated":
                explanation_wording = FORENSIC_CONFIG.TAMPERING_POSITIVE_LABEL
            else:
                explanation_wording = FORENSIC_CONFIG.TAMPERING_NEGATIVE_LABEL

        # 4. Optional Grad-CAM Generation
        cam_file_str: Optional[str] = None
        if generate_gradcam:
            try:
                # Find final conv layer
                if self.arch == "resnet18":
                    target_layer = self.model.layer4[-1]
                else:
                    target_layer = self.model.features[-1]

                out_cam = gradcam_output_path or (
                    path.parent / f"gradcam_{path.stem}.png"
                )
                generate_explanation_overlay(
                    image_path=path,
                    model=self.model,
                    target_layer=target_layer,
                    output_path=out_cam,
                    device=self.device,
                )
                cam_file_str = str(out_cam)
            except Exception:
                cam_file_str = None

        # 5. Signal-level Error Level Analysis (ELA)
        ela_metrics = {}
        try:
            ela_out = FORENSIC_CONFIG.ARTIFACTS_DIR / f"ela_{path.stem}.jpg"
            ela_metrics = compute_ela(path, output_ela_path=ela_out)
        except Exception:
            ela_metrics = {"error": "ELA computation bypassed"}

        return {
            "status": "completed",
            "predicted_label": predicted_label,
            "probabilities": prob_dict,
            "confidence": round(top_prob, 4),
            "is_uncertain": is_uncertain,
            "explanation_wording": explanation_wording,
            "grad_cam_path": cam_file_str,
            "ela_metrics": ela_metrics,
            "model_architecture": self.arch,
            "model_version": f"{self.arch}_v1.0",
            "saved_test_metrics": self.saved_test_metrics.get("clean_test_metrics", {}),
            "quality_metrics": {
                "blur_score": quality.blur_score,
                "mean_luminance": quality.mean_luminance,
                "resolution": f"{quality.width}x{quality.height}",
            },
            "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
        }

