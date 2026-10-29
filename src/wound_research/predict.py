"""
Wound Research Prediction Pipeline with Strict Educational & Forensic Guardrails
Rejects non-research inputs by policy.
Applies quality gating and uncertainty rejection below confidence threshold.
Labels outputs strictly with mandatory research disclaimer.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from src.common.config import FORENSIC_CONFIG
from src.common.quality_gate import evaluate_image_quality
from src.common.utils import get_optimal_device
from src.wound_research.dataset import (
    ALLOWED_WOUND_CLASSES,
    IDX_TO_CLASS,
    verify_research_provenance,
)
from src.wound_research.train import get_wound_backbone


class WoundResearchPredictor:
    """
    Research-only visual category predictor.
    Never infers gunshot, stab, wound age, severity, or cause of injury.
    """

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        uncertainty_threshold: float = 0.60,
        enforce_research_consent: bool = True,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device) if device else get_optimal_device()
        if checkpoint_path is None:
            checkpoint_path = FORENSIC_CONFIG.MODELS_DIR / "wound_resnet18_best.pt"
        self.checkpoint_path = Path(checkpoint_path)
        self.uncertainty_threshold = uncertainty_threshold
        self.enforce_research_consent = enforce_research_consent


        ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.arch = ckpt.get("arch", "resnet18")
        self.model = get_wound_backbone(arch=self.arch, num_classes=len(ALLOWED_WOUND_CLASSES), pretrained=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def predict(
        self,
        image_path: Path,
        research_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Runs research provenance gate, image quality gate, and visual category inference.
        """
        path = Path(image_path)

        # 1. Research Provenance Gate
        if self.enforce_research_consent:
            is_valid_research, reason = verify_research_provenance(research_metadata or {})
            if not is_valid_research:
                return {
                    "status": "rejected_by_policy",
                    "predicted_category": "rejected / unconsented",
                    "probabilities": {},
                    "confidence": 0.0,
                    "rejection_reason": reason,
                    "disclaimer": FORENSIC_CONFIG.WOUND_OUTPUT_WORDING,
                }

        # 2. Quality Gate
        quality = evaluate_image_quality(path)
        if not quality.passed:
            return {
                "status": "failed_quality_gate",
                "predicted_category": "unknown / uncertain",
                "probabilities": {},
                "confidence": 0.0,
                "rejection_reason": quality.summary_message,
                "quality_issues": quality.reasons,
                "disclaimer": FORENSIC_CONFIG.WOUND_OUTPUT_WORDING,
            }

        # 3. Model Inference
        with Image.open(path) as img:
            rgb = img.convert("RGB")

        tensor = self.transform(rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().tolist()

        prob_dict = {
            IDX_TO_CLASS[i]: round(probs[i], 4) for i in range(len(probs))
        }

        top_idx = int(torch.argmax(logits, dim=1).item())
        top_prob = probs[top_idx]
        top_class = IDX_TO_CLASS[top_idx]

        # 4. Uncertainty Check
        is_uncertain = top_prob < self.uncertainty_threshold
        if is_uncertain:
            predicted_category = "unknown / uncertain"
            advisory_text = (
                f"Model confidence ({top_prob:.1%}) is below reliability threshold ({self.uncertainty_threshold:.1%}). "
                f"Visual category cannot be determined reliably."
            )
        else:
            predicted_category = top_class
            advisory_text = (
                f"Experimental visual category classified as '{predicted_category}' based on training distribution patterns."
            )

        return {
            "status": "completed",
            "predicted_category": predicted_category,
            "probabilities": prob_dict,
            "confidence": round(top_prob, 4),
            "is_uncertain": is_uncertain,
            "advisory_text": advisory_text,
            "model_version": f"{self.arch}_wound_research_v1.0",
            "safety_constraints_enforced": [
                "Zero gunshot determination",
                "Zero stab determination",
                "Zero wound age estimation",
                "Zero severity estimation",
                "Zero body-location inference",
                "Zero treatment recommendation",
                "Zero forensic or legal conclusion",
            ],
            "disclaimer": FORENSIC_CONFIG.WOUND_OUTPUT_WORDING,
        }
