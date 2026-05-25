#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_RRF_K = 60


def preview_text(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    if not isinstance(questions, list):
        raise ValueError(f"Eval file must contain a JSON list: {path}")

    for item in questions:
        if "id" not in item or "question" not in item or "expected_pages" not in item:
            raise ValueError(f"Invalid eval item: {item}")
        if not item["expected_pages"]:
            raise ValueError(f"Eval item has no expected pages: {item['id']}")

    return questions


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc
    if not chunks:
        raise ValueError(f"No chunks found in: {path}")
    return chunks


def safe_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(chunk.get("source", "")),
        "page_start": int(chunk.get("page_start", -1)),
        "page_end": int(chunk.get("page_end", -1)),
        "chunk_index": int(chunk.get("chunk_index", -1)),
        "page_chunk_index": int(chunk.get("page_chunk_index", -1)),
        "token_count": int(chunk.get("token_count", -1)),
    }


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def page_hit(meta: dict[str, Any], expected_pages: set[int]) -> bool:
    page_start = int(meta.get("page_start", -1))
    page_end = int(meta.get("page_end", page_start))
    return any(page_start <= page <= page_end for page in expected_pages)


def vector_search(
    *,
    collection: Any,
    model: SentenceTransformer,
    query: str,
    top_k: int,
    include_documents: bool,
) -> list[dict[str, Any]]:
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    include = ["metadatas", "distances"]
    if include_documents:
        include.append("documents")

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=include,
    )

    metas = results["metadatas"][0]
    distances = results["distances"][0]
    result_documents = results.get("documents")
    documents = result_documents[0] if result_documents else []

    rows = []
    for rank, (meta, distance) in enumerate(zip(metas, distances), start=1):
        document = documents[rank - 1] if rank - 1 < len(documents) else ""
        rows.append(
            {
                "key": int(meta.get("chunk_index", rank - 1)),
                "meta": meta,
                "distance": float(distance),
                "document": document,
                "vector_rank": rank,
            }
        )
    return rows


def bm25_search(
    *,
    bm25: BM25Okapi,
    chunks: list[dict[str, Any]],
    query: str,
    top_k: int,
    include_documents: bool,
) -> list[dict[str, Any]]:
    scores = bm25.get_scores(tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    rows = []
    for rank, index in enumerate(ranked_indices, start=1):
        chunk = chunks[index]
        rows.append(
            {
                "key": int(chunk.get("chunk_index", index)),
                "meta": safe_metadata(chunk),
                "distance": -float(scores[index]),
                "bm25_score": float(scores[index]),
                "document": str(chunk.get("text", "")) if include_documents else "",
                "bm25_rank": rank,
            }
        )
    return rows


def rrf_fuse(
    vector_rows: list[dict[str, Any]],
    bm25_rows: list[dict[str, Any]],
    top_k: int,
    rrf_k: int,
) -> list[dict[str, Any]]:
    fused: dict[int, dict[str, Any]] = {}

    for source_name, rows in (("vector", vector_rows), ("bm25", bm25_rows)):
        for rank, row in enumerate(rows, start=1):
            key = int(row["key"])
            if key not in fused:
                fused[key] = dict(row)
                fused[key]["rrf_score"] = 0.0
                fused[key]["sources"] = []
            fused[key]["rrf_score"] += 1.0 / (rrf_k + rank)
            fused[key]["sources"].append(source_name)
            if source_name == "vector":
                fused[key]["vector_rank"] = rank
            else:
                fused[key]["bm25_rank"] = rank

    ranked = sorted(fused.values(), key=lambda row: row["rrf_score"], reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["distance"] = -row["rrf_score"]
        row["hybrid_rank"] = rank
    return ranked[:top_k]


def bm25_first_fuse(
    vector_rows: list[dict[str, Any]],
    bm25_rows: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    fused: list[dict[str, Any]] = []
    seen_keys: set[int] = set()

    for source_name, rows in (("bm25", bm25_rows), ("vector", vector_rows)):
        for row in rows:
            key = int(row["key"])
            if key in seen_keys:
                continue
            merged = dict(row)
            seen_keys.add(key)
            if source_name == "bm25":
                merged["bm25_first_rank"] = len(fused) + 1
            else:
                merged["vector_fill_rank"] = len(fused) + 1
            fused.append(merged)
            if len(fused) >= top_k:
                return fused

    return fused


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval hit@k over a Chroma collection.")
    parser.add_argument(
        "--eval",
        default="eval/boot_bmhd_eval.json",
        help="Path to retrieval eval JSON file.",
    )
    parser.add_argument("--db", default="vector_db/chroma", help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default="technical_docs", help="Chroma collection name.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="SentenceTransformer model name. Must match embed_chunks.py.",
    )
    parser.add_argument(
        "--chunks",
        default="data/chunks.jsonl",
        help="Path to chunks JSONL file used for BM25/hybrid modes.",
    )
    parser.add_argument(
        "--mode",
        choices=["vector", "bm25", "hybrid", "bm25_first_hybrid"],
        default="vector",
        help="Retrieval mode to evaluate.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve.")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=10,
        help="Candidate count per retriever before hybrid fusion.",
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        default=DEFAULT_RRF_K,
        help=f"Reciprocal Rank Fusion k value. Default: {DEFAULT_RRF_K}",
    )
    parser.add_argument(
        "--fail-under-hit3",
        type=float,
        default=None,
        help="Optional hit@3 threshold between 0 and 1 that makes the command fail if not met.",
    )
    parser.add_argument(
        "--debug-failures",
        action="store_true",
        help="Print retrieved snippets for questions that miss hit@3.",
    )
    parser.add_argument(
        "--debug-snippet-chars",
        type=int,
        default=500,
        help="Snippet length used with --debug-failures.",
    )
    args = parser.parse_args()

    questions = load_questions(Path(args.eval))

    collection = None
    model = None
    if args.mode in {"vector", "hybrid", "bm25_first_hybrid"}:
        db_path = Path(args.db)
        if not db_path.exists():
            raise FileNotFoundError(f"Chroma DB not found: {db_path}. Run embed_chunks.py first.")

        print(f"Loading embedding model: {args.model}")
        model = SentenceTransformer(args.model)

        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name=args.collection)

    chunks: list[dict[str, Any]] = []
    bm25 = None
    if args.mode in {"bm25", "hybrid", "bm25_first_hybrid"}:
        chunks = load_chunks(Path(args.chunks))
        bm25 = BM25Okapi([tokenize(str(chunk.get("text", ""))) for chunk in chunks])

    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_k = 0

    print()
    print(f"Eval file: {args.eval}")
    print(f"Questions: {len(questions)}")
    print(f"Mode: {args.mode}")
    print(f"Top-k: {args.top_k}")
    if args.mode in {"hybrid", "bm25_first_hybrid"}:
        print(f"Candidate-k: {args.candidate_k}")
        if args.mode == "hybrid":
            print(f"RRF-k: {args.rrf_k}")
    print("=" * 120)

    for item in questions:
        expected_pages = {int(page) for page in item["expected_pages"]}
        include_documents = args.debug_failures

        if args.mode == "vector":
            if collection is None or model is None:
                raise RuntimeError("Vector mode requires an initialized Chroma collection and embedding model.")
            rows = vector_search(
                collection=collection,
                model=model,
                query=item["question"],
                top_k=args.top_k,
                include_documents=include_documents,
            )
        elif args.mode == "bm25":
            if bm25 is None:
                raise RuntimeError("BM25 mode requires an initialized BM25 index.")
            rows = bm25_search(
                bm25=bm25,
                chunks=chunks,
                query=item["question"],
                top_k=args.top_k,
                include_documents=include_documents,
            )
        else:
            if collection is None or model is None or bm25 is None:
                raise RuntimeError("Hybrid modes require vector and BM25 retrievers.")
            vector_rows = vector_search(
                collection=collection,
                model=model,
                query=item["question"],
                top_k=args.candidate_k,
                include_documents=include_documents,
            )
            bm25_rows = bm25_search(
                bm25=bm25,
                chunks=chunks,
                query=item["question"],
                top_k=args.candidate_k,
                include_documents=include_documents,
            )
            if args.mode == "hybrid":
                rows = rrf_fuse(vector_rows, bm25_rows, args.top_k, args.rrf_k)
            else:
                rows = bm25_first_fuse(vector_rows, bm25_rows, args.top_k)

        metas = [row["meta"] for row in rows]
        distances = [row["distance"] for row in rows]
        top_pages = [f"{m.get('page_start')}-{m.get('page_end')}" for m in metas]

        this_hit_at_1 = bool(metas) and page_hit(metas[0], expected_pages)
        this_hit_at_3 = any(page_hit(meta, expected_pages) for meta in metas[:3])
        this_hit_at_k = any(page_hit(meta, expected_pages) for meta in metas)

        hit_at_1 += int(this_hit_at_1)
        hit_at_3 += int(this_hit_at_3)
        hit_at_k += int(this_hit_at_k)

        status = "PASS" if this_hit_at_3 else "FAIL"
        distance_text = ", ".join(f"{distance:.4f}" for distance in distances[:3])

        print(f"{item['id']} {status}")
        print(f"  question: {item['question']}")
        print(f"  expected: {sorted(expected_pages)}")
        print(f"  top_pages: {top_pages}")
        print(f"  top_distances: {distance_text}")
        if item.get("notes"):
            print(f"  notes: {item['notes']}")

        if args.debug_failures and not this_hit_at_3:
            print("  debug_results:")
            for rank, row in enumerate(rows, start=1):
                meta = row["meta"]
                distance = row["distance"]
                rank_bits = []
                if "vector_rank" in row:
                    rank_bits.append(f"vector_rank={row['vector_rank']}")
                if "bm25_rank" in row:
                    rank_bits.append(f"bm25_rank={row['bm25_rank']}")
                if "bm25_first_rank" in row:
                    rank_bits.append(f"bm25_first_rank={row['bm25_first_rank']}")
                if "vector_fill_rank" in row:
                    rank_bits.append(f"vector_fill_rank={row['vector_fill_rank']}")
                rank_text = f" {' '.join(rank_bits)}" if rank_bits else ""
                print(
                    f"    {rank}. distance={distance:.4f} "
                    f"page={meta.get('page_start')}-{meta.get('page_end')} "
                    f"chunk={meta.get('chunk_index')}{rank_text}"
                )
                print(f"       {preview_text(str(row.get('document', '')), args.debug_snippet_chars)}")
        print()

    total = len(questions)
    print("=" * 120)
    print(f"hit@1: {hit_at_1}/{total} = {hit_at_1 / total:.2%}")
    print(f"hit@3: {hit_at_3}/{total} = {hit_at_3 / total:.2%}")
    print(f"hit@{args.top_k}: {hit_at_k}/{total} = {hit_at_k / total:.2%}")

    hit_at_3_ratio = hit_at_3 / total
    if args.fail_under_hit3 is not None and hit_at_3_ratio < args.fail_under_hit3:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
