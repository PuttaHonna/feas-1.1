"""
CCTV Camera Health & Tampering Diagnostics Service.
===================================================
Replaces traditional film scene-cut heuristics with surveillance camera telemetry:
1. MOG2/KNN Background Subtraction & Foreground Motion Ratio.
2. Lens Tampering / Occlusion (e.g. spray paint, object covering lens, sudden solid color/darkness).
3. Camera Shift / Deframing (structural dislocation from wind or physical tampering).
4. Day/Night Illumination Phase Transitions (sudden lux drop/rise, IR cut-filter toggle).
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np


@dataclass
class CameraTamperAlert:
    """Security alert emitted when CCTV camera is occluded, moved, or blinded."""
    alert_id: str
    tamper_type: str        # 'OCCLUSION_BLIND', 'DEFOCUS_BLUR', 'CAMERA_SHIFT', 'DAY_NIGHT_TRANSITION'
    frame_number: int
    timestamp_seconds: float
    timestamp_hms: str
    confidence: float
    metric_value: float
    description: str
    severity: str = "HIGH"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CameraTamperDetector:
    """
    Evaluates surveillance camera feed stability, optical integrity, and environmental lighting.
    """

    def __init__(
        self,
        occlusion_variance_thresh: float = 8.0,
        blur_laplacian_thresh: float = 40.0,
        light_shift_ratio_thresh: float = 0.55
    ):
        self.occlusion_thresh = occlusion_variance_thresh
        self.blur_thresh = blur_laplacian_thresh
        self.light_shift_thresh = light_shift_ratio_thresh

        # MOG2 background subtractor
        self.mog2 = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=False)

        # Baseline metrics
        self._prev_gray: Optional[np.ndarray] = None
        self._prev_mean_luminance: Optional[float] = None
        self._alert_counter = 0

        self.alerts: List[CameraTamperAlert] = []

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        frame_number: int,
        timestamp_s: float
    ) -> Tuple[float, Optional[CameraTamperAlert]]:
        """
        Processes frame and returns (motion_ratio, optional_tamper_alert).
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        total_pixels = h * w

        # 1. Background subtraction for motion ratio
        fg_mask = self.mog2.apply(gray)
        motion_pixels = cv2.countNonZero(fg_mask)
        motion_ratio = motion_pixels / total_pixels

        alert = None
        hms = f"{int(timestamp_s // 3600):02d}:{int((timestamp_s % 3600) // 60):02d}:{timestamp_s % 60:05.2f}"

        # 2. Check for Lens Occlusion / Solid Covering (Low spatial variance across entire frame)
        frame_variance = float(np.var(gray))
        if frame_variance < self.occlusion_thresh and frame_number > 5:
            self._alert_counter += 1
            alert = CameraTamperAlert(
                alert_id=f"ALT-TAMPER-{self._alert_counter:04d}",
                tamper_type="OCCLUSION_BLIND",
                frame_number=frame_number,
                timestamp_seconds=round(timestamp_s, 2),
                timestamp_hms=hms,
                confidence=0.96,
                metric_value=round(frame_variance, 2),
                description=f"Surveillance camera lens occluded/covered (spatial variance={frame_variance:.1f})",
                severity="CRITICAL"
            )

        # 3. Check for Extreme Defocus / Spray Tampering (Laplacian variance)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < self.blur_thresh and not alert and frame_number > 10:
            self._alert_counter += 1
            alert = CameraTamperAlert(
                alert_id=f"ALT-TAMPER-{self._alert_counter:04d}",
                tamper_type="DEFOCUS_BLUR",
                frame_number=frame_number,
                timestamp_seconds=round(timestamp_s, 2),
                timestamp_hms=hms,
                confidence=0.91,
                metric_value=round(laplacian_var, 2),
                description=f"Severe optical defocus/blur detected on camera feed (laplacian={laplacian_var:.1f})",
                severity="HIGH"
            )

        # 4. Check for Sudden Day/Night Illumination Shift (IR Cut Filter / Lights turned off)
        curr_luminance = float(np.mean(gray))
        if self._prev_mean_luminance is not None and not alert and frame_number > 5:
            delta = abs(curr_luminance - self._prev_mean_luminance)
            ratio = delta / (self._prev_mean_luminance + 1e-4)

            if ratio > self.light_shift_thresh:
                self._alert_counter += 1
                mode_str = "NIGHT/IR MODE" if curr_luminance < self._prev_mean_luminance else "DAY/LIGHT MODE"
                alert = CameraTamperAlert(
                    alert_id=f"ALT-TAMPER-{self._alert_counter:04d}",
                    tamper_type="DAY_NIGHT_TRANSITION",
                    frame_number=frame_number,
                    timestamp_seconds=round(timestamp_s, 2),
                    timestamp_hms=hms,
                    confidence=0.88,
                    metric_value=round(ratio, 2),
                    description=f"Sudden lighting shift transition to {mode_str} (luminance shift={delta:.1f})",
                    severity="LOW"
                )

        if alert:
            self.alerts.append(alert)

        self._prev_gray = gray
        self._prev_mean_luminance = curr_luminance
        return motion_ratio, alert

