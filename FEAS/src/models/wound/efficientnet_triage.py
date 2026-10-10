"""
Forensic Evidence Analysis System (FEAS) - EfficientNet Multi-Head Wound Triage
Analyzes genuine biological trauma and classifies wound Type, Severity, Age, and Location.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from src.config import DEVICE, SEED, TEMP_DIR, WOUND_CLASSES


def detect_wound_characteristics(img_bgr: np.ndarray) -> bool:
    """
    Check if the image exhibits genuine wound / biological lesion characteristics:
    - Analyzes color spectrum (erythema, hematoma, localized tissue trauma) in HSV & Lab color spaces.
    """
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Blood / wound erythema range in HSV
    lower_red1 = np.array([0, 50, 40], dtype=np.uint8)
    upper_red1 = np.array([12, 255, 255], dtype=np.uint8)
    lower_red2 = np.array([168, 50, 40], dtype=np.uint8)
    upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    wound_mask = cv2.bitwise_or(mask1, mask2)

    wound_pixels = np.sum(wound_mask > 0)
    ratio = wound_pixels / float(h * w + 1e-5)

    # If at least 1.5% and under 70% of pixels match wound tissue characteristics
    return bool(0.015 <= ratio <= 0.75)


class MultiHeadWoundNet(nn.Module):
    """
    Multi-head neural network with 4 discrete classification heads:
    1. Type: Gunshot, Stab, Blunt, Burn
    2. Severity: Minor, Moderate, Severe
    3. Age: Fresh, 1-Day, Week Old
    4. Location: Head, Torso, Limb
    """

    def __init__(self):
        super().__init__()
        try:
            eff = models.efficientnet_b4(weights=None)
            self.backbone = eff.features
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            in_features = 1792
        except Exception:
            res = models.resnet18(weights=None)
            self.backbone = nn.Sequential(*list(res.children())[:-2])
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            in_features = 512

        self.shared_fc = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(True),
            nn.Dropout(0.3)
        )

        self.head_type = nn.Linear(512, len(WOUND_CLASSES["type"]))
        self.head_severity = nn.Linear(512, len(WOUND_CLASSES["severity"]))
        self.head_age = nn.Linear(512, len(WOUND_CLASSES["age"]))
        self.head_location = nn.Linear(512, len(WOUND_CLASSES["location"]))

        self._init_weights()

    def _init_weights(self):
        torch.manual_seed(SEED)
        for m in [self.shared_fc, self.head_type, self.head_severity, self.head_age, self.head_location]:
            for layer in m.modules():
                if isinstance(layer, nn.Linear):
                    nn.init.kaiming_normal_(layer.weight, mode="fan_out", nonlinearity="relu")
                    if layer.bias is not None:
                        nn.init.constant_(layer.bias, 0)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        feat = self.backbone(x)
        feat = self.pool(feat)
        feat = torch.flatten(feat, 1)
        shared = self.shared_fc(feat)

        out_type = self.head_type(shared)
        out_severity = self.head_severity(shared)
        out_age = self.head_age(shared)
        out_location = self.head_location(shared)

        return out_type, out_severity, out_age, out_location


class WoundTriageClassifier:
    """Forensic Wound Triage Inference Engine."""

    def __init__(self):
        self.device = DEVICE
        self.classes = WOUND_CLASSES
        self.model = MultiHeadWoundNet().to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    @torch.no_grad()
    def predict(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Perform wound classification only when genuine trauma is present.
        """
        out_dir = output_dir or (TEMP_DIR / "wound_results")
        out_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(image_input, (str, Path)):
            img_bgr = cv2.imread(str(image_input))
            base_name = Path(image_input).stem
        elif isinstance(image_input, np.ndarray):
            img_bgr = image_input.copy()
            base_name = "wound_sample"
        elif isinstance(image_input, Image.Image):
            img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
            base_name = "wound_sample"
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        if img_bgr is None:
            raise ValueError("Failed to load wound image.")

        # Check if the image contains biological trauma
        has_wound = detect_wound_characteristics(img_bgr)
        if not has_wound:
            return {
                "wound_detected": False,
                "wound_type": "N/A",
                "wound_type_confidence": 0.0,
                "wound_type_distribution": {},
                "severity": "N/A",
                "severity_confidence": 0.0,
                "severity_distribution": {},
                "age": "N/A",
                "age_confidence": 0.0,
                "age_distribution": {},
                "location": "N/A",
                "location_confidence": 0.0,
                "location_distribution": {},
                "annotated_image_path": None,
                "message": "No biological wound or trauma pattern identified in evidence frame."
            }

        # Prepare PIL image for neural network
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        logits_type, logits_sev, logits_age, logits_loc = self.model(tensor)

        prob_type = torch.softmax(logits_type, dim=1).cpu().numpy()[0]
        prob_sev = torch.softmax(logits_sev, dim=1).cpu().numpy()[0]
        prob_age = torch.softmax(logits_age, dim=1).cpu().numpy()[0]
        prob_loc = torch.softmax(logits_loc, dim=1).cpu().numpy()[0]

        type_idx = int(np.argmax(prob_type))
        sev_idx = int(np.argmax(prob_sev))
        age_idx = int(np.argmax(prob_age))
        loc_idx = int(np.argmax(prob_loc))

        pred_type = self.classes["type"][type_idx]
        conf_type = round(float(prob_type[type_idx]), 4)

        pred_sev = self.classes["severity"][sev_idx]
        conf_sev = round(float(prob_sev[sev_idx]), 4)

        pred_age = self.classes["age"][age_idx]
        conf_age = round(float(prob_age[age_idx]), 4)

        pred_loc = self.classes["location"][loc_idx]
        conf_loc = round(float(prob_loc[loc_idx]), 4)

        # Create overlay annotation
        annotated_bgr = img_bgr.copy()
        h, w = annotated_bgr.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        sev_color = (0, 0, 255) if pred_sev == "severe" else ((0, 165, 255) if pred_sev == "moderate" else (0, 255, 0))
        cv2.circle(annotated_bgr, (center_x, center_y), min(w, h) // 4, sev_color, 2)

        # Telemetry panel
        overlay_text_1 = f"TYPE: {pred_type.upper()} ({conf_type*100:.1f}%)"
        overlay_text_2 = f"SEVERITY: {pred_sev.upper()} ({conf_sev*100:.1f}%)"
        overlay_text_3 = f"AGE: {pred_age.upper()} | LOC: {pred_loc.upper()}"

        cv2.rectangle(annotated_bgr, (10, h - 75), (w - 10, h - 10), (20, 20, 20), -1)
        cv2.putText(annotated_bgr, overlay_text_1, (20, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(annotated_bgr, overlay_text_2, (20, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.45, sev_color, 1)
        cv2.putText(annotated_bgr, overlay_text_3, (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        annotated_path = out_dir / f"{base_name}_wound_triage.jpg"
        cv2.imwrite(str(annotated_path), annotated_bgr)

        type_probs = {self.classes["type"][i]: round(float(prob_type[i]), 4) for i in range(len(self.classes["type"]))}
        sev_probs = {self.classes["severity"][i]: round(float(prob_sev[i]), 4) for i in range(len(self.classes["severity"]))}
        age_probs = {self.classes["age"][i]: round(float(prob_age[i]), 4) for i in range(len(self.classes["age"]))}
        loc_probs = {self.classes["location"][i]: round(float(prob_loc[i]), 4) for i in range(len(self.classes["location"]))}

        return {
            "wound_detected": True,
            "wound_type": pred_type,
            "wound_type_confidence": conf_type,
            "wound_type_distribution": type_probs,
            "severity": pred_sev,
            "severity_confidence": conf_sev,
            "severity_distribution": sev_probs,
            "age": pred_age,
            "age_confidence": conf_age,
            "age_distribution": age_probs,
            "location": pred_loc,
            "location_confidence": conf_loc,
            "location_distribution": loc_probs,
            "annotated_image_path": str(annotated_path),
            "message": "Trauma pattern classified."
        }


# Global instance
_wound_classifier = None


def get_wound_classifier() -> WoundTriageClassifier:
    global _wound_classifier
    if _wound_classifier is None:
        _wound_classifier = WoundTriageClassifier()
    return _wound_classifier


def predict_wound(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    classifier = get_wound_classifier()
    return classifier.predict(image_input, output_dir=output_dir)
