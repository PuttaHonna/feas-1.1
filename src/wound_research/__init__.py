"""
Wound Research Module (Research & Educational Only)
Enforces consented research dataset policies, patient-level splits,
and restricted visual categories.
"""

from src.wound_research.dataset import (
    ALLOWED_WOUND_CLASSES,
    create_patient_level_splits,
    verify_research_provenance,
    WoundResearchDataset,
)
from src.wound_research.train import train_wound_classifier
from src.wound_research.evaluate import evaluate_wound_test_set
from src.wound_research.predict import WoundResearchPredictor

__all__ = [
    "ALLOWED_WOUND_CLASSES",
    "create_patient_level_splits",
    "verify_research_provenance",
    "WoundResearchDataset",
    "train_wound_classifier",
    "evaluate_wound_test_set",
    "WoundResearchPredictor",
]
