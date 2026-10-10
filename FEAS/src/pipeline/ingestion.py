"""
Forensic Evidence Analysis System (FEAS) - Ingestion & Keyframe Extraction Pipeline
Validates file extensions & size, computes cryptographic SHA-256 hashes, and extracts video keyframes at 1 fps.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
from PIL import Image

from src.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    STORAGE_DIR,
    TEMP_DIR,
    VIDEO_KEYFRAME_FPS
)
from src.pipeline.advanced_metadata import inspect_advanced_binary_metadata
from src.pipeline.metadata import extract_metadata


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash directly from byte buffer."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def compute_sha256_file(file_path: Union[str, Path]) -> str:
    """Compute SHA-256 hash of a file by streaming in chunks."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_file(filename: str, size_bytes: int) -> Tuple[bool, Optional[str]]:
    """Validate file extension and size constraints."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return False, f"File size ({size_bytes / (1024*1024):.2f} MB) exceeds 500 MB limit."
    
    return True, None


def extract_video_keyframes(video_path: Union[str, Path], output_dir: Path) -> List[str]:
    """
    Extract keyframes from a video file at exactly 1 frame per second (1 fps).
    Saves extracted frames as JPEG files in output_dir.
    Returns list of extracted keyframe paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or not (fps == fps):  # handle NaN or 0
        fps = 30.0
        
    frame_interval = max(1, int(round(fps / VIDEO_KEYFRAME_FPS)))
    frame_idx = 0
    extracted_idx = 0
    keyframe_paths = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % frame_interval == 0:
            frame_filename = f"keyframe_{extracted_idx:04d}.jpg"
            frame_path = output_dir / frame_filename
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            keyframe_paths.append(str(frame_path))
            extracted_idx += 1
            
        frame_idx += 1
        
    cap.release()
    return keyframe_paths


def process_uploaded_media(
    file_bytes: bytes,
    filename: str,
    target_storage_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Ingest and process media:
    1. Validate size and extension.
    2. Compute SHA-256 hash.
    3. Persist to storage directory.
    4. Extract EXIF metadata (for images).
    5. Extract keyframes at 1 fps (for videos).
    """
    size_bytes = len(file_bytes)
    is_valid, err_msg = validate_file(filename, size_bytes)
    if not is_valid:
        raise ValueError(err_msg)

    sha256_hash = compute_sha256_bytes(file_bytes)
    ext = Path(filename).suffix.lower()
    is_video = ext in {".mp4", ".mkv", ".avi"}
    is_audio = ext in {".wav", ".mp3", ".m4a", ".aac", ".flac"}

    dest_dir = target_storage_dir or (STORAGE_DIR / sha256_hash)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    saved_media_path = dest_dir / f"source{ext}"
    with open(saved_media_path, "wb") as f:
        f.write(file_bytes)

    keyframes: List[str] = []
    primary_image_path = str(saved_media_path)
    metadata: Dict[str, Any] = {}

    if is_video:
        frames_dir = dest_dir / "keyframes"
        keyframes = extract_video_keyframes(saved_media_path, frames_dir)
        if keyframes:
            primary_image_path = keyframes[0]
        metadata = {
            "has_exif": False,
            "is_video": True,
            "total_keyframes": len(keyframes),
            "keyframe_paths": keyframes
        }
    elif is_audio:
        metadata = {
            "has_exif": False,
            "is_audio": True,
            "format": ext
        }
    else:
        metadata = extract_metadata(saved_media_path)

    advanced_meta = inspect_advanced_binary_metadata(saved_media_path)

    file_type = "video" if is_video else ("audio" if is_audio else "image")

    return {
        "filename": filename,
        "file_type": file_type,
        "file_ext": ext,
        "file_size": size_bytes,
        "input_sha256": sha256_hash,
        "stored_path": str(saved_media_path),
        "is_video": is_video,
        "is_audio": is_audio,
        "keyframes": keyframes,
        "primary_image_path": primary_image_path,
        "metadata": metadata,
        "advanced_metadata": advanced_meta
    }
