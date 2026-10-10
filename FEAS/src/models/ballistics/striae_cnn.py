"""
Forensic Evidence Analysis System (FEAS) - Ballistics Striae CNN
Extracts microscopic striation patterns and classifies caliber, rifling direction, and weapon manufacturer only when ballistics textures are present.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from src.config import BALLISTICS_CLASSES, DEVICE, SEED, TEMP_DIR


def detect_striation_texture(img_bgr: np.ndarray) -> bool:
    """
    Check if the image exhibits parallel microscopic striation line textures.
    Computes horizontal vs vertical Sobel gradient variance ratio.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    var_x = float(np.var(sobel_x))
    var_y = float(np.var(sobel_y))
    
    if var_y < 1e-5:
        return False

    ratio = var_x / (var_y + 1e-5)
    total_energy = var_x + var_y

    # Microscopic striation textures have high directional anisotropy (ratio > 1.8 or < 0.55) and sufficient texture energy
    return bool((ratio > 1.65 or ratio < 0.58) and total_energy > 400)


class StriaeTextureCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=(7, 3), padding=(3, 1))
        self.bn1 = nn.BatchNorm2d(32)
        self.relu = nn.LeakyReLU(0.1)
        self.pool1 = nn.MaxPool2d((2, 2))

        self.conv2 = nn.Conv2d(32, 64, kernel_size=(5, 3), padding=(2, 1))
        self.bn2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d((2, 2))

        self.conv3 = nn.Conv2d(64, 128, kernel_size=(3, 3), padding=(1, 1))
        self.bn3 = nn.BatchNorm2d(128)
        self.pool3 = nn.AdaptiveAvgPool2d((4, 4))

        self.fc_shared = nn.Sequential(
            nn.Linear(128 * 4 * 4, 256),
            nn.ReLU(True),
            nn.Dropout(0.3)
        )

        self.head_caliber = nn.Linear(256, len(BALLISTICS_CLASSES["caliber"]))
        self.head_rifling = nn.Linear(256, len(BALLISTICS_CLASSES["rifling"]))
        self.head_manufacturer = nn.Linear(256, len(BALLISTICS_CLASSES["manufacturer"]))

        self._init_weights()

    def _init_weights(self):
        torch.manual_seed(SEED)
        for m in self.modules():
            if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        c1 = self.relu(self.bn1(self.conv1(x)))
        p1 = self.pool1(c1)
        c2 = self.relu(self.bn2(self.conv2(p1)))
        p2 = self.pool2(c2)
        c3 = self.relu(self.bn3(self.conv3(p2)))
        p3 = self.pool3(c3)
        
        flat = torch.flatten(p3, 1)
        feat = self.fc_shared(flat)

        out_cal = self.head_caliber(feat)
        out_rif = self.head_rifling(feat)
        out_mfg = self.head_manufacturer(feat)

        return out_cal, out_rif, out_mfg, c3


class BallisticsStriaeEngine:
    def __init__(self):
        self.device = DEVICE
        self.classes = BALLISTICS_CLASSES
        self.model = StriaeTextureCNN().to(self.device)
        self.model.eval()

    @torch.no_grad()
    def analyze(
        self,
        image_input: Union[str, Path, np.ndarray, Image.Image],
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        out_dir = output_dir or (TEMP_DIR / "ballistics_results")
        out_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(image_input, (str, Path)):
            img_bgr = cv2.imread(str(image_input))
            base_name = Path(image_input).stem
        elif isinstance(image_input, np.ndarray):
            img_bgr = image_input.copy()
            base_name = "bullet_sample"
        elif isinstance(image_input, Image.Image):
            img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
            base_name = "bullet_sample"
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        if img_bgr is None:
            raise ValueError("Failed to load ballistics image.")

        # Check if the image exhibits ballistic striations
        has_striae = detect_striation_texture(img_bgr)
        if not has_striae:
            return {
                "striae_detected": False,
                "caliber": "N/A",
                "caliber_confidence": 0.0,
                "caliber_distribution": {},
                "rifling": "N/A",
                "rifling_confidence": 0.0,
                "rifling_distribution": {},
                "manufacturer": "N/A",
                "manufacturer_confidence": 0.0,
                "manufacturer_distribution": {},
                "striation_map_path": None,
                "message": "No ballistic micro-striations identified in evidence frame."
            }

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        resized_gray = cv2.resize(gray, (256, 256), interpolation=cv2.INTER_AREA)
        norm_gray = resized_gray.astype(np.float32) / 255.0
        tensor = torch.from_numpy(norm_gray).unsqueeze(0).unsqueeze(0).to(self.device)

        logits_cal, logits_rif, logits_mfg, feat_map = self.model(tensor)

        prob_cal = torch.softmax(logits_cal, dim=1).cpu().numpy()[0]
        prob_rif = torch.softmax(logits_rif, dim=1).cpu().numpy()[0]
        prob_mfg = torch.softmax(logits_mfg, dim=1).cpu().numpy()[0]

        cal_idx = int(np.argmax(prob_cal))
        rif_idx = int(np.argmax(prob_rif))
        mfg_idx = int(np.argmax(prob_mfg))

        pred_cal = self.classes["caliber"][cal_idx]
        conf_cal = round(float(prob_cal[cal_idx]), 4)

        pred_rif = self.classes["rifling"][rif_idx]
        conf_rif = round(float(prob_rif[rif_idx]), 4)

        pred_mfg = self.classes["manufacturer"][mfg_idx]
        conf_mfg = round(float(prob_mfg[mfg_idx]), 4)

        act_map = torch.mean(feat_map, dim=1).squeeze(0).cpu().numpy()
        act_norm = cv2.normalize(act_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        act_resized = cv2.resize(act_norm, (img_bgr.shape[1], img_bgr.shape[0]))
        heatmap = cv2.applyColorMap(act_resized, cv2.COLORMAP_VIRIDIS)

        blended = cv2.addWeighted(img_bgr, 0.65, heatmap, 0.35, 0)
        
        hud_h, hud_w = blended.shape[:2]
        cv2.rectangle(blended, (10, hud_h - 70), (hud_w - 10, hud_h - 10), (15, 15, 15), -1)
        cv2.putText(blended, f"CALIBER: {pred_cal} ({conf_cal*100:.1f}%) | RIFLING: {pred_rif} ({conf_rif*100:.1f}%)", (20, hud_h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(blended, f"SIGNATURE: {pred_mfg.upper()} ({conf_mfg*100:.1f}%)", (20, hud_h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        map_path = out_dir / f"{base_name}_striae_map.jpg"
        cv2.imwrite(str(map_path), blended)

        cal_dist = {self.classes["caliber"][i]: round(float(prob_cal[i]), 4) for i in range(len(self.classes["caliber"]))}
        rif_dist = {self.classes["rifling"][i]: round(float(prob_rif[i]), 4) for i in range(len(self.classes["rifling"]))}
        mfg_dist = {self.classes["manufacturer"][i]: round(float(prob_mfg[i]), 4) for i in range(len(self.classes["manufacturer"]))}

        return {
            "striae_detected": True,
            "caliber": pred_cal,
            "caliber_confidence": conf_cal,
            "caliber_distribution": cal_dist,
            "rifling": pred_rif,
            "rifling_confidence": conf_rif,
            "rifling_distribution": rif_dist,
            "manufacturer": pred_mfg,
            "manufacturer_confidence": conf_mfg,
            "manufacturer_distribution": mfg_dist,
            "striation_map_path": str(map_path),
            "message": "Striation pattern classified."
        }


# Global instance
_ballistics_engine = None


def get_ballistics_engine() -> BallisticsStriaeEngine:
    global _ballistics_engine
    if _ballistics_engine is None:
        _ballistics_engine = BallisticsStriaeEngine()
    return _ballistics_engine


def analyze_striae(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    engine = get_ballistics_engine()
    return engine.analyze(image_input, output_dir=output_dir)
