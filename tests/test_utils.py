"""
Unit tests for evidence preservation and working copy creation.
"""

from pathlib import Path
from PIL import Image
from src.common.utils import preserve_original_evidence, create_working_copy
from src.common.hashing import calculate_sha256


def test_evidence_preservation_and_working_copy(tmp_path: Path):
    vault_dir = tmp_path / "vault"
    working_dir = tmp_path / "working"

    # Create dummy source image
    src_file = tmp_path / "original_sample.png"
    img = Image.new("RGB", (100, 100), color=(50, 100, 150))
    img.save(src_file)

    original_hash = calculate_sha256(src_file)

    # 1. Preserve evidence
    evidence_id = "test-ev-001"
    vault_path, vault_hash = preserve_original_evidence(
        src_file, evidence_id=evidence_id, vault_dir=vault_dir
    )

    assert vault_path.exists()
    assert vault_hash == original_hash
    assert calculate_sha256(vault_path) == original_hash

    # 2. Create derived working copy
    working_path, working_hash = create_working_copy(
        vault_path, evidence_id=evidence_id, working_dir=working_dir
    )

    assert working_path.exists()
    assert working_hash == original_hash
    assert calculate_sha256(working_path) == original_hash
    assert working_path != vault_path
