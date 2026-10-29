"""
CCTV Working Copy Module.
Creates a cryptographically verified working copy for all downstream processing,
guaranteeing the original evidence remains immutable and untouched.
"""

from __future__ import annotations
import shutil
from pathlib import Path
from typing import Tuple

from src.cctv.integrity import calculate_file_sha256, verify_sha256


def create_verified_working_copy(
    original_path: Path | str,
    working_copies_dir: Path | str,
    unique_prefix: str = "",
    evidence_id: Optional[str] = None,
    **kwargs
) -> Tuple[Path, str]:
    """Create an exact, byte-for-byte working copy of the original video and verify hash match."""
    orig = Path(original_path)
    dest_dir = Path(working_copies_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    pfx = evidence_id or unique_prefix
    prefix = f"{pfx}_" if pfx else "work_"
    filename = f"{prefix}{orig.name}"
    working_copy_path = dest_dir / filename

    # Compute original hash
    original_hash = calculate_file_sha256(orig)

    # Perform binary copy
    shutil.copy2(orig, working_copy_path)

    # Verify working copy hash
    working_copy_hash = calculate_file_sha256(working_copy_path)
    if working_copy_hash.lower() != original_hash.lower():
        # Clean up corrupted copy immediately
        try:
            working_copy_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise ValueError(
            f"Working copy verification failed! Hash mismatch between original "
            f"({original_hash}) and working copy ({working_copy_hash})."
        )

    return working_copy_path, working_copy_hash
