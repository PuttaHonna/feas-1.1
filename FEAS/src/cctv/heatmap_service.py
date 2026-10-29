"""
CCTV Crowd Density & Motion Heatmap Service.
============================================
Aggregates spatial (x, y) centroids of tracks across temporal windows, applies Gaussian accumulation,
and renders calibrated thermal 2D heatmaps (COLORMAP_JET / INFERNO) overlaid on surveillance backgrounds.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np


@dataclass
class HeatmapSummary:
    """Statistical summary of the generated surveillance density map."""
    total_samples: int
    peak_density_value: float
    peak_location_xy: Tuple[int, int]
    coverage_ratio: float
    output_image_path: str
    output_url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CCTVHeatmapGenerator:
    """
    Accumulates spatial presence points and creates high-fidelity heatmap overlays.
    """

    def __init__(self, frame_width: int = 1280, frame_height: int = 720, decay_rate: float = 1.0):
        self.width = frame_width
        self.height = frame_height
        self.decay = decay_rate
        # Float32 accumulation buffer
        self.density_grid = np.zeros((self.height, self.width), dtype=np.float32)
        self.total_points = 0

    def add_point(self, x: float, y: float, weight: float = 1.0, radius: int = 25) -> None:
        """Add a single centroid detection point with Gaussian dispersion."""
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.width and 0 <= iy < self.height:
            # Add spatial kernel at (ix, iy)
            x_min = max(0, ix - radius)
            x_max = min(self.width, ix + radius + 1)
            y_min = max(0, iy - radius)
            y_max = min(self.height, iy + radius + 1)

            # 2D Gaussian kernel on subgrid
            y_coords, x_coords = np.ogrid[y_min - iy : y_max - iy, x_min - ix : x_max - ix]
            dist_sq = x_coords**2 + y_coords**2
            sigma = radius / 2.5
            kernel = np.exp(-dist_sq / (2 * sigma**2)) * weight

            self.density_grid[y_min:y_max, x_min:x_max] += kernel
            self.total_points += 1

    def add_batch(self, points: List[Tuple[float, float]], weights: Optional[List[float]] = None) -> None:
        """Add a list of centroid (x, y) tuples."""
        w_list = weights if weights else [1.0] * len(points)
        for (x, y), w in zip(points, w_list):
            self.add_point(x, y, weight=w)

    def generate_heatmap_overlay(
        self,
        background_frame: Optional[np.ndarray] = None,
        alpha: float = 0.60,
        colormap: int = cv2.COLORMAP_JET
    ) -> np.ndarray:
        """
        Produce a color-mapped visualization overlaid onto the background video frame.
        """
        if self.density_grid.max() > 0:
            norm_grid = (self.density_grid / self.density_grid.max() * 255.0).astype(np.uint8)
        else:
            norm_grid = np.zeros((self.height, self.width), dtype=np.uint8)

        # Apply smooth Gaussian blur
        blurred = cv2.GaussianBlur(norm_grid, (31, 31), 0)
        color_heatmap = cv2.applyColorMap(blurred, colormap)

        # Mask out very low intensity regions (zero activity background)
        mask = blurred > 12
        mask_3c = np.stack([mask] * 3, axis=-1)

        if background_frame is not None:
            if background_frame.shape[:2] != (self.height, self.width):
                bg = cv2.resize(background_frame, (self.width, self.height))
            else:
                bg = background_frame.copy()
            
            blended = bg.copy()
            blended[mask] = cv2.addWeighted(bg, 1.0 - alpha, color_heatmap, alpha, 0)[mask]
            return blended
        else:
            # Standalone heatmap canvas on dark background
            dark_bg = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            dark_bg[mask] = color_heatmap[mask]
            return dark_bg

    def save_heatmap(
        self,
        output_path: Path | str,
        background_frame: Optional[np.ndarray] = None,
        alpha: float = 0.60
    ) -> HeatmapSummary:
        """Export generated density heatmap to disk and return summary metadata."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        vis = self.generate_heatmap_overlay(background_frame=background_frame, alpha=alpha)
        cv2.imwrite(str(out_p), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        max_val = float(self.density_grid.max()) if self.density_grid.size > 0 else 0.0
        peak_idx = np.unravel_index(np.argmax(self.density_grid), self.density_grid.shape) if max_val > 0 else (0, 0)
        coverage = float(np.count_nonzero(self.density_grid > 0.05 * max_val) / (self.width * self.height)) if max_val > 0 else 0.0

        return HeatmapSummary(
            total_samples=self.total_points,
            peak_density_value=round(max_val, 2),
            peak_location_xy=(int(peak_idx[1]), int(peak_idx[0])),
            coverage_ratio=round(coverage, 4),
            output_image_path=str(out_p),
            output_url=f"/results/cctv/heatmaps/{out_p.name}"
        )

