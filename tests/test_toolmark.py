"""
Unit and integration tests for Module 4: Bullet & Toolmark Visual Similarity Retrieval.
"""

from pathlib import Path
import pytest
from PIL import Image
import numpy as np

from src.toolmark_research.standardization import standardize_toolmark_working_copy
from src.toolmark_research.index import ToolmarkIndexBuilder
from src.toolmark_research.retrieve import ToolmarkRetriever
from src.toolmark_research.evaluate import evaluate_toolmark_retrieval
from src.common.config import FORENSIC_CONFIG


def test_toolmark_working_copy_standardization(tmp_path: Path):
    # Create rectangular image (200x150)
    arr = np.full((150, 200, 3), 110, dtype=np.uint8)
    arr[50:100, 50:100] = 200
    in_img = tmp_path / "raw_toolmark.png"
    Image.fromarray(arr).save(in_img)

    out_std = tmp_path / "std_toolmark.png"
    res_path, res_hash = standardize_toolmark_working_copy(
        working_copy_path=in_img,
        output_standardized_path=out_std,
        target_dim=128,
        normalize_lighting=True,
    )

    assert res_path.exists()
    assert len(res_hash) == 64
    with Image.open(res_path) as out:
        assert out.size == (128, 128)  # Square standardized


def test_toolmark_indexing_and_retrieval(tmp_path: Path):
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()

    records = []
    # Create 3 reference images
    for i in range(3):
        arr = np.zeros((128, 128, 3), dtype=np.uint8)
        arr[i * 30:(i + 1) * 30, :] = 255
        p = gallery_dir / f"ref_{i}.png"
        Image.fromarray(arr).save(p)

        records.append({
            "ref_id": f"NIST_REF_{i}",
            "image_path": str(p),
            "metadata": {"class": f"tool_pattern_{i}"},
            "lab_dataset": "NIST_NBTRD_BENCHMARK",
        })

    # Build index with random weights for speed
    index_dir = tmp_path / "index"
    builder = ToolmarkIndexBuilder(pretrained=False, device="cpu")
    idx_out = builder.build_index(records, index_dir)
    assert idx_out["total_indexed"] == 3

    # Query with identical image to ref_1
    retriever = ToolmarkRetriever(index_dir, similarity_threshold=0.40, encoder=builder.encoder, device="cpu")
    res = retriever.retrieve_similar(
        query_image_path=Path(records[1]["image_path"]),
        working_dir=tmp_path / "working",
        top_k=2,
    )

    assert res["status"] == "completed"
    assert len(res["top_k_candidates"]) == 2
    # Top rank should be the identical reference item
    assert res["top_k_candidates"][0]["ref_id"] == "NIST_REF_1"
    assert res["disclaimer"] == FORENSIC_CONFIG.TOOLMARK_OUTPUT_WORDING
    assert res["human_review_required"] is True
    assert "No firearm attribution" in res["forbidden_claims"]

    # Query with unrelated image with high threshold -> insufficient reference data
    strict_retriever = ToolmarkRetriever(index_dir, similarity_threshold=0.99999, encoder=builder.encoder, device="cpu")
    diff_img = tmp_path / "different.png"
    Image.new("RGB", (128, 128), color=(10, 10, 10)).save(diff_img)

    low_res = strict_retriever.retrieve_similar(
        query_image_path=diff_img,
        working_dir=tmp_path / "working",
        top_k=2,
    )
    assert low_res["status"] == "insufficient_reference_data"
    assert "Insufficient reference data" in low_res["message"]


def test_toolmark_retrieval_evaluation(tmp_path: Path):
    gallery_dir = tmp_path / "gallery_eval"
    gallery_dir.mkdir()

    records = []
    for i in range(4):
        arr = np.zeros((128, 128, 3), dtype=np.uint8)
        arr[i * 20:(i + 1) * 20, :] = 255
        p = gallery_dir / f"ref_{i}.png"
        Image.fromarray(arr).save(p)
        records.append({
            "ref_id": f"REF_{i}",
            "image_path": str(p),
            "metadata": {"class": f"type_{i % 2}"},
        })

    index_dir = tmp_path / "index_eval"
    builder = ToolmarkIndexBuilder(pretrained=False, device="cpu")
    builder.build_index(records, index_dir)

    retriever = ToolmarkRetriever(index_dir, similarity_threshold=0.10, encoder=builder.encoder, device="cpu")

    queries = [
        {"image_path": records[0]["image_path"], "ground_truth_class": "type_0"},
        {"image_path": records[1]["image_path"], "ground_truth_class": "type_1"},
    ]

    rep_path = tmp_path / "retrieval_report.json"
    eval_result = evaluate_toolmark_retrieval(
        retriever=retriever,
        query_samples=queries,
        output_report_path=rep_path,
        working_dir=tmp_path / "working_eval",
        top_k_eval=2,
    )

    assert rep_path.exists()
    assert "recall_at_1" in eval_result["metrics"]
    assert "mAP" in eval_result["metrics"]
    assert eval_result["metrics"]["recall_at_1"] == 1.0
