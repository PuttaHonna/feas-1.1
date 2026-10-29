"""
Retrieval Evaluation for Toolmark Research Gallery
Computes Recall@K (K=1, 5, 10) and mean Average Precision (mAP)
strictly on ground-truth labeled laboratory test sets.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from src.toolmark_research.retrieve import ToolmarkRetriever
from src.common.config import FORENSIC_CONFIG


def compute_ap(retrieved_labels: List[str], target_label: str) -> float:
    """Computes Average Precision for a single query."""
    hits = 0
    sum_prec = 0.0
    for rank, label in enumerate(retrieved_labels, 1):
        if label == target_label:
            hits += 1
            sum_prec += hits / rank
    return sum_prec / hits if hits > 0 else 0.0


def evaluate_toolmark_retrieval(
    retriever: ToolmarkRetriever,
    query_samples: List[Dict[str, Any]],
    output_report_path: Path,
    working_dir: Path,
    top_k_eval: int = 10,
) -> Dict[str, Any]:
    """
    Evaluates retrieval performance across test queries against gallery index.
    Each query_sample must have: 'image_path' and 'ground_truth_class'.
    """
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    ap_scores: List[float] = []

    total_queries = len(query_samples)
    if total_queries == 0:
        raise ValueError("No query samples provided for retrieval evaluation.")

    for q in query_samples:
        q_path = Path(q["image_path"])
        gt_class = q["ground_truth_class"]

        res = retriever.retrieve_similar(q_path, working_dir=working_dir, top_k=top_k_eval)
        candidates = res.get("top_k_candidates", [])

        candidate_classes = [c.get("metadata", {}).get("class", "") for c in candidates]

        if candidate_classes:
            if candidate_classes[0] == gt_class:
                recall_at_1 += 1
            if gt_class in candidate_classes[:5]:
                recall_at_5 += 1
            if gt_class in candidate_classes[:10]:
                recall_at_10 += 1

        ap = compute_ap(candidate_classes, gt_class)
        ap_scores.append(ap)

    r1 = recall_at_1 / total_queries
    r5 = recall_at_5 / total_queries
    r10 = recall_at_10 / total_queries
    map_score = sum(ap_scores) / total_queries if ap_scores else 0.0

    eval_result = {
        "total_queries_evaluated": total_queries,
        "gallery_size": retriever.gallery_embeddings.shape[0],
        "metrics": {
            "recall_at_1": round(r1, 4),
            "recall_at_5": round(r5, 4),
            "recall_at_10": round(r10, 4),
            "mAP": round(map_score, 4),
        },
        "disclaimer": FORENSIC_CONFIG.TOOLMARK_OUTPUT_WORDING,
        "human_review_notice": "Evaluation metrics represent experimental visual retrieval only and do not establish forensic firearm identification.",
    }

    out_p = Path(output_report_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, indent=2)

    return eval_result
