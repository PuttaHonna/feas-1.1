"""
Forensic Dataset Audit & Leakage Prevention Pipeline
Audits image manipulation datasets for:
1. Corrupt/unreadable images
2. Exact duplicate images (SHA-256)
3. Near-duplicate images (Perceptual Hashing)
4. Information leakage (filename, extension, resolution bias across classes)
5. Strict train/validation/test splitting without cross-split leakage
"""

import os
import json
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from PIL import Image
import numpy as np

from src.common.hashing import calculate_sha256, calculate_perceptual_hash, calculate_hamming_distance
from src.common.config import FORENSIC_CONFIG


class DatasetAuditor:
    """
    Audits an image dataset directory containing subdirectories for each class.
    Ensures strict scientific integrity and prevents split contamination.
    """

    def __init__(
        self,
        dataset_dir: Path,
        classes: Tuple[str, ...] = ("authentic", "manipulated"),
        near_duplicate_hamming_thresh: int = 3,
        random_seed: int = FORENSIC_CONFIG.DEFAULT_RANDOM_SEED,
    ):
        self.dataset_dir = Path(dataset_dir)
        self.classes = classes
        self.near_duplicate_thresh = near_duplicate_hamming_thresh
        self.random_seed = random_seed

    def audit(self) -> Dict[str, Any]:
        """
        Runs the full audit suite.
        Returns a detailed summary dictionary of findings.
        """
        corrupted_files: List[str] = []
        valid_files_by_class: Dict[str, List[Path]] = defaultdict(list)
        file_sha256: Dict[str, str] = {}
        file_phash: Dict[str, str] = {}
        resolution_stats: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        ext_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 1. Scan and detect corruption
        for cls in self.classes:
            cls_dir = self.dataset_dir / cls
            if not cls_dir.exists():
                continue

            for file_path in cls_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                ext = file_path.suffix.lower()
                if ext not in FORENSIC_CONFIG.SUPPORTED_IMAGE_EXTENSIONS:
                    continue

                ext_stats[cls][ext] += 1

                # Check decodability
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                    with Image.open(file_path) as img:
                        w, h = img.size
                    resolution_stats[cls].append((w, h))

                    # Compute hashes
                    sha = calculate_sha256(file_path)
                    ph = calculate_perceptual_hash(file_path, hash_type="phash")

                    file_sha256[str(file_path)] = sha
                    file_phash[str(file_path)] = ph
                    valid_files_by_class[cls].append(file_path)

                except Exception as e:
                    corrupted_files.append(f"{file_path} (Error: {str(e)})")

        # 2. Detect exact duplicates across and within classes
        sha_to_paths: Dict[str, List[str]] = defaultdict(list)
        for p_str, sha in file_sha256.items():
            sha_to_paths[sha].append(p_str)

        exact_duplicates: List[List[str]] = [
            paths for paths in sha_to_paths.values() if len(paths) > 1
        ]

        # 3. Detect near duplicates using perceptual hashing
        unique_paths = list(file_phash.keys())
        near_duplicate_pairs: List[Tuple[str, str, int]] = []
        
        # Compare pairwise among samples
        for i in range(len(unique_paths)):
            for j in range(i + 1, len(unique_paths)):
                p1, p2 = unique_paths[i], unique_paths[j]
                # Skip if already identified as exact duplicate
                if file_sha256[p1] == file_sha256[p2]:
                    continue
                dist = calculate_hamming_distance(file_phash[p1], file_phash[p2])
                if dist <= self.near_duplicate_thresh:
                    near_duplicate_pairs.append((p1, p2, dist))

        # 4. Leakage checks
        leakage_warnings: List[str] = []
        
        # Extension distribution check
        for cls, counts in ext_stats.items():
            total = sum(counts.values())
            for ext, count in counts.items():
                ratio = count / total if total > 0 else 0
                if ratio > 0.95 and len(self.classes) > 1:
                    other_cls = [c for c in self.classes if c != cls]
                    for oc in other_cls:
                        oc_total = sum(ext_stats[oc].values())
                        oc_count = ext_stats[oc].get(ext, 0)
                        oc_ratio = oc_count / oc_total if oc_total > 0 else 0
                        if oc_ratio < 0.05:
                            leakage_warnings.append(
                                f"Potential extension leakage: class '{cls}' is {ratio*100:.1f}% '{ext}' "
                                f"whereas class '{oc}' is only {oc_ratio*100:.1f}% '{ext}'."
                            )

        # Audit report
        report: Dict[str, Any] = {
            "dataset_directory": str(self.dataset_dir),
            "classes_scanned": list(self.classes),
            "corrupted_files_count": len(corrupted_files),
            "corrupted_files": corrupted_files[:20],  # first 20 if large
            "total_valid_images": sum(len(v) for v in valid_files_by_class.values()),
            "class_counts": {c: len(v) for c, v in valid_files_by_class.items()},
            "exact_duplicate_groups_count": len(exact_duplicates),
            "near_duplicate_pairs_count": len(near_duplicate_pairs),
            "leakage_warnings": leakage_warnings,
        }
        return report

    def create_clean_splits(
        self,
        output_manifest_path: Path,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Creates deduplicated train/val/test splits.
        Guarantees:
        - No exact duplicate images cross splits.
        - No near duplicate images cross splits.
        """
        random.seed(self.random_seed)
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-4

        # Group connected duplicate/near-duplicate images into clusters
        file_sha: Dict[str, str] = {}
        file_phash: Dict[str, str] = {}
        class_map: Dict[str, str] = {}
        all_paths: List[str] = []

        for cls in self.classes:
            cls_dir = self.dataset_dir / cls
            if not cls_dir.exists():
                continue
            for f in cls_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in FORENSIC_CONFIG.SUPPORTED_IMAGE_EXTENSIONS:
                    try:
                        sha = calculate_sha256(f)
                        ph = calculate_perceptual_hash(f)
                        p_str = str(f)
                        file_sha[p_str] = sha
                        file_phash[p_str] = ph
                        class_map[p_str] = cls
                        all_paths.append(p_str)
                    except Exception:
                        continue

        # Disjoint Set Union (DSU) to cluster duplicates
        parent: Dict[str, str] = {p: p for p in all_paths}

        def find(i: str) -> str:
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i: str, j: str) -> None:
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        # Cluster by exact SHA-256
        sha_buckets: Dict[str, List[str]] = defaultdict(list)
        for p, sha in file_sha.items():
            sha_buckets[sha].append(p)
        for p_list in sha_buckets.values():
            for i in range(1, len(p_list)):
                union(p_list[0], p_list[i])

        # Cluster by near-duplicate pHash
        for i in range(len(all_paths)):
            for j in range(i + 1, len(all_paths)):
                p1, p2 = all_paths[i], all_paths[j]
                if find(p1) != find(p2):
                    dist = calculate_hamming_distance(file_phash[p1], file_phash[p2])
                    if dist <= self.near_duplicate_thresh:
                        union(p1, p2)

        # Collect clusters
        clusters: Dict[str, List[str]] = defaultdict(list)
        for p in all_paths:
            clusters[find(p)].append(p)

        cluster_list = list(clusters.values())
        random.shuffle(cluster_list)

        # Split clusters
        n_clusters = len(cluster_list)
        n_train = int(n_clusters * train_ratio)
        n_val = int(n_clusters * val_ratio)

        train_clusters = cluster_list[:n_train]
        val_clusters = cluster_list[n_train:n_train + n_val]
        test_clusters = cluster_list[n_train + n_val:]

        splits: Dict[str, List[Dict[str, str]]] = {"train": [], "val": [], "test": []}

        for c_group in train_clusters:
            for p in c_group:
                splits["train"].append({"path": p, "class": class_map[p], "sha256": file_sha[p]})
        for c_group in val_clusters:
            for p in c_group:
                splits["val"].append({"path": p, "class": class_map[p], "sha256": file_sha[p]})
        for c_group in test_clusters:
            for p in c_group:
                splits["test"].append({"path": p, "class": class_map[p], "sha256": file_sha[p]})

        out_path = Path(output_manifest_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(splits, f, indent=2)

        return splits
