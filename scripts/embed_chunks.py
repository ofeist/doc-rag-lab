#!/usr/bin/env python3

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterator

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

SAFE_METADATA_FIELDS = [
    "doc_id",
    "source",
    "page_start",
    "page_end",
    "chunk_index",
    "page_chunk_index",
    "token_count",
    "chunk_type",
    "section_title",
    "table_title",
    "table_context",
    "row_count",
]


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc


def is_chroma_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def safe_metadata(chunk: dict) -> dict:
    metadata = {
        "doc_id": str(chunk.get("doc_id", "")),
        "source": str(chunk.get("source", "")),
        "page_start": int(chunk.get("page_start", -1)),
        "page_end": int(chunk.get("page_end", -1)),
        "chunk_index": int(chunk.get("chunk_index", -1)),
        "page_chunk_index": int(chunk.get("page_chunk_index", -1)),
        "token_count": int(chunk.get("token_count", -1)),
    }

    for field in SAFE_METADATA_FIELDS:
        if field in metadata or field not in chunk:
            continue
        value = chunk[field]
        if is_chroma_scalar(value):
            metadata[field] = value

    return metadata


def build_chunk_id(chunk: dict) -> str:
    source = str(chunk.get("source", "source")).replace("\\", "/")
    source_name = Path(source).stem or "source"
    chunk_index = int(chunk.get("chunk_index", -1))
    page_start = int(chunk.get("page_start", -1))
    page_chunk_index = int(chunk.get("page_chunk_index", -1))
    return f"{source_name}-p{page_start:05d}-c{page_chunk_index:03d}-g{chunk_index:06d}"


def embed_chunks(
    chunks_path: Path,
    db_path: Path,
    collection_name: str,
    model_name: str,
    batch_size: int,
    reset: bool = False,
) -> int:
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

    if reset and db_path.exists():
        print(f"Resetting existing DB: {db_path}")
        shutil.rmtree(db_path)

    db_path.mkdir(parents=True, exist_ok=True)

    print(f"Reading chunks from: {chunks_path}")
    chunks = list(read_jsonl(chunks_path))
    if not chunks:
        raise ValueError(f"No chunks found in: {chunks_path}")

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    skipped = 0

    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            skipped += 1
            continue
        documents.append(text)
        metadatas.append(safe_metadata(chunk))
        ids.append(build_chunk_id(chunk))

    if not documents:
        raise ValueError("No non-empty chunk text found.")

    print(f"Chunks loaded: {len(chunks)}")
    print(f"Chunks skipped because empty: {skipped}")
    print(f"Chunks to embed: {len(documents)}")
    print(f"Loading embedding model: {model_name}")

    model = SentenceTransformer(model_name)

    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"Writing to Chroma collection: {collection_name}")
    print(f"DB path: {db_path}")

    for start in tqdm(range(0, len(documents), batch_size), desc="Embedding"):
        end = start + batch_size
        batch_docs = documents[start:end]
        embeddings = model.encode(
            batch_docs,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=ids[start:end],
            documents=batch_docs,
            metadatas=metadatas[start:end],
            embeddings=embeddings,
        )

    print()
    print("Done.")
    print(f"Collection count: {collection.count()}")
    print('Next test: python scripts/search_chunks.py "your search question here"')
    return collection.count()


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed chunks.jsonl into local ChromaDB.")
    parser.add_argument("--chunks", default="data/chunks.jsonl", help="Path to chunks JSONL file.")
    parser.add_argument("--db", default="vector_db/chroma", help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default="technical_docs", help="Chroma collection name.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="SentenceTransformer model name.")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB directory before embedding.",
    )
    args = parser.parse_args()

    embed_chunks(
        chunks_path=Path(args.chunks),
        db_path=Path(args.db),
        collection_name=args.collection,
        model_name=args.model,
        batch_size=args.batch_size,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
