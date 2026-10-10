"""
CCTV Video Validation Module.
Validates file extensions, size limits, and stream integrity without raising unhandled crashes.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Set
import cv2

SUPPORTED_EXTENSIONS: Set[str] = {".mp4", ".avi", ".mkv", ".mov"}
DEFAULT_MAX_SIZE_MB: int = 500


@dataclass
class ValidationResult:
    """Outcome of CCTV file validation."""
    is_valid: bool
    error_message: str | None = None
    file_size_bytes: int = 0
    extension: str = ""


def validate_cctv_video(
    file_path: Path | str,
    max_size_mb: int = DEFAULT_MAX_SIZE_MB
) -> ValidationResult:
    """Validate a CCTV video file before any analytical processing.

    Args:
        file_path: Absolute or relative path to the candidate video.
        max_size_mb: Maximum permitted file size in Megabytes.

    Returns:
        ValidationResult object indicating pass/fail status and message.
    """
    path = Path(file_path)

    # 1. Check existence
    if not path.is_file():
        return ValidationResult(
            is_valid=False,
            error_message=f"File not found: {path.name}"
        )

    # 2. Check extension
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Unsupported video format '{ext}'. "
                f"Supported formats are: {allowed}"
            ),
            extension=ext
        )

    # 3. Check file size
    try:
        file_size = path.stat().st_size
    except OSError as e:
        return ValidationResult(
            is_valid=False,
            error_message=f"Unable to read file metadata: {e}",
            extension=ext
        )

    if file_size == 0:
        return ValidationResult(
            is_valid=False,
            error_message="Uploaded video file is empty (0 bytes).",
            file_size_bytes=0,
            extension=ext
        )

    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        size_mb = file_size / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit "
                f"of {max_size_mb} MB."
            ),
            file_size_bytes=file_size,
            extension=ext
        )

    # 4. Stream integrity check using OpenCV
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return ValidationResult(
            is_valid=False,
            error_message=(
                "OpenCV could not open this video stream. The container may be corrupted "
                "or encoded with an unsupported codec."
            ),
            file_size_bytes=file_size,
            extension=ext
        )

    try:
        success, frame = cap.read()
        if not success or frame is None or frame.size == 0:
            return ValidationResult(
                is_valid=False,
                error_message="Video stream opened but no readable video frames were decoded.",
                file_size_bytes=file_size,
                extension=ext
            )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            error_message=f"Exception encountered while reading video stream: {e}",
            file_size_bytes=file_size,
            extension=ext
        )
    finally:
        cap.release()

    return ValidationResult(
        is_valid=True,
        error_message=None,
        file_size_bytes=file_size,
        extension=ext
    )
