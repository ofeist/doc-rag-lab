#!/usr/bin/env python3

import argparse
import json
from datetime import datetime, timezone
import os
import re
from pathlib import Path
from typing import Any

import chromadb
import requests
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DB = "vector_db/chroma"
DEFAULT_COLLECTION = "technical_docs"
DEFAULT_CHUNKS = "data/chunks.jsonl"
DEFAULT_MODE = "hybrid"
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 10
DEFAULT_RRF_K = 60
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_TOKEN_PARAM = "max_completion_tokens"

SYSTEM_PROMPT = """You are a technical documentation assistant.
Answer only using the provided context.
If the provided context is not sufficient, say: "The provided context is not sufficient to answer this question."
Do not use outside knowledge.
Always cite sources using the provided source ids like [S1], [S2].
Keep the answer concise and technical."""


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                chunks.append(json.loads(stripped))
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


def vector_search(
    *,
    collection: Any,
    model: SentenceTransformer,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    metas = results["metadatas"][0]
    distances = results["distances"][0]
    documents = results["documents"][0]

    rows: list[dict[str, Any]] = []
    for rank, (meta, distance, document) in enumerate(zip(metas, distances, documents), start=1):
        rows.append(
            {
                "key": int(meta.get("chunk_index", rank - 1)),
                "meta": meta,
                "distance": float(distance),
                "document": str(document),
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
) -> list[dict[str, Any]]:
    scores = bm25.get_scores(tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    rows: list[dict[str, Any]] = []
    for rank, index in enumerate(ranked_indices, start=1):
        chunk = chunks[index]
        rows.append(
            {
                "key": int(chunk.get("chunk_index", index)),
                "meta": safe_metadata(chunk),
                "distance": -float(scores[index]),
                "bm25_score": float(scores[index]),
                "document": str(chunk.get("text", "")),
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
            else:
                for field in ("document", "meta", "bm25_score"):
                    if field in row and fused[key].get(field) is None:
                        fused[key][field] = row[field]
            fused[key]["rrf_score"] += 1.0 / (rrf_k + rank)
            if source_name == "vector":
                fused[key]["vector_rank"] = rank
            else:
                fused[key]["bm25_rank"] = rank
                if "bm25_score" in row:
                    fused[key]["bm25_score"] = row["bm25_score"]

    ranked = sorted(fused.values(), key=lambda row: row["rrf_score"], reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["distance"] = -row["rrf_score"]
        row["hybrid_rank"] = rank
    return ranked[:top_k]


def build_context_and_sources(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    blocks: list[str] = []
    source_lines: list[str] = []
    for idx, row in enumerate(rows, start=1):
        meta = row["meta"]
        sid = f"S{idx}"
        source = str(meta.get("source", "unknown"))
        page_start = int(meta.get("page_start", -1))
        page_end = int(meta.get("page_end", page_start))
        chunk_index = int(meta.get("chunk_index", -1))
        score = row.get("distance", 0.0)
        source_lines.append(
            f"[{sid}] pages {page_start}-{page_end} chunk={chunk_index} score={score:.4f}"
        )
        blocks.append(
            f"[{sid}]\n"
            f"source: {source}\n"
            f"pages: {page_start}-{page_end}\n"
            f"chunk_id: {chunk_index}\n"
            f"text:\n{row.get('document', '')}\n"
        )
    return "\n".join(blocks), source_lines


def build_source_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        meta = row["meta"]
        records.append(
            {
                "id": f"S{idx}",
                "source": str(meta.get("source", "unknown")),
                "page_start": int(meta.get("page_start", -1)),
                "page_end": int(meta.get("page_end", meta.get("page_start", -1))),
                "chunk_index": int(meta.get("chunk_index", -1)),
                "score": float(row.get("distance", 0.0)),
                "vector_rank": row.get("vector_rank"),
                "bm25_rank": row.get("bm25_rank"),
                "hybrid_rank": row.get("hybrid_rank"),
                "bm25_score": row.get("bm25_score"),
            }
        )
    return records


def write_jsonl_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_run_record(
    *,
    question: str,
    model: str,
    base_url: str,
    mode: str,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
    embedding_model: str,
    collection: str,
    chunks: str,
    sources: list[dict[str, Any]],
    answer: str | None,
    dry_run: bool,
    token_param: str,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "model": model,
        "base_url": base_url,
        "mode": mode,
        "top_k": top_k,
        "candidate_k": candidate_k,
        "rrf_k": rrf_k,
        "embedding_model": embedding_model,
        "collection": collection,
        "chunks": chunks,
        "sources": sources,
        "answer": answer,
        "dry_run": dry_run,
        "token_param": token_param,
    }


def build_user_prompt(question: str, context: str) -> str:
    return (
        "Question:\n"
        f"{question}\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Answer requirements:\n"
        "- Answer only from the context above.\n"
        "- Include citations like [S1] or [S2].\n"
        "- If the context is insufficient, say so explicitly.\n"
    )


def call_openai_compatible(
    *,
    base_url: str,
    model: str,
    api_key: str,
    user_prompt: str,
    temperature: float | None,
    max_tokens: int,
    token_param: str,
    timeout_seconds: int,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        token_param: max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise RuntimeError(f"Connection error: {exc}. Use --dry-run to verify retrieval/prompt.")

    if response.status_code >= 400:
        raise RuntimeError(
            f"Model endpoint error HTTP {response.status_code}: {response.text}. "
            "Use --dry-run to verify retrieval/prompt."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Malformed JSON response from model endpoint.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Model response missing choices[0].message.content.") from exc

    if not content:
        raise RuntimeError("Model returned an empty answer.")
    return str(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="First grounded RAG answer slice (CLI).")
    parser.add_argument("--question", required=True, help="User question.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name.")
    parser.add_argument("--chunks", default=DEFAULT_CHUNKS, help="Path to chunks JSONL.")
    parser.add_argument(
        "--mode",
        choices=["vector", "bm25", "hybrid"],
        default=DEFAULT_MODE,
        help="Retrieval mode.",
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Top results.")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=DEFAULT_CANDIDATE_K,
        help="Candidate count per retriever before hybrid fusion.",
    )
    parser.add_argument("--rrf-k", type=int, default=DEFAULT_RRF_K, help="RRF k value.")
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="Embedding model used for vector retrieval.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible base URL.")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV, help="API key env var name.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max output tokens.")
    parser.add_argument(
        "--token-param",
        choices=["max_completion_tokens", "max_tokens"],
        default=DEFAULT_TOKEN_PARAM,
        help="Token limit payload field sent to the chat completions endpoint.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not call model endpoint.")
    parser.add_argument("--show-context", action="store_true", help="Print full retrieved context.")
    parser.add_argument(
        "--output-jsonl",
        help="Optional JSONL file to append one structured run record.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional model temperature. If omitted, endpoint default is used.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.mode in {"vector", "hybrid"} and not db_path.is_dir():
        print(f"ERROR: Chroma directory not found: {db_path}")
        print("Run scripts/embed_chunks.py first.")
        return 1

    chunks: list[dict[str, Any]] = []
    bm25 = None
    if args.mode in {"bm25", "hybrid"}:
        chunks_path = Path(args.chunks)
        if not chunks_path.exists():
            print(f"ERROR: chunks file not found: {chunks_path}")
            return 1
        chunks = load_chunks(chunks_path)
        bm25 = BM25Okapi([tokenize(str(chunk.get("text", ""))) for chunk in chunks])

    collection = None
    model = None
    if args.mode in {"vector", "hybrid"}:
        print(f"Loading embedding model: {args.embedding_model}")
        model = SentenceTransformer(args.embedding_model)
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        try:
            collection = client.get_collection(name=args.collection)
        except Exception as exc:
            print(f"ERROR: Could not open Chroma collection '{args.collection}': {exc}")
            return 1

    if args.mode == "vector":
        if collection is None or model is None:
            print("ERROR: Vector mode requires Chroma collection and embedding model.")
            return 1
        rows = vector_search(collection=collection, model=model, query=args.question, top_k=args.top_k)
    elif args.mode == "bm25":
        if bm25 is None:
            print("ERROR: BM25 mode requires chunks index.")
            return 1
        rows = bm25_search(bm25=bm25, chunks=chunks, query=args.question, top_k=args.top_k)
    else:
        if collection is None or model is None or bm25 is None:
            print("ERROR: Hybrid mode requires both vector and BM25 retrieval.")
            return 1
        vector_rows = vector_search(
            collection=collection,
            model=model,
            query=args.question,
            top_k=args.candidate_k,
        )
        bm25_rows = bm25_search(
            bm25=bm25,
            chunks=chunks,
            query=args.question,
            top_k=args.candidate_k,
        )
        rows = rrf_fuse(vector_rows, bm25_rows, args.top_k, args.rrf_k)

    context, source_lines = build_context_and_sources(rows)
    source_records = build_source_records(rows)
    user_prompt = build_user_prompt(args.question, context)

    print("Question:")
    print(args.question)
    print()
    print("Retrieval:")
    print(f"mode: {args.mode}")
    print(f"top_k: {args.top_k}")
    if args.mode == "hybrid":
        print(f"candidate_k: {args.candidate_k}")
        print(f"rrf_k: {args.rrf_k}")
    print()
    print("Sources:")
    for line in source_lines:
        print(line)

    if args.show_context:
        print()
        print("Context:")
        print(context)

    if args.dry_run:
        print()
        print("DRY RUN - no model call performed")
        print()
        print("Prompt:")
        print("SYSTEM:")
        print(SYSTEM_PROMPT)
        print()
        print("USER:")
        print(user_prompt)
        if args.output_jsonl:
            write_jsonl_record(
                Path(args.output_jsonl),
                build_run_record(
                    question=args.question,
                    model=args.model,
                    base_url=args.base_url,
                    mode=args.mode,
                    top_k=args.top_k,
                    candidate_k=args.candidate_k,
                    rrf_k=args.rrf_k,
                    embedding_model=args.embedding_model,
                    collection=args.collection,
                    chunks=args.chunks,
                    sources=source_records,
                    answer=None,
                    dry_run=True,
                    token_param=args.token_param,
                ),
            )
            print()
            print(f"Wrote JSONL record: {args.output_jsonl}")
        return 0

    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        print(f"ERROR: Missing API key. Set environment variable: {args.api_key_env}")
        print("Tip: use --dry-run to test retrieval and prompt without model call.")
        return 1

    try:
        answer = call_openai_compatible(
            base_url=args.base_url,
            model=args.model,
            api_key=api_key,
            user_prompt=user_prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            token_param=args.token_param,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    print()
    print("Answer:")
    print(answer)

    if args.output_jsonl:
        write_jsonl_record(
            Path(args.output_jsonl),
            build_run_record(
                question=args.question,
                model=args.model,
                base_url=args.base_url,
                mode=args.mode,
                top_k=args.top_k,
                candidate_k=args.candidate_k,
                rrf_k=args.rrf_k,
                embedding_model=args.embedding_model,
                collection=args.collection,
                chunks=args.chunks,
                sources=source_records,
                answer=answer,
                dry_run=False,
                token_param=args.token_param,
            ),
        )
        print()
        print(f"Wrote JSONL record: {args.output_jsonl}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
