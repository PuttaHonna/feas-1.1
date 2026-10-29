"""
Forensic File Validation Utilities
Performs strict validation of file existence, extension, magic bytes, size limits,
and decodability for images and CCTV video files.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from PIL import Image
import cv2

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256


class ValidationResult(BaseModel):
    is_valid: bool
    file_type: str = "unknown"  # 'image', 'video', or 'unknown'
    file_size_bytes: int = 0
    sha256: str = ""
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Magic byte signatures for supported forensic formats
MAGIC_SIGNATURES = {
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "tiff": [b"II*\x00", b"MM\x00*"],
    "mkv": [b"\x1aE\xdf\xa3"],
    "avi": [b"RIFF"],
}


def _check_magic_bytes(header: bytes, ext: str) -> bool:
    """Validate header bytes against expected format signature."""
    ext_lower = ext.lower().lstrip(".")
    if ext_lower in ("jpg", "jpeg"):
        return any(header.startswith(sig) for sig in MAGIC_SIGNATURES["jpeg"])
    elif ext_lower == "png":
        return any(header.startswith(sig) for sig in MAGIC_SIGNATURES["png"])
    elif ext_lower in ("tif", "tiff"):
        return any(header.startswith(sig) for sig in MAGIC_SIGNATURES["tiff"])
    elif ext_lower == "mkv":
        return any(header.startswith(sig) for sig in MAGIC_SIGNATURES["mkv"])
    elif ext_lower == "avi":
        return header.startswith(MAGIC_SIGNATURES["avi"])
    elif ext_lower in ("mp4", "mov"):
        # MP4/MOV typically have 'ftyp' at offset 4
        return b"ftyp" in header[:32] or b"moov" in header[:32]
    return False


def validate_file_integrity(filepath: Path) -> ValidationResult:
    """
    Validates file existence, non-empty size, valid extension, magic bytes,
    and actual image/video decodability.
    
    Returns:
        ValidationResult containing is_valid, computed SHA-256, and metadata or error.
    """
    path = Path(filepath)

    if not path.exists():
        return ValidationResult(
            is_valid=False,
            error_message=f"Evidence file does not exist: {path}",
        )

    if not path.is_file():
        return ValidationResult(
            is_valid=False,
            error_message=f"Path is not a regular file: {path}",
        )

    size = path.stat().st_size
    if size == 0:
        return ValidationResult(
            is_valid=False,
            file_size_bytes=0,
            error_message="Evidence file is empty (0 bytes). Cannot process zero-byte input.",
        )

    if size > FORENSIC_CONFIG.MAX_FILE_SIZE_BYTES:
        return ValidationResult(
            is_valid=False,
            file_size_bytes=size,
            error_message=(
                f"File size ({size / (1024*1024):.2f} MB) exceeds maximum allowed size "
                f"({FORENSIC_CONFIG.MAX_FILE_SIZE_BYTES / (1024*1024):.2f} MB)."
            ),
        )

    ext = path.suffix.lower()
    is_image = ext in FORENSIC_CONFIG.SUPPORTED_IMAGE_EXTENSIONS
    is_video = ext in FORENSIC_CONFIG.SUPPORTED_VIDEO_EXTENSIONS

    if not is_image and not is_video:
        return ValidationResult(
            is_valid=False,
            file_size_bytes=size,
            error_message=(
                f"Unsupported file extension '{ext}'. Supported image formats: "
                f"{sorted(list(FORENSIC_CONFIG.SUPPORTED_IMAGE_EXTENSIONS))}; "
                f"Supported video formats: {sorted(list(FORENSIC_CONFIG.SUPPORTED_VIDEO_EXTENSIONS))}."
            ),
        )

    # Compute genuine SHA-256
    try:
        file_sha256 = calculate_sha256(path)
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            file_size_bytes=size,
            error_message=f"Failed to calculate SHA-256 hash: {str(e)}",
        )

    # Inspect header bytes
    try:
        with open(path, "rb") as f:
            header = f.read(64)
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            file_size_bytes=size,
            sha256=file_sha256,
            error_message=f"Failed to read file header: {str(e)}",
        )

    if not _check_magic_bytes(header, ext):
        return ValidationResult(
            is_valid=False,
            file_size_bytes=size,
            sha256=file_sha256,
            error_message=(
                f"File header magic bytes do not match declared extension '{ext}'. "
                f"Possible file corruption or spoofed extension."
            ),
        )

    # Validate actual decoding
    if is_image:
        try:
            with Image.open(path) as img:
                img.verify()  # Verifies structural integrity without fully decoding into memory
            # Reopen to check dimensions (verify() invalidates image buffer)
            with Image.open(path) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode

            return ValidationResult(
                is_valid=True,
                file_type="image",
                file_size_bytes=size,
                sha256=file_sha256,
                metadata={
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                },
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                file_type="image",
                file_size_bytes=size,
                sha256=file_sha256,
                error_message=f"Corrupt or unreadable image stream: {str(e)}",
            )

    elif is_video:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return ValidationResult(
                is_valid=False,
                file_type="video",
                file_size_bytes=size,
                sha256=file_sha256,
                error_message="OpenCV failed to open video stream. Codec may be missing or file is corrupted.",
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = (frame_count / fps) if fps > 0 else 0.0

        # Attempt to read first frame
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return ValidationResult(
                is_valid=False,
                file_type="video",
                file_size_bytes=size,
                sha256=file_sha256,
                error_message="Video opened but failed to read initial frame (0 decoded frames).",
            )

        return ValidationResult(
            is_valid=True,
            file_type="video",
            file_size_bytes=size,
            sha256=file_sha256,
            metadata={
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration_seconds": round(duration_sec, 2),
            },
        )

    return ValidationResult(
        is_valid=False,
        error_message="Unrecognized validation path.",
    )
