"""
Command-Line Interface for Module 4: Bullet & Toolmark Visual Similarity Retrieval
"""

import argparse
import json
from pathlib import Path

from src.toolmark_research.index import ToolmarkIndexBuilder
from src.toolmark_research.retrieve import ToolmarkRetriever
from src.toolmark_research.evaluate import evaluate_toolmark_retrieval


def main():
    parser = argparse.ArgumentParser(
        description="Module 4: Laboratory Toolmark Image Similarity Retrieval (Research Protocol Only)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Index
    idx_p = subparsers.add_parser("index", help="Index reference laboratory images")
    idx_p.add_argument("--manifest", type=str, required=True, help="JSON file with list of reference image records")
    idx_p.add_argument("--output-dir", type=str, default="data/indices/toolmark", help="Output directory for index")

    # 2. Retrieve
    ret_p = subparsers.add_parser("retrieve", help="Retrieve top-K visually similar lab reference images")
    ret_p.add_argument("--index-dir", type=str, required=True, help="Path to built gallery index directory")
    ret_p.add_argument("--query-image", type=str, required=True, help="Path to query image")
    ret_p.add_argument("--top-k", type=int, default=5, help="Number of top candidates to retrieve")
    ret_p.add_argument("--working-dir", type=str, default="data/working_copies/toolmarks", help="Working copy directory")
    ret_p.add_argument("--similarity-thresh", type=float, default=0.45, help="Minimum similarity threshold")

    # 3. Evaluate
    eval_p = subparsers.add_parser("evaluate", help="Evaluate retrieval with Recall@K and mAP on labeled test set")
    eval_p.add_argument("--index-dir", type=str, required=True)
    eval_p.add_argument("--test-manifest", type=str, required=True)
    eval_p.add_argument("--output-report", type=str, default="data/evaluation/toolmark_retrieval_eval.json")
    eval_p.add_argument("--working-dir", type=str, default="data/working_copies/toolmarks")

    args = parser.parse_args()

    if args.command == "index":
        with open(args.manifest, "r", encoding="utf-8") as f:
            records = json.load(f)
        builder = ToolmarkIndexBuilder()
        out = builder.build_index(records, Path(args.output_dir))
        print(f"[+] Indexing completed. {out['total_indexed']} reference images indexed at: {args.output_dir}")

    elif args.command == "retrieve":
        retriever = ToolmarkRetriever(Path(args.index_dir), similarity_threshold=args.similarity_thresh)
        res = retriever.retrieve_similar(Path(args.query_image), working_dir=Path(args.working_dir), top_k=args.top_k)
        print(json.dumps(res, indent=2))

    elif args.command == "evaluate":
        with open(args.test_manifest, "r", encoding="utf-8") as f:
            queries = json.load(f)
        retriever = ToolmarkRetriever(Path(args.index_dir))
        eval_res = evaluate_toolmark_retrieval(retriever, queries, Path(args.output_report), Path(args.working_dir))
        print(json.dumps(eval_res, indent=2))


if __name__ == "__main__":
    main()
