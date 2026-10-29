"""
Forensic Cryptographic & Perceptual Hashing Utilities
Provides strictly deterministic SHA-256 evidence integrity hashing and perceptual hashing (pHash/dHash).
"""

import hashlib
from pathlib import Path
from typing import Union
from PIL import Image
import imagehash


def calculate_sha256(filepath: Union[Path, str], chunk_size: int = 65536) -> str:
    """
    Calculate cryptographic SHA-256 hash of a file using chunked streaming.
    Preserves memory safety on large CCTV video files.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If file is unreadable.
        ValueError: If filepath points to a directory.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Target evidence file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
            
    return hasher.hexdigest().lower()


def calculate_sha256_bytes(data: bytes) -> str:
    """Calculate cryptographic SHA-256 hash of in-memory bytes."""
    return hashlib.sha256(data).hexdigest().lower()


def calculate_perceptual_hash(
    image_input: Union[Path, str, Image.Image],
    hash_type: str = "phash",
    hash_size: int = 8,
) -> str:
    """
    Calculate perceptual hash (pHash, dHash, or aHash) for near-duplicate and leakage detection.
    
    Args:
        image_input: Path to image or PIL Image instance.
        hash_type: 'phash' (DCT-based), 'dhash' (gradient difference), or 'ahash' (average).
        hash_size: Size of the hash matrix (default 8 -> 64-bit hash).
        
    Returns:
        Hexadecimal perceptual hash string.
    """
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")
        with Image.open(path) as img:
            pil_img = img.convert("RGB")
    elif isinstance(image_input, Image.Image):
        pil_img = image_input.convert("RGB")
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    hash_type_lower = hash_type.lower()
    if hash_type_lower == "phash":
        h = imagehash.phash(pil_img, hash_size=hash_size)
    elif hash_type_lower == "dhash":
        h = imagehash.dhash(pil_img, hash_size=hash_size)
    elif hash_type_lower == "ahash":
        h = imagehash.average_hash(pil_img, hash_size=hash_size)
    else:
        raise ValueError(f"Unsupported hash_type: {hash_type}. Choose from 'phash', 'dhash', 'ahash'.")

    return str(h)


def calculate_hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate the Hamming distance (number of bit positions differing) between two perceptual hashes.
    A distance of 0 indicates an identical visual representation; <= 5 indicates high visual similarity.
    """
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return int(h1 - h2)
