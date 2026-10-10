"""
CCTV Frame Extraction Module.
Extracts working frames under configurable sampling policies with millisecond timestamp precision.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional, Tuple
import cv2
import numpy as np


@dataclass
class ExtractedFrame:
    """Represents a discrete decoded frame from the derived working copy."""
    frame_index: int
    timestamp_seconds: float
    timestamp_hms: str
    image: np.ndarray
    is_overview_keyframe: bool = False


def format_seconds_to_hms(seconds: float) -> str:
    """Format decimal seconds into HH:MM:SS.mmm representation."""
    total_sec = max(0.0, float(seconds))
    hrs = int(total_sec // 3600)
    mins = int((total_sec % 3600) // 60)
    secs = int(total_sec % 60)
    millis = int(round((total_sec - int(total_sec)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


def extract_cctv_frames(
    video_path: Path | str,
    analysis_mode: str = "fast_review",
    sampling_step: int = 1,
    target_fps: float = 1.0,
    max_frames: Optional[int] = None
) -> Generator[ExtractedFrame, None, Tuple[int, float]]:
    """Stream frames from the working copy according to the configured analysis policy.

    Args:
        video_path: Path to the working copy video file.
        analysis_mode: 'fast_review' (1 frame per second) or 'full_analysis' (frame step).
        sampling_step: Frame increment when analysis_mode is 'full_analysis' (e.g. 1, 2, 5).
        target_fps: Sampling frequency for 'fast_review' mode (default 1.0 = 1 frame/sec).
        max_frames: Optional upper limit for total frames processed (testing/demo safety).

    Yields:
        ExtractedFrame objects containing the decoded BGR image and calculated timestamp.

    Returns:
        Tuple of (total_extracted_frames, video_fps).
    """
    path = Path(video_path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file for extraction: {path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0 or fps != fps:
        fps = 25.0

    # Determine frame step interval
    if analysis_mode == "fast_review":
        step = max(1, int(round(fps / target_fps)))
    else:  # full_analysis
        step = max(1, int(sampling_step))

    # Overview keyframe interval (strictly 1 second)
    overview_interval = max(1, int(round(fps)))

    frame_index = 0
    extracted_count = 0
    last_overview_sec = -1

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Check if this frame should be processed
            if frame_index % step == 0:
                timestamp_sec = round(frame_index / fps, 3)
                timestamp_str = format_seconds_to_hms(timestamp_sec)

                current_sec_int = int(timestamp_sec)
                is_overview = False
                if current_sec_int > last_overview_sec:
                    is_overview = True
                    last_overview_sec = current_sec_int

                yield ExtractedFrame(
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_sec,
                    timestamp_hms=timestamp_str,
                    image=frame,
                    is_overview_keyframe=is_overview
                )

                extracted_count += 1
                if max_frames and extracted_count >= max_frames:
                    break

            frame_index += 1

    finally:
        cap.release()

    return extracted_count, fps
