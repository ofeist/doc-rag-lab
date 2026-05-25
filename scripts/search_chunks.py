#!/usr/bin/env python3

import argparse
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def preview_text(text: str, max_chars: int = 700) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic search over local ChromaDB chunks.")
    parser.add_argument("query", help="Search query, for example: 'pin configuration analog input'")
    parser.add_argument("--db", default="vector_db/chroma", help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default="technical_docs", help="Chroma collection name.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="SentenceTransformer model name. Must match embed_chunks.py.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    args = parser.parse_args()

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

    query_embedding = model.encode(
        [args.query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    print()
    print(f"Top {len(docs)} results for: {args.query}")
    print("=" * 100)

    for i, (doc, meta, distance) in enumerate(zip(docs, metas, distances), start=1):
        print()
        print(
            f"[{i}] distance={distance:.4f} | "
            f"page={meta.get('page_start')}-{meta.get('page_end')} | "
            f"chunk={meta.get('chunk_index')} | "
            f"tokens={meta.get('token_count')} | "
            f"source={meta.get('source')}"
        )
        print("-" * 100)
        print(preview_text(doc))
        print("-" * 100)


if __name__ == "__main__":
    main()
