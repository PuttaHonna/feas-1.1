"""
Forensic Evidence Vault & Working Copy Management Utilities
Preserves original digital evidence read-only, calculates hashes before and after copy,
and manages derived working copies.
"""

import os
import shutil
import stat
import random
from pathlib import Path
from typing import Tuple
import numpy as np

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256


def set_random_seed(seed: int = FORENSIC_CONFIG.DEFAULT_RANDOM_SEED) -> None:
    """Set deterministic random seed for Python, NumPy, and PyTorch (if available)."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)
    except ImportError:
        pass


def get_optimal_device():
    """
    Returns optimal computation device across all operating systems and hardware:
    - CUDA for NVIDIA GPUs (Linux/Windows)
    - MPS for Apple Silicon GPUs (macOS M1/M2/M3/M4)
    - CPU fallback (Universal)
    """
    try:
        import torch
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    except ImportError:
        return "cpu"


def preserve_original_evidence(
    source_path: Path,
    evidence_id: str,
    vault_dir: Path = FORENSIC_CONFIG.EVIDENCE_VAULT_DIR,
) -> Tuple[Path, str]:
    """
    Copies uploaded evidence into the evidence vault and makes it strictly read-only.
    Verifies that the copied file's SHA-256 precisely matches the original.
    
    Returns:
        Tuple of (vault_path, sha256_hash)
        
    Raises:
        ValueError: If SHA-256 hash differs after copy.
    """
    src = Path(source_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Source evidence file not found: {src}")

    vault_dir.mkdir(parents=True, exist_ok=True)
    orig_sha256 = calculate_sha256(src)

    # Destination filename includes evidence_id to avoid collisions
    dest_name = f"{evidence_id}_{src.name}"
    vault_path = vault_dir / dest_name

    # If already safely preserved with matching SHA-256, reuse existing vault record
    if vault_path.exists():
        try:
            if calculate_sha256(vault_path) == orig_sha256:
                return vault_path, orig_sha256
        except Exception:
            pass
        # If hash differs or cannot read, create unique collision-free destination
        import uuid
        dest_name = f"{evidence_id}_{uuid.uuid4().hex[:8]}_{src.name}"
        vault_path = vault_dir / dest_name

    # Copy binary stream verbatim
    shutil.copy2(str(src), str(vault_path))

    # Verify SHA-256 integrity post-copy
    copied_sha256 = calculate_sha256(vault_path)
    if copied_sha256 != orig_sha256:
        # Integrity violation, delete corrupted target
        if vault_path.exists():
            try:
                os.chmod(vault_path, stat.S_IWRITE)
                vault_path.unlink()
            except Exception:
                pass
        raise ValueError(
            f"Cryptographic hash mismatch after vault copy! Original: {orig_sha256}, Copied: {copied_sha256}"
        )

    # Make file read-only to preserve evidentiary integrity
    try:
        os.chmod(vault_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except Exception:
        pass

    return vault_path, orig_sha256


def create_working_copy(
    vault_path: Path,
    evidence_id: str,
    working_dir: Path = FORENSIC_CONFIG.WORKING_COPY_DIR,
) -> Tuple[Path, str]:
    """
    Creates a separate working copy for derived automated analysis.
    The working copy is read-write for analysis pipelines, while the vault file remains read-only.
    
    Returns:
        Tuple of (working_copy_path, working_copy_sha256)
    """
    vault = Path(vault_path)
    if not vault.exists():
        raise FileNotFoundError(f"Evidence vault file not found: {vault}")

    working_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"working_{evidence_id}_{vault.name}"
    working_path = working_dir / dest_name

    if working_path.exists():
        try:
            os.chmod(working_path, stat.S_IWRITE | stat.S_IREAD)
            working_path.unlink()
        except Exception:
            import uuid
            dest_name = f"working_{evidence_id}_{uuid.uuid4().hex[:8]}_{vault.name}"
            working_path = working_dir / dest_name

    shutil.copy2(str(vault), str(working_path))

    # Ensure working copy is writable
    try:
        os.chmod(working_path, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass

    working_sha256 = calculate_sha256(working_path)
    return working_path, working_sha256
