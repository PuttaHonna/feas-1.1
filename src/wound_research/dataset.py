"""
Wound Research Dataset Management & Patient-Level Splitting
Enforces:
1. Research provenance and consent verification.
2. Patient/subject-level disjoint splitting (no images from the same subject cross splits).
3. Whitelisted visual categories only (no diagnostic/forensic claims).
"""

import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

# Permitted visual categories (mechanical trauma and clinical dermatopathology)
ALLOWED_WOUND_CLASSES = [
    "abrasion",
    "bruise/contusion",
    "laceration",
    "incision",
    "puncture",
    "burn",
    "no visible wound",
    "benign_lesion",
    "nevus",
    "melanoma",
    "keratosis",
    "carcinoma",
]

CLASS_TO_IDX = {cls_name: idx for idx, cls_name in enumerate(ALLOWED_WOUND_CLASSES)}
IDX_TO_CLASS = {idx: cls_name for idx, cls_name in enumerate(ALLOWED_WOUND_CLASSES)}



def verify_research_provenance(metadata: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifies that the uploaded image belongs to a documented, consented research protocol.
    Rejects normal unconsented user-uploaded photos by policy.
    """
    if not metadata:
        return False, "No research metadata provided. Direct user-uploaded photos are rejected by policy."

    has_dataset_id = bool(metadata.get("research_dataset_id"))
    has_consent = bool(metadata.get("ethical_consent_documented"))
    has_license = bool(metadata.get("research_license"))

    if not (has_dataset_id and has_consent and has_license):
        missing = []
        if not has_dataset_id:
            missing.append("research_dataset_id")
        if not has_consent:
            missing.append("ethical_consent_documented")
        if not has_license:
            missing.append("research_license")
        return (
            False,
            f"Input fails research compliance gate. Missing mandatory attributes: {', '.join(missing)}.",
        )

    return True, "Research provenance verified."


def create_patient_level_splits(
    samples: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups images by patient_id / source_id to prevent subject-level data leakage across splits.
    """
    random.seed(seed)
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-4

    # Group by patient_id
    patient_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        pid = sample.get("patient_id") or sample.get("source_id") or "anonymous_unlinked"
        patient_buckets[pid].append(sample)

    patient_ids = list(patient_buckets.keys())
    random.shuffle(patient_ids)

    n_patients = len(patient_ids)
    n_train = max(1, int(n_patients * train_ratio))
    n_val = max(1, int(n_patients * val_ratio)) if n_patients > 2 else 0

    train_pids = set(patient_ids[:n_train])
    val_pids = set(patient_ids[n_train:n_train + n_val])
    test_pids = set(patient_ids[n_train + n_val:])

    # If test is empty due to small count, adjust
    if not test_pids and len(val_pids) > 1:
        moved = val_pids.pop()
        test_pids.add(moved)

    splits: Dict[str, List[Dict[str, Any]]] = {"train": [], "val": [], "test": []}

    for pid, s_list in patient_buckets.items():
        if pid in train_pids:
            splits["train"].extend(s_list)
        elif pid in val_pids:
            splits["val"].extend(s_list)
        else:
            splits["test"].extend(s_list)

    return splits


class WoundResearchDataset(Dataset):
    """PyTorch Dataset for consented wound research images."""

    def __init__(
        self,
        samples: List[Dict[str, Any]],
        transform: Optional[transforms.Compose] = None,
    ):
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        item = self.samples[idx]
        img_path = Path(item["path"])
        label_str = item["class"]
        label_idx = CLASS_TO_IDX.get(label_str, len(CLASS_TO_IDX) - 1)

        with Image.open(img_path) as img:
            rgb_img = img.convert("RGB")

        if self.transform:
            tensor = self.transform(rgb_img)
        else:
            tensor = transforms.ToTensor()(rgb_img)

        return tensor, label_idx, str(img_path)
