"""
Grad-CAM Explanatory Visualizations for Image Tampering Detection
Generates class activation heatmaps strictly labeled as non-evidentiary explanations.
"""

from pathlib import Path
from typing import Optional, Tuple
import torch
import torch.nn as nn
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms


class GradCAM:
    """
    Computes Gradient-weighted Class Activation Mapping for CNN architectures.
    Advisory explanation only — not a forensic proof of forgery.
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None

        self._hook_handles = [
            self.target_layer.register_forward_hook(self._forward_hook),
            self.target_layer.register_full_backward_hook(self._backward_hook),
        ]

    def _forward_hook(self, module, input, output):
        self.activations = output.detach()

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_cam(self, input_tensor: torch.Tensor, class_idx: Optional[int] = None) -> np.ndarray:
        """
        Generates 2D normalized Grad-CAM heatmap array (values in [0.0, 1.0]).
        """
        self.model.zero_grad()
        output = self.model(input_tensor)

        if class_idx is None:
            class_idx = int(torch.argmax(output, dim=1).item())

        score = output[0, class_idx]
        score.backward()

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Failed to capture activations or gradients for Grad-CAM.")

        # Global average pooling of gradients
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        cam = torch.sum(weights * self.activations, dim=1).squeeze(0)
        cam = torch.clamp(cam, min=0).cpu().numpy()

        if np.max(cam) > 0:
            cam = (cam - np.min(cam)) / (np.max(cam) - np.min(cam))
        else:
            cam = np.zeros_like(cam)

        return cam

    def remove_hooks(self):
        for handle in self._hook_handles:
            handle.remove()


def generate_explanation_overlay(
    image_path: Path,
    model: nn.Module,
    target_layer: nn.Module,
    output_path: Path,
    device: torch.device,
) -> Path:
    """
    Renders Grad-CAM heatmap overlaid on original image with a mandatory explanatory banner.
    """
    grad_cam = GradCAM(model, target_layer)

    with Image.open(image_path) as img:
        orig_rgb = img.convert("RGB")

    orig_w, orig_h = orig_rgb.size

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    tensor = transform(orig_rgb).unsqueeze(0).to(device)
    cam = grad_cam.generate_cam(tensor)
    grad_cam.remove_hooks()

    # Resize CAM to original dimensions
    cam_resized = cv2.resize(cam, (orig_w, orig_h))
    heatmap = (cam_resized * 255).astype(np.uint8)
    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    orig_np = np.array(orig_rgb)
    overlay = (0.55 * orig_np + 0.45 * heatmap_colored).astype(np.uint8)

    # Add explanatory footer banner
    banner_height = 40
    banner = np.zeros((banner_height, orig_w, 3), dtype=np.uint8)
    # Dark gray background
    banner[:] = (40, 40, 40)

    disclaimer_text = "Advisory Grad-CAM: Visualizes model attention regions. Not forensic proof of forgery location."
    font_scale = max(0.35, min(0.6, orig_w / 900))
    cv2.putText(
        banner,
        disclaimer_text,
        (10, int(banner_height * 0.65)),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )

    combined = np.vstack([overlay, banner])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(combined).save(output_path)

    return output_path
