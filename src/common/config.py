"""
Forensics Configuration & Compliance Constraints
Central configuration defining evidence isolation directories, quality-gate thresholds,
deterministic seeds, and mandatory forensic disclaimers.
"""

import os
from pathlib import Path
from typing import List, Set
from pydantic import BaseModel, Field

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class ForensicConfig(BaseModel):
    # Directory paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data")
    EVIDENCE_VAULT_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "evidence_vault")
    WORKING_COPY_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "working_copies")
    ARTIFACTS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "artifacts")
    AUDIT_DB_PATH: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data" / "forensics_audit.db")
    MODELS_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "models")

    # Determinism
    DEFAULT_RANDOM_SEED: int = 42

    # Supported formats
    SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mkv", ".avi", ".mov"}
    MAX_FILE_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB default max

    # Pre-inference quality gate thresholds
    MIN_IMAGE_WIDTH: int = 64
    MIN_IMAGE_HEIGHT: int = 64
    BLUR_LAPLACIAN_VAR_MIN: float = 25.0
    LUMINANCE_MIN: float = 15.0     # Reject pitch black / severely underexposed
    LUMINANCE_MAX: float = 245.0    # Reject washed out / completely overexposed

    # Mandatory Legal & Forensic Disclaimers
    MANDATORY_DISCLAIMER: str = (
        "Experimental model output — requires qualified human review."
    )
    MANDATORY_REPORT_FOOTER: str = (
        "Experimental software output. Not a legal conclusion, medical diagnosis, firearm attribution, "
        "or proof of authenticity. Human expert review is required."
    )
    WOUND_OUTPUT_WORDING: str = (
        "Experimental visual-category prediction. This output is not a diagnosis and must not be used for "
        "medical, legal, or forensic decisions."
    )
    TOOLMARK_OUTPUT_WORDING: str = (
        "Experimental visual similarity retrieval. Similarity does not establish common source, firearm "
        "attribution, caliber, manufacturer, or legal conclusion."
    )
    DERIVED_FRAME_LABEL: str = (
        "Derived working image for visualization and automated analysis. Original footage remains unchanged."
    )
    TAMPERING_POSITIVE_LABEL: str = (
        "The model classified this image as likely manipulated based on patterns represented in its training data."
    )
    TAMPERING_NEGATIVE_LABEL: str = (
        "The model classified this image as consistent with authentic reference data in its training distribution."
    )

    def ensure_directories(self) -> None:
        """Create required data directories if they do not exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.EVIDENCE_VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.WORKING_COPY_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


FORENSIC_CONFIG = ForensicConfig()
FORENSIC_CONFIG.ensure_directories()
