#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from ask_chunks import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_CANDIDATE_K,
    DEFAULT_CHUNKS,
    DEFAULT_COLLECTION,
    DEFAULT_DB,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MODE,
    DEFAULT_MODEL,
    DEFAULT_RRF_K,
    DEFAULT_TABLE_BOOST,
    DEFAULT_TOKEN_PARAM,
    DEFAULT_TOP_K,
    bm25_table_boost_search,
    build_context_and_sources,
    build_run_record,
    build_source_records,
    build_user_prompt,
    bm25_search,
    call_openai_compatible,
    load_chunks,
    rrf_fuse,
    tokenize,
    vector_search,
    write_jsonl_record,
)


def load_eval_questions(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        questions = json.load(f)
    if not isinstance(questions, list):
        raise ValueError(f"Eval file must contain a JSON list: {path}")
    for item in questions:
        if "question" not in item:
            raise ValueError(f"Eval item missing question: {item}")
    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Run grounded answer generation over an eval JSON file.")
    parser.add_argument("--eval", required=True, help="Path to eval JSON file.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of questions to run.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name.")
    parser.add_argument("--chunks", default=DEFAULT_CHUNKS, help="Path to chunks JSONL.")
    parser.add_argument(
        "--mode",
        choices=["vector", "bm25", "hybrid", "bm25_table_boost"],
        default=DEFAULT_MODE,
        help="Retrieval mode.",
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Top results.")
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K, help="Hybrid candidate count.")
    parser.add_argument("--rrf-k", type=int, default=DEFAULT_RRF_K, help="RRF k value.")
    parser.add_argument(
        "--table-boost",
        type=float,
        default=DEFAULT_TABLE_BOOST,
        help="BM25 score multiplier for table_row_group chunks in bm25_table_boost mode.",
    )
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL, help="Embedding model.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Answer model.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible base URL.")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV, help="API key env var name.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max output tokens.")
    parser.add_argument(
        "--token-param",
        choices=["max_completion_tokens", "max_tokens"],
        default=DEFAULT_TOKEN_PARAM,
        help="Token limit payload field sent to the chat completions endpoint.",
    )
    parser.add_argument("--temperature", type=float, default=None, help="Optional model temperature.")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="HTTP timeout in seconds.")
    parser.add_argument("--output-jsonl", required=True, help="JSONL output path.")
    parser.add_argument("--dry-run", action="store_true", help="Do not call the model endpoint.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing JSONL output file.")
    parser.add_argument("--append", action="store_true", help="Append to an existing JSONL output file.")
    args = parser.parse_args()

    questions = load_eval_questions(Path(args.eval))
    if args.limit is not None:
        if args.limit < 1:
            print("ERROR: --limit must be >= 1")
            return 1
        questions = questions[: args.limit]

    rows_out = Path(args.output_jsonl)
    if args.overwrite and args.append:
        print("ERROR: --overwrite and --append cannot be used together.")
        return 1

    if rows_out.exists():
        if args.overwrite:
            rows_out.unlink()
        elif args.append:
            pass
        else:
            print(f"ERROR: Output file already exists: {rows_out}")
            print("Use --overwrite to replace it, or --append to add records to the existing file.")
            return 1

    if args.mode in {"vector", "hybrid"} and not Path(args.db).is_dir():
        print(f"ERROR: Chroma directory not found: {args.db}")
        return 1

    api_key = ""
    if not args.dry_run:
        api_key = os.getenv(args.api_key_env, "").strip()
        if not api_key:
            print(f"ERROR: Missing API key. Set environment variable: {args.api_key_env}")
            print("Tip: use --dry-run to test retrieval and prompt construction.")
            return 1

    chunks: list[dict[str, Any]] = []
    bm25 = None
    if args.mode in {"bm25", "hybrid", "bm25_table_boost"}:
        chunks = load_chunks(Path(args.chunks))
        bm25 = BM25Okapi([tokenize(str(chunk.get("text", ""))) for chunk in chunks])

    collection = None
    embedding_model = None
    if args.mode in {"vector", "hybrid"}:
        print(f"Loading embedding model: {args.embedding_model}")
        embedding_model = SentenceTransformer(args.embedding_model)
        client = chromadb.PersistentClient(
            path=str(args.db),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name=args.collection)

    print(f"Eval file: {args.eval}")
    print(f"Questions: {len(questions)}")
    print(f"Mode: {args.mode}")
    print(f"Output: {args.output_jsonl}")
    print()

    for index, item in enumerate(questions, start=1):
        question = str(item["question"])
        print(f"[{index}/{len(questions)}] {item.get('id', 'question')}: {question}")

        if args.mode == "vector":
            if collection is None or embedding_model is None:
                print("ERROR: Vector mode requires Chroma collection and embedding model.")
                return 1
            retrieved = vector_search(
                collection=collection,
                model=embedding_model,
                query=question,
                top_k=args.top_k,
            )
        elif args.mode == "bm25":
            if bm25 is None:
                print("ERROR: BM25 mode requires chunks index.")
                return 1
            retrieved = bm25_search(bm25=bm25, chunks=chunks, query=question, top_k=args.top_k)
        elif args.mode == "bm25_table_boost":
            if bm25 is None:
                print("ERROR: bm25_table_boost mode requires chunks index.")
                return 1
            retrieved, _table_like_query = bm25_table_boost_search(
                bm25=bm25,
                chunks=chunks,
                query=question,
                top_k=args.top_k,
                boost=args.table_boost,
            )
        else:
            if collection is None or embedding_model is None or bm25 is None:
                print("ERROR: Hybrid mode requires vector and BM25 retrieval.")
                return 1
            vector_rows = vector_search(
                collection=collection,
                model=embedding_model,
                query=question,
                top_k=args.candidate_k,
            )
            bm25_rows = bm25_search(
                bm25=bm25,
                chunks=chunks,
                query=question,
                top_k=args.candidate_k,
            )
            retrieved = rrf_fuse(vector_rows, bm25_rows, args.top_k, args.rrf_k)

        context, _source_lines = build_context_and_sources(retrieved)
        sources = build_source_records(retrieved)
        answer = None
        if not args.dry_run:
            try:
                answer = call_openai_compatible(
                    base_url=args.base_url,
                    model=args.model,
                    api_key=api_key,
                    user_prompt=build_user_prompt(question, context),
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    token_param=args.token_param,
                    timeout_seconds=args.timeout_seconds,
                )
            except RuntimeError as exc:
                print(f"ERROR: {exc}")
                return 1

        write_jsonl_record(
            rows_out,
            build_run_record(
                question=question,
                model=args.model,
                base_url=args.base_url,
                mode=args.mode,
                top_k=args.top_k,
                candidate_k=args.candidate_k,
                rrf_k=args.rrf_k,
                embedding_model=args.embedding_model,
                collection=args.collection,
                chunks=args.chunks,
                sources=sources,
                answer=answer,
                dry_run=args.dry_run,
                token_param=args.token_param,
            ),
        )

    print()
    print(f"Wrote {len(questions)} JSONL records: {args.output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
