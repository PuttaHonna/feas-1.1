"""
Forensic Evidence Analysis System (FEAS) - Deep Learning Forgery Classifier
Loads real trained ResNet-18 model weights (trained on CASIA 2.0 Forensic Benchmark)
with fallback to deterministic VGG16 architecture.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from src.config import DEVICE, SEED, BASE_DIR


def get_checkpoint_path() -> Optional[Path]:
    """Find trained tampering checkpoint in FEAS or root models directory."""
    candidates = [
        BASE_DIR / "models" / "tampering_resnet18_best.pt",
        BASE_DIR.parent / "models" / "tampering_resnet18_best.pt",
        Path("models/tampering_resnet18_best.pt"),
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    return None


class ResNet18TamperNet(nn.Module):
    """ResNet-18 classifier matching trained CASIA 2.0 architecture."""

    def __init__(self, num_classes: int = 2):
        super().__init__()
        resnet = models.resnet18(weights=None)
        in_features = resnet.fc.in_features
        resnet.fc = nn.Linear(in_features, num_classes)
        self.model = resnet

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


class VGG16ForgeryNet(nn.Module):
    """VGG16-based binary classifier fallback for image tampering detection."""

    def __init__(self):
        super().__init__()
        vgg = models.vgg16(weights=None)
        self.features = vgg.features
        self.avgpool = nn.AdaptiveAvgPool2d((7, 7))
        self.classifier = nn.Sequential(
            nn.Linear(512 * 7 * 7, 512),
            nn.ReLU(True),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(True),
            nn.Linear(128, 2),
        )
        self._init_weights()

    def _init_weights(self):
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
    """Production Forgery Detection Inference Engine supporting trained ResNet-18 & VGG16."""

    def __init__(self):
        self.device = DEVICE
        self.ckpt_path = get_checkpoint_path()
        self.model_loaded = False
        self.arch_name = "VGG16"

        if self.ckpt_path:
            try:
                ckpt = torch.load(self.ckpt_path, map_location=self.device, weights_only=False)
                self.model = ResNet18TamperNet(num_classes=2)
                self.model.model.load_state_dict(ckpt["model_state_dict"])
                self.model.to(self.device)
                self.model.eval()
                self.model_loaded = True
                self.arch_name = "ResNet-18 (CASIA 2.0 Benchmark)"
            except Exception as e:
                print(f"[!] Warning: Failed loading ResNet-18 checkpoint ({e}), using VGG16 fallback.")
                self.model = VGG16ForgeryNet().to(self.device)
                self.model.eval()
        else:
            self.model = VGG16ForgeryNet().to(self.device)
            self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    @torch.no_grad()
    def predict(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> float:
        """Predict probability that the image is tampered (0.0 to 1.0)."""
        result = self.predict_detailed(image_input)
        return result["tamper_prob"]

    @torch.no_grad()
    def predict_detailed(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> Dict[str, Any]:
        """Predict detailed probabilities, confidence, and model architecture metadata."""
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
        probs = torch.softmax(logits, dim=1).squeeze(0).cpu().tolist()

        auth_prob = round(probs[0], 4)
        tamper_prob = round(probs[1], 4)
        top_prob = max(auth_prob, tamper_prob)
        predicted_class = "tampered" if tamper_prob >= 0.50 else "authentic"

        return {
            "tamper_prob": tamper_prob,
            "authentic_prob": auth_prob,
            "confidence": round(top_prob, 4),
            "predicted_class": predicted_class,
            "is_trained_model": self.model_loaded,
            "model_architecture": self.arch_name,
            "checkpoint_source": str(self.ckpt_path) if self.ckpt_path else "None (Initialized)",
        }

    def generate_gradcam(
        self, image_input: Union[str, Path, np.ndarray, Image.Image]
    ) -> np.ndarray:
        """
        Generate Class Activation Map (Grad-CAM) highlighting spatial tampering regions.
        Hooks into the final convolutional feature extractor layer.
        Returns a normalized (0.0 to 1.0) float32 2D numpy array with dimensions (H, W) matching input image.
        """
        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input)).convert("RGB")
            orig_w, orig_h = img.size
        elif isinstance(image_input, np.ndarray):
            orig_h, orig_w = image_input.shape[:2]
            rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) if len(image_input.shape) == 3 else image_input
            img = Image.fromarray(rgb)
        elif isinstance(image_input, Image.Image):
            orig_w, orig_h = image_input.size
            img = image_input.convert("RGB")
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        tensor = self.transform(img).unsqueeze(0).to(self.device)
        tensor.requires_grad = True

        activations = []
        gradients = []

        # Target layer: layer4 for ResNet18, features[-1] for VGG16
        if hasattr(self.model, "model") and hasattr(self.model.model, "layer4"):
            target_layer = self.model.model.layer4
        elif hasattr(self.model, "features"):
            target_layer = self.model.features[-1]
        else:
            return np.zeros((orig_h, orig_w), dtype=np.float32)

        h_f = target_layer.register_forward_hook(lambda m, i, o: activations.append(o))
        h_b = target_layer.register_full_backward_hook(lambda m, gi, go: gradients.append(go[0]))

        try:
            logits = self.model(tensor)
            # Focus on class index 1 (manipulated/tampered)
            score = logits[0, 1] if logits.shape[1] > 1 else logits[0, 0]
            self.model.zero_grad()
            score.backward(retain_graph=False)

            if not activations or not gradients:
                return np.zeros((orig_h, orig_w), dtype=np.float32)

            act = activations[0]
            grad = gradients[0]
            weights = grad.mean(dim=(2, 3), keepdim=True)
            cam = torch.relu((weights * act).sum(dim=1, keepdim=True))

            if cam.max() == 0:
                cam = act.abs().mean(dim=1, keepdim=True)

            cam = torch.nn.functional.interpolate(
                cam, size=(orig_h, orig_w), mode="bilinear", align_corners=False
            )
            cam_np = cam.squeeze().detach().cpu().numpy()
            c_min = float(cam_np.min())
            c_max = float(cam_np.max())
            if c_max > c_min:
                cam_np = (cam_np - c_min) / (c_max - c_min)
            else:
                cam_np = np.zeros((orig_h, orig_w), dtype=np.float32)

            return cam_np.astype(np.float32)
        except Exception:
            return np.zeros((orig_h, orig_w), dtype=np.float32)
        finally:
            try:
                h_f.remove()
                h_b.remove()
            except Exception:
                pass


# Global singleton instance
_vgg_detector = None


def get_vgg_detector() -> ForgeryVGG16Detector:
    global _vgg_detector
    if _vgg_detector is None:
        _vgg_detector = ForgeryVGG16Detector()
    return _vgg_detector
