"""
Image Tampering Detection Module
Public benchmark dataset audit, training, single-pass test evaluation,
and advisory prediction with Grad-CAM explanatory visualizations.
"""

from src.tampering.dataset_audit import DatasetAuditor
from src.tampering.train import train_tampering_classifier
from src.tampering.evaluate import evaluate_test_set
from src.tampering.predict import TamperingPredictor

__all__ = [
    "DatasetAuditor",
    "train_tampering_classifier",
    "evaluate_test_set",
    "TamperingPredictor",
]
