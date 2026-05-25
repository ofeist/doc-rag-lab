# RAG PoC — Step 3: Embeddings + ChromaDB + Semantic Search

## Cilj

U Step 1 smo dobili:

```text
data/raw_pages.jsonl
```

U Step 2 smo dobili:

```text
data/chunks.jsonl
```

U Step 3 radimo:

```text
chunks.jsonl
  ↓
embedding model
  ↓
ChromaDB vector database
  ↓
semantic search
```

Još **ne koristimo LLM**.

Ovaj step mora dokazati:

> Kad postavim pitanje, sustav vraća relevantne chunkove i njihove stranice.

Ako ovo ne radi dobro, nema smisla ići na LLM jer će LLM samo lijepo upakirati loš retrieval.

---

## Što ćemo dobiti na kraju

Nakon ovog stepa imat ćemo:

```text
vector_db/chroma/
scripts/embed_chunks.py
scripts/search_chunks.py
```

I moći ćemo pokrenuti:

```bash
python scripts/search_chunks.py "pin configuration analog input"
```

Primjer outputa:

```text
Top 5 results for: pin configuration analog input

[1] distance=0.2187 | page=12 | chunk=17 | source=docs/infineon-manual.pdf
...
```

---

## Trenutna struktura projekta

Očekivano:

```text
test-rag/
  docs/
    infineon-manual.pdf

  data/
    raw_pages.jsonl
    chunks.jsonl

  scripts/
    extract_pages.py
    chunk_pages.py

  vector_db/
    # ChromaDB će se ovdje napraviti

  requirements.txt
```

Ako nemaš `vector_db/`, skripta će ga sama napraviti.

---

## 1. Update `requirements.txt`

Dodaj ove dependencyje:

```txt
chromadb
sentence-transformers
numpy
tqdm
```

Ako želiš imati kompletan `requirements.txt` za Step 1–3, može izgledati ovako:

```txt
pymupdf
tiktoken
chromadb
sentence-transformers
numpy
tqdm
```

Instalacija:

```bash
pip install -r requirements.txt
```

Prvi put će `sentence-transformers` skinuti model s Hugging Facea.

Za PoC koristimo mali model:

```text
BAAI/bge-small-en-v1.5
```

Zašto taj model?

- mali je;
- dovoljno brz na CPU-u;
- dovoljno dobar za prvi semantic-search PoC;
- tehnička dokumentacija je uglavnom na engleskom.

Kasnije možemo prijeći na `bge-m3`, ali za prvi loop ne treba odmah ići teško.

---

## 2. Skripta: `scripts/embed_chunks.py`

Ova skripta čita:

```text
data/chunks.jsonl
```

i puni ChromaDB bazu u:

```text
vector_db/chroma/
```

Kreiraj file:

```text
scripts/embed_chunks.py
```

Sadržaj:

```python
import argparse
import json
import shutil
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc


def safe_metadata(chunk: dict) -> dict:
    """
    Chroma metadata values must be simple scalar values:
    str, int, float, bool.

    We intentionally do not store the full text in metadata.
    The text goes into Chroma's document field.
    """
    return {
        "source": str(chunk.get("source", "")),
        "page_start": int(chunk.get("page_start", -1)),
        "page_end": int(chunk.get("page_end", -1)),
        "chunk_index": int(chunk.get("chunk_index", -1)),
        "page_chunk_index": int(chunk.get("page_chunk_index", -1)),
        "token_count": int(chunk.get("token_count", -1)),
    }


def build_chunk_id(chunk: dict) -> str:
    source = str(chunk.get("source", "source")).replace("\\", "/")
    source_name = Path(source).stem or "source"
    chunk_index = int(chunk.get("chunk_index", -1))
    page_start = int(chunk.get("page_start", -1))
    page_chunk_index = int(chunk.get("page_chunk_index", -1))

    return f"{source_name}-p{page_start:05d}-c{page_chunk_index:03d}-g{chunk_index:06d}"


def main():
    parser = argparse.ArgumentParser(
        description="Embed chunks.jsonl into local ChromaDB."
    )
    parser.add_argument(
        "--chunks",
        default="data/chunks.jsonl",
        help="Path to chunks JSONL file.",
    )
    parser.add_argument(
        "--db",
        default="vector_db/chroma",
        help="Path to persistent ChromaDB directory.",
    )
    parser.add_argument(
        "--collection",
        default="technical_docs",
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="SentenceTransformer model name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB directory before embedding.",
    )

    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    db_path = Path(args.db)

    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

    if args.reset and db_path.exists():
        print(f"Resetting existing DB: {db_path}")
        shutil.rmtree(db_path)

    db_path.mkdir(parents=True, exist_ok=True)

    print(f"Reading chunks from: {chunks_path}")
    chunks = list(read_jsonl(chunks_path))

    if not chunks:
        raise ValueError(f"No chunks found in: {chunks_path}")

    documents = []
    metadatas = []
    ids = []

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
    print(f"Loading embedding model: {args.model}")

    model = SentenceTransformer(args.model)

    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False),
    )

    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"Writing to Chroma collection: {args.collection}")
    print(f"DB path: {db_path}")

    for start in tqdm(range(0, len(documents), args.batch_size), desc="Embedding"):
        end = start + args.batch_size

        batch_docs = documents[start:end]
        batch_metas = metadatas[start:end]
        batch_ids = ids[start:end]

        embeddings = model.encode(
            batch_docs,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=embeddings,
        )

    print()
    print("Done.")
    print(f"Collection count: {collection.count()}")
    print()
    print("Next test:")
    print('python scripts/search_chunks.py "your search question here"')


if __name__ == "__main__":
    main()
```

---

## 3. Pokretanje embedding stepa

Prvi put pokreni s `--reset`:

```bash
python scripts/embed_chunks.py --reset
```

Ako želiš eksplicitno navesti file:

```bash
python scripts/embed_chunks.py --chunks data/chunks.jsonl --db vector_db/chroma --reset
```

Očekivani output:

```text
Reading chunks from: data/chunks.jsonl
Chunks loaded: 123
Chunks skipped because empty: 0
Chunks to embed: 123
Loading embedding model: BAAI/bge-small-en-v1.5
Writing to Chroma collection: technical_docs
Embedding: 100%
Done.
Collection count: 123
```

Prvi run može potrajati jer se model skida lokalno.

---

## 4. Skripta: `scripts/search_chunks.py`

Ova skripta radi semantic search nad ChromaDB.

Kreiraj file:

```text
scripts/search_chunks.py
```

Sadržaj:

```python
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


def main():
    parser = argparse.ArgumentParser(
        description="Semantic search over local ChromaDB chunks."
    )
    parser.add_argument(
        "query",
        help="Search query, for example: 'pin configuration analog input'",
    )
    parser.add_argument(
        "--db",
        default="vector_db/chroma",
        help="Path to persistent ChromaDB directory.",
    )
    parser.add_argument(
        "--collection",
        default="technical_docs",
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="SentenceTransformer model name. Must match embed_chunks.py.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return.",
    )

    args = parser.parse_args()

    db_path = Path(args.db)

    if not db_path.exists():
        raise FileNotFoundError(
            f"Chroma DB not found: {db_path}. Run embed_chunks.py first."
        )

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
        source = meta.get("source")
        page_start = meta.get("page_start")
        page_end = meta.get("page_end")
        chunk_index = meta.get("chunk_index")
        token_count = meta.get("token_count")

        print()
        print(
            f"[{i}] distance={distance:.4f} | "
            f"page={page_start}-{page_end} | "
            f"chunk={chunk_index} | "
            f"tokens={token_count} | "
            f"source={source}"
        )
        print("-" * 100)
        print(preview_text(doc))
        print("-" * 100)


if __name__ == "__main__":
    main()
```

---

## 5. Prvi search testovi

Pokreni nekoliko jednostavnih queryja.

Primjeri:

```bash
python scripts/search_chunks.py "pin configuration"
```

```bash
python scripts/search_chunks.py "analog input voltage"
```

```bash
python scripts/search_chunks.py "reset behavior"
```

```bash
python scripts/search_chunks.py "interrupt priority"
```

Za tvoj konkretni Infineon dokument koristi pojmove koje vidiš u PDF-u.

Ako dokument govori o pinovima, ADC-u, packageu ili electrical characteristics, koristi takve queryje.

---

## 6. Kako znati da Step 3 radi dobro?

Za sada ne tražimo savršenstvo.

Dovoljno je da:

1. search vraća tekstualno relevantne chunkove;
2. vraća page number;
3. top 1–3 rezultata često imaju smisla;
4. `source` metadata je ispravan;
5. nema errora;
6. rezultat nije potpuno random.

Dobar znak:

```text
Query: analog input voltage
Result: stranice gdje se stvarno spominje analog input, voltage, pin, ADC...
```

Loš znak:

```text
Query: analog input voltage
Result: table of contents, revision history, unrelated pages...
```

Ako top result često vraća Table of Contents, to nije katastrofa, ali ćemo kasnije dodati filtering ili bolji chunking.

---

## 7. Važna napomena o `distance`

Chroma vraća `distance`.

Kod cosine distance:

```text
manji broj = sličnije
veći broj = manje slično
```

Nemoj još previše gledati apsolutnu vrijednost.

Gledaj:

- je li rezultat smislen;
- jesu li top 3 bolji od top 5;
- vraća li prave stranice.

---

## 8. Ako promijeniš chunkove

Ako promijeniš `data/chunks.jsonl`, moraš ponovno buildati bazu:

```bash
python scripts/embed_chunks.py --reset
```

Ako ne koristiš `--reset`, možeš završiti s duplikatima ili starim chunkovima u bazi.

Za PoC: uvijek koristi `--reset` nakon promjene chunkova.

---

## 9. Ako želiš bolji model kasnije

Trenutni default:

```text
BAAI/bge-small-en-v1.5
```

Kasnije možemo probati:

```text
BAAI/bge-base-en-v1.5
BAAI/bge-m3
intfloat/e5-base-v2
```

Ali nemoj sada mijenjati sve odjednom.

Prvo napravi baseline.

---

## 10. Tipični problemi

### Problem: `ModuleNotFoundError: No module named chromadb`

Rješenje:

```bash
pip install -r requirements.txt
```

ili:

```bash
pip install chromadb
```

---

### Problem: model se dugo skida

Normalno je pri prvom pokretanju.

`sentence-transformers` skida model lokalno.

---

### Problem: corporate proxy / nema interneta

Ako si u mreži bez direktnog interneta, model download može pasti.

Privremena rješenja:

- testiraj doma / na mreži koja ima internet;
- ručno preuzmi model;
- koristi već cacheani model;
- kasnije možemo složiti offline model path.

---

### Problem: search vraća loše rezultate

Mogući razlozi:

- chunkovi su loši;
- PDF extraction je loš;
- query je preopćenit;
- dokument je previše tabličan;
- model nije idealan za taj tip sadržaja;
- Table of Contents dominira rezultatima.

Za PoC ne paničari.

Prvo probaj queryje koji koriste stvarne pojmove iz dokumenta.

---

## 11. Definition of Done za Step 3

Step 3 je gotov kada:

- `python scripts/embed_chunks.py --reset` prođe bez errora;
- `vector_db/chroma/` postoji;
- `python scripts/search_chunks.py "some technical query"` vrati top rezultate;
- rezultati imaju `source`, `page`, `chunk`, `distance`;
- barem nekoliko queryja vraća smislene stranice.

---

## 12. Što je sljedeće?

Ako Step 3 radi, Step 4 je:

# Step 4 — Retrieval Quality Check / Mini Eval

Nećemo odmah na LLM.

Prvo ćemo napraviti mali eval file:

```text
eval/questions.md
```

s 10–20 pitanja i očekivanim stranicama/sekcijama.

Cilj Step 4:

> Znati koliko dobar je retrieval prije nego dodamo LLM.

Tek nakon toga ide:

# Step 5 — LLM answer with citations

Tada ćemo od top chunkova napraviti prompt i dobiti odgovor s izvorima.
