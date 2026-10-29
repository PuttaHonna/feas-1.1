"""
Top-K Toolmark Visual Similarity Retrieval Engine
Performs similarity search against laboratory reference image index.
Strictly prohibited from asserting firearm attribution, caliber, manufacturer, or legal conclusions.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256
from src.toolmark_research.index import ToolmarkIndexBuilder
from src.toolmark_research.standardization import standardize_toolmark_working_copy


class ToolmarkRetriever:
    """
    Experimental similarity search engine for controlled laboratory reference toolmarks.
    Returns nearest visual neighbors with explicit non-attribution warnings.
    """

    def __init__(
        self,
        index_dir: Path,
        similarity_threshold: float = 0.45,
        pretrained: bool = True,
        seed: int = 42,
        encoder: Optional[Any] = None,
        device: Optional[str] = None,
    ):
        self.index_dir = Path(index_dir)
        self.similarity_threshold = similarity_threshold

        # Load indexed embeddings and gallery metadata
        matrix_p = self.index_dir / "toolmark_embeddings.npy"
        meta_p = self.index_dir / "toolmark_gallery_meta.json"

        if not matrix_p.exists() or not meta_p.exists():
            raise FileNotFoundError(
                f"Toolmark gallery index files not found in {self.index_dir}."
            )

        self.gallery_embeddings = np.load(str(matrix_p))
        with open(meta_p, "r", encoding="utf-8") as f:
            self.gallery_metadata = json.load(f)

        self.index_builder = ToolmarkIndexBuilder(
            pretrained=pretrained,
            seed=seed,
            encoder=encoder,
            device=device,
        )

    def retrieve_similar(
        self,
        query_image_path: Path,
        working_dir: Path,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes query image standardization, embedding extraction, and top-K nearest search.
        """
        q_path = Path(query_image_path)
        if not q_path.exists():
            raise FileNotFoundError(f"Query toolmark image not found: {q_path}")

        # 1. Standardize query working copy
        working_std_path = Path(working_dir) / f"standardized_{q_path.stem}.png"
        std_path, std_sha256 = standardize_toolmark_working_copy(
            working_copy_path=q_path,
            output_standardized_path=working_std_path,
        )

        # 2. Extract query embedding
        query_emb = self.index_builder.extract_embedding(std_path)

        # 3. Compute cosine similarities (dot product between normalized vectors)
        similarities = np.dot(self.gallery_embeddings, query_emb)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        max_sim = float(similarities[top_indices[0]]) if len(top_indices) > 0 else 0.0

        # Check for insufficient reference data
        if max_sim < self.similarity_threshold:
            return {
                "status": "insufficient_reference_data",
                "message": (
                    f"Highest similarity score ({max_sim:.4f}) is below threshold ({self.similarity_threshold:.4f}). "
                    f"Insufficient reference data in gallery for reliable visual comparison."
                ),
                "query_image": str(q_path),
                "standardized_copy_sha256": std_sha256,
                "top_k_candidates": [],
                "disclaimer": FORENSIC_CONFIG.TOOLMARK_OUTPUT_WORDING,
                "human_review_required": True,
            }

        candidates: List[Dict[str, Any]] = []
        for rank, idx in enumerate(top_indices, 1):
            sim = float(similarities[idx])
            dist = float(np.sqrt(max(0.0, 2.0 - 2.0 * sim)))
            meta = self.gallery_metadata[idx]

            candidates.append({
                "rank": rank,
                "ref_id": meta["ref_id"],
                "similarity_score": round(sim, 4),
                "cosine_distance": round(dist, 4),
                "image_path": meta["image_path"],
                "sha256": meta["sha256"],
                "lab_dataset": meta["lab_dataset"],
                "metadata": meta["metadata"],
            })

        return {
            "status": "completed",
            "query_image": str(q_path),
            "standardized_copy_sha256": std_sha256,
            "top_k_candidates": candidates,
            "max_similarity": round(max_sim, 4),
            "total_gallery_items": len(self.gallery_metadata),
            "disclaimer": FORENSIC_CONFIG.TOOLMARK_OUTPUT_WORDING,
            "human_review_required": True,
            "forbidden_claims": [
                "No firearm attribution",
                "No bullet caliber conclusion",
                "No manufacturer identification",
                "No common source determination",
                "No criminal linkage",
            ],
        }
