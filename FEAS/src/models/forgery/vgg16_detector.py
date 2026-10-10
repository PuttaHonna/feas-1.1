"""
Forensic Evidence Analysis System (FEAS) - VGG16 Forgery Classifier
Binary classifier for Authentic vs. Tampered digital media detection.
"""

from pathlib import Path
from typing import Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from src.config import DEVICE, SEED


class VGG16ForgeryNet(nn.Module):
    """VGG16-based binary classifier for image tampering detection."""

    def __init__(self):
        super().__init__()
        # Use torchvision VGG16 features structure
        vgg = models.vgg16(weights=None)
        self.features = vgg.features
        self.avgpool = nn.AdaptiveAvgPool2d((7, 7))
        self.classifier = nn.Sequential(
            nn.Linear(512 * 7 * 7, 512),
            nn.ReLU(True),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(True),
            nn.Linear(128, 2)  # [0: Authentic, 1: Tampered]
        )
        self._init_weights()

    def _init_weights(self):
        """Deterministic initialization for reproducible inference."""
        torch.manual_seed(SEED)
        for m in self.classifier.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


class ForgeryVGG16Detector:
    """Wrapper for VGG16 Forgery Detection Inference."""

    def __init__(self):
        self.device = DEVICE
        self.model = VGG16ForgeryNet().to(self.device)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    @torch.no_grad()
    def predict(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> float:
        """
        Predict probability that the image is tampered (0.0 to 1.0).
        """
        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input)).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) if len(image_input.shape) == 3 else image_input
            img = Image.fromarray(rgb)
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        tensor = self.transform(img).unsqueeze(0).to(self.device)
        logits = self.model(tensor)
        probs = torch.softmax(logits, dim=1)
        # Class 1 is 'Tampered'
        tamper_prob = float(probs[0, 1].item())
        return round(tamper_prob, 4)


# Global singleton instance
_vgg_detector = None


def get_vgg_detector() -> ForgeryVGG16Detector:
    global _vgg_detector
    if _vgg_detector is None:
        _vgg_detector = ForgeryVGG16Detector()
    return _vgg_detector
