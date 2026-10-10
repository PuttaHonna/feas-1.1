"""
CCTV Evidence Integrity Module.
Computes cryptographic SHA-256 hashes to guarantee chain-of-custody verification.
"""

from __future__ import annotations
import hashlib
from pathlib import Path


def calculate_file_sha256(file_path: Path | str, chunk_size: int = 65536) -> str:
    """Calculate the cryptographic SHA-256 hash of a file.

    Args:
        file_path: Path to target file.
        chunk_size: Byte chunk size for streaming read (default 64 KB).

    Returns:
        Hexadecimal SHA-256 string.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Target file does not exist: {path}")

    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(file_path: Path | str, expected_hash: str) -> bool:
    """Verify whether a file's SHA-256 hash matches the expected hash.

    Args:
        file_path: Path to target file.
        expected_hash: Hexadecimal expected hash string.

    Returns:
        True if hashes match exactly, False otherwise.
    """
    actual_hash = calculate_file_sha256(file_path)
    return actual_hash.lower() == expected_hash.lower()
