#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import chromadb
import requests
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
DEFAULT_LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
DEFAULT_LLM_API_KEY = os.getenv("LLM_API_KEY", "")


SYSTEM_PROMPT = """You are a technical documentation assistant.

Rules:
- Use ONLY the provided documentation context.
- Do NOT answer from general knowledge.
- If the answer is not present in the context, say: "Not found in the provided documentation context."
- Keep the answer concise and technical.
- Always mention which sources support the answer.
- If the context is weak or incomplete, say so.
"""


def build_context(results: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    context_blocks = []
    source_debug = []

    for idx, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        source = meta.get("source", "unknown")
        page_start = meta.get("page_start", "unknown")
        page_end = meta.get("page_end", page_start)
        chunk_index = meta.get("chunk_index", "unknown")

        source_label = (
            f"S{idx}: source={source}, "
            f"page_start={page_start}, page_end={page_end}, chunk_index={chunk_index}"
        )
        context_blocks.append(f"[{source_label}]\n{doc}\n")
        source_debug.append(
            {
                "rank": idx,
                "source": source,
                "page_start": page_start,
                "page_end": page_end,
                "chunk_index": chunk_index,
                "distance": distance,
            }
        )

    return "\n---\n".join(context_blocks), source_debug


def call_llm(
    *,
    base_url: str,
    model: str,
    api_key: str,
    question: str,
    context: str,
    timeout_seconds: int,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    user_prompt = f"""Documentation context:

{context}

Question:
{question}

Answer format:

Answer:
...

Sources:
- ...

Limitations:
...
"""

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
    if response.status_code >= 400:
        raise RuntimeError(f"LLM request failed: HTTP {response.status_code}\n{response.text}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM response format:\n{data}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask a question using retrieved ChromaDB chunks and an OpenAI-compatible LLM."
    )
    parser.add_argument("question", help="Question to ask against the indexed documentation.")
    parser.add_argument("--db", default="vector_db/chroma", help="Persistent ChromaDB directory.")
    parser.add_argument("--chroma-dir", dest="db", help="Alias for --db.")
    parser.add_argument("--collection", default="technical_docs", help="Chroma collection name.")
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="SentenceTransformers embedding model. Must match embed_chunks.py.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve.")
    parser.add_argument(
        "--llm-base-url",
        default=DEFAULT_LLM_BASE_URL,
        help=f"OpenAI-compatible base URL. Default: {DEFAULT_LLM_BASE_URL}",
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_LLM_MODEL,
        help=f"LLM model name. Default: {DEFAULT_LLM_MODEL}",
    )
    parser.add_argument("--llm-api-key", default=DEFAULT_LLM_API_KEY, help="LLM API key.")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="LLM request timeout.")
    parser.add_argument("--show-context", action="store_true", help="Print retrieved context.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_dir():
        print(f"ERROR: Chroma directory not found: {db_path}", file=sys.stderr)
        print("Run scripts/embed_chunks.py first.", file=sys.stderr)
        return 1

    print(f"Loading embedding model: {args.embedding_model}")
    embedding_model = SentenceTransformer(args.embedding_model)

    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False),
    )

    try:
        collection = client.get_collection(name=args.collection)
    except Exception as exc:
        print(f"ERROR: Could not open Chroma collection '{args.collection}'.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    query_embedding = embedding_model.encode(
        [args.question],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    context, source_debug = build_context(results)

    print("\nQuestion:")
    print(args.question)

    print("\nRetrieved sources:")
    for item in source_debug:
        print(
            f"{item['rank']}. distance={item['distance']:.4f} "
            f"source={item['source']} "
            f"page={item['page_start']}-{item['page_end']} "
            f"chunk={item['chunk_index']}"
        )

    if args.show_context:
        print("\nRetrieved context:")
        print(context)

    try:
        answer = call_llm(
            base_url=args.llm_base_url,
            model=args.llm_model,
            api_key=args.llm_api_key,
            question=args.question,
            context=context,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:
        print("\nERROR while calling LLM:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print("\nAnswer:")
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
