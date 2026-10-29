"""
Unit tests for forensic file validation, magic bytes, and decodability gates.
"""

from pathlib import Path
from PIL import Image

from src.common.file_validation import validate_file_integrity


def test_validate_valid_jpeg(tmp_path: Path):
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    file_path = tmp_path / "sample.jpg"
    img.save(file_path, format="JPEG")

    result = validate_file_integrity(file_path)
    assert result.is_valid is True
    assert result.file_type == "image"
    assert result.metadata.get("width") == 200
    assert result.metadata.get("height") == 200
    assert len(result.sha256) == 64
    assert result.error_message is None


def test_validate_zero_byte_file(tmp_path: Path):
    empty_file = tmp_path / "empty.jpg"
    empty_file.write_bytes(b"")

    result = validate_file_integrity(empty_file)
    assert result.is_valid is False
    assert "empty (0 bytes)" in (result.error_message or "")


def test_validate_unsupported_extension(tmp_path: Path):
    unsupported = tmp_path / "document.pdf"
    unsupported.write_bytes(b"%PDF-1.4 sample content")

    result = validate_file_integrity(unsupported)
    assert result.is_valid is False
    assert "Unsupported file extension" in (result.error_message or "")


def test_validate_spoofed_extension(tmp_path: Path):
    # Text file disguised as JPEG
    fake_jpg = tmp_path / "spoofed.jpg"
    fake_jpg.write_text("This is plain text pretending to be an image.")

    result = validate_file_integrity(fake_jpg)
    assert result.is_valid is False
    assert "magic bytes do not match" in (result.error_message or "")


def test_validate_corrupted_image(tmp_path: Path):
    # Valid JPEG header followed by junk
    corrupt_jpg = tmp_path / "corrupt.jpg"
    corrupt_jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)

    result = validate_file_integrity(corrupt_jpg)
    assert result.is_valid is False
    assert "Corrupt or unreadable image stream" in (result.error_message or "")
