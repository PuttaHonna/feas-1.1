"""
Unit tests for cryptographic SHA-256 and perceptual hashing utilities.
"""

import hashlib
import pytest
from pathlib import Path
from PIL import Image

from src.common.hashing import (
    calculate_sha256,
    calculate_sha256_bytes,
    calculate_perceptual_hash,
    calculate_hamming_distance,
)


def test_calculate_sha256_known_vector(tmp_path: Path):
    test_data = b"forensic_integrity_test_payload_123456"
    expected_sha256 = hashlib.sha256(test_data).hexdigest().lower()

    test_file = tmp_path / "test_sample.bin"
    test_file.write_bytes(test_data)

    computed_sha256 = calculate_sha256(test_file)
    assert computed_sha256 == expected_sha256
    assert calculate_sha256_bytes(test_data) == expected_sha256


def test_calculate_sha256_missing_file():
    with pytest.raises(FileNotFoundError):
        calculate_sha256("non_existent_evidence_file_999.jpg")


def test_calculate_sha256_directory(tmp_path: Path):
    with pytest.raises(ValueError):
        calculate_sha256(tmp_path)


def test_perceptual_hashing_identical_and_different(tmp_path: Path):
    # Create test image
    img1 = Image.new("RGB", (100, 100), color=(120, 120, 120))
    path1 = tmp_path / "img1.png"
    img1.save(path1)

    # Identical content
    path2 = tmp_path / "img2.png"
    img1.save(path2)

    # Radically different pattern
    img3 = Image.new("RGB", (100, 100), color=(0, 0, 0))
    for x in range(50):
        for y in range(50):
            img3.putpixel((x, y), (255, 255, 255))
    path3 = tmp_path / "img3.png"
    img3.save(path3)

    hash1 = calculate_perceptual_hash(path1, hash_type="phash")
    hash2 = calculate_perceptual_hash(path2, hash_type="phash")
    hash3 = calculate_perceptual_hash(path3, hash_type="phash")

    assert hash1 == hash2
    assert calculate_hamming_distance(hash1, hash2) == 0
    assert calculate_hamming_distance(hash1, hash3) > 0
