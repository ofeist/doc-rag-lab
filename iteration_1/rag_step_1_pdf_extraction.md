# RAG PoC — STEP 1: Project Skeleton + PDF Extraction Smoke Test

## Cilj Step 1

Prvi cilj nije “napraviti RAG”.

Prvi cilj je puno jednostavniji:

> Uzeti jedan PDF, izvući tekst page-by-page, spremiti ga u reproducibilan format i ručno provjeriti je li ekstrakcija dovoljno dobra za nastavak.

Ako ovaj korak ne radi dobro, nema smisla ići na chunking, embeddings ili LLM.

---

## Što nam treba

### Alati

Minimalno:

- Python 3.10+
- Git Bash / terminal
- jedan testni PDF
- PyMuPDF biblioteka

Za sada ne trebamo:

- ChromaDB
- embeddings
- LLM
- FastAPI
- Docker
- frontend
- Kubernetes
- OCR
- AUTOSAR / Vector dokumente

Ovo je samo **PDF extraction smoke test**.

---

## Predložena folder struktura

Kreiramo projekt ovako:

```text
aurix-rag/
  docs/
    sample.pdf
  data/
    raw_pages.jsonl
  scripts/
    extract_pages.py
  eval/
  requirements.txt
  README.md
```

Za početak `sample.pdf` može biti bilo koji PDF.

Kasnije ćemo ga zamijeniti konkretnim AURIX manualom.

---

## Korak 1.1 — Kreiraj projekt

```bash
mkdir aurix-rag
cd aurix-rag

mkdir docs data scripts eval
touch README.md requirements.txt
```

Na Windowsu kroz Git Bash ovo bi trebalo raditi normalno.

---

## Korak 1.2 — Virtual environment

```bash
python -m venv .venv
```

Aktivacija:

### Git Bash / Linux / macOS

```bash
source .venv/Scripts/activate
```

Ako si na Linuxu/macOS-u:

```bash
source .venv/bin/activate
```

### Windows CMD

```cmd
.venv\Scripts\activate
```

---

## Korak 1.3 — requirements.txt

U `requirements.txt` stavi:

```txt
pymupdf==1.24.14
```

Instalacija:

```bash
pip install -r requirements.txt
```

Ako ne želiš odmah pinati verziju, može i ovako:

```txt
pymupdf
```

Za PoC je to dovoljno.

---

## Korak 1.4 — Ubaci PDF

Stavi jedan PDF u folder `docs/`.

Za početak:

```text
docs/sample.pdf
```

Može biti bilo koji PDF, ali idealno je da bude tehnički manual ili nešto slično AURIX dokumentaciji.

---

## Korak 1.5 — Skripta: `scripts/extract_pages.py`

Kreiraj file:

```text
scripts/extract_pages.py
```

I ubaci ovaj kod:

```python
#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import fitz  # PyMuPDF


def extract_pages(pdf_path: Path, max_pages: int | None = None) -> list[dict]:
    """
    Extract text from a PDF page-by-page.

    Output is intentionally simple:
    - one record per page
    - page number is 1-based
    - text is raw-ish extraction from PyMuPDF

    This is not yet a perfect ingestion pipeline.
    It is a smoke test: can we extract usable text?
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    records: list[dict] = []

    total_pages = len(doc)
    pages_to_process = total_pages if max_pages is None else min(max_pages, total_pages)

    for page_index in range(pages_to_process):
        page = doc[page_index]
        text = page.get_text("text")

        record = {
            "source": pdf_path.name,
            "source_path": str(pdf_path),
            "page": page_index + 1,
            "page_index": page_index,
            "total_pages": total_pages,
            "char_count": len(text),
            "text": text,
        }

        records.append(record)

    doc.close()
    return records


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_preview(records: list[dict], preview_pages: int = 3, preview_chars: int = 1000) -> None:
    for record in records[:preview_pages]:
        print("\n" + "=" * 80)
        print(f"PAGE {record['page']} | chars={record['char_count']}")
        print("=" * 80)
        print(record["text"][:preview_chars])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract page-by-page text from a PDF into JSONL."
    )
    parser.add_argument(
        "pdf",
        type=Path,
        help="Path to the PDF file, e.g. docs/sample.pdf",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw_pages.jsonl"),
        help="Output JSONL path. Default: data/raw_pages.jsonl",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional limit for smoke testing, e.g. --max-pages 10",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Do not print page preview to terminal.",
    )

    args = parser.parse_args()

    records = extract_pages(args.pdf, args.max_pages)
    write_jsonl(records, args.out)

    print(f"Extracted pages: {len(records)}")
    print(f"Output written to: {args.out}")

    if not args.no_preview:
        print_preview(records)


if __name__ == "__main__":
    main()
```

---

## Korak 1.6 — Pokretanje

Ako imaš PDF ovdje:

```text
docs/sample.pdf
```

Pokreni:

```bash
python scripts/extract_pages.py docs/sample.pdf
```

Output bi trebao biti:

```text
Extracted pages: 123
Output written to: data/raw_pages.jsonl

================================================================================
PAGE 1 | chars=...
================================================================================
...
```

Ako želiš prvo samo 10 stranica:

```bash
python scripts/extract_pages.py docs/sample.pdf --max-pages 10
```

Ako ne želiš preview u terminalu:

```bash
python scripts/extract_pages.py docs/sample.pdf --no-preview
```

---

## Što dobivamo na kraju Step 1

Glavni output:

```text
data/raw_pages.jsonl
```

Format je JSONL: jedan JSON objekt po stranici.

Primjer jednog reda:

```json
{"source":"sample.pdf","source_path":"docs/sample.pdf","page":1,"page_index":0,"total_pages":123,"char_count":842,"text":"..."}
```

Zašto JSONL?

- jednostavno se čita line-by-line;
- dobro radi za veće dokumente;
- lako se kasnije pretvara u chunks;
- lako se debugira;
- ne mora se sve držati u memoriji.

---

## Kako znamo da je Step 1 uspješan?

Step 1 je uspješan ako vrijedi ovo:

1. `data/raw_pages.jsonl` postoji.
2. Ima približno isti broj redova kao PDF stranica.
3. Prvih nekoliko stranica ima čitljiv tekst.
4. Tehničke sekcije nisu potpuno uništene.
5. Nema očitog problema tipa:
   - svaka stranica prazna;
   - tekst je potpuno razbijen;
   - tablice su potpuno neupotrebljive;
   - redoslijed teksta je katastrofalan.

Ne tražimo savršenstvo.

Tražimo:

> “Dovoljno dobro da možemo probati chunking.”

---

## Mini quality check

Nakon pokretanja, napravi ručni check:

```bash
head -n 1 data/raw_pages.jsonl
```

Ili čitljivije:

```bash
python -m json.tool data/raw_pages.jsonl
```

Napomena: `json.tool` radi bolje za JSON file, ali JSONL ima više JSON redova, pa može puknuti na cijelom fileu. Zato je za JSONL praktičnije kasnije napraviti mali preview helper.

Za sada je dovoljno pogledati terminal preview.

---

## Tipični problemi

### Problem 1 — PDF ima jako malo teksta

Simptom:

```text
PAGE 1 | chars=0
PAGE 2 | chars=0
```

Mogući uzroci:

- PDF je skenirana slika;
- PDF nema text layer;
- dokument je zaštićen;
- PyMuPDF ne može izvući tekst.

Za sada ne rješavamo OCR. Samo zabilježimo problem.

---

### Problem 2 — tablice su loše

Ovo je očekivano.

PyMuPDF plain text extraction često razbije tablice.

Za Step 1 to nije blocker ako običan tekst radi.

Kasnije možemo posebno obraditi:

- register tablice;
- bitfieldove;
- reset values;
- warning/note blokove.

---

### Problem 3 — header/footer noise

Primjer:

- naziv dokumenta na svakoj stranici;
- page footer;
- copyright;
- repeated chapter title.

Za Step 1 ne čistimo agresivno.

Kasnije možemo dodati cleaning.

---

## Važno: što Step 1 NIJE

Step 1 nije:

- RAG;
- semantička pretraga;
- chatbot;
- LLM integration;
- final ingestion pipeline;
- production-ready extractor.

Step 1 je samo:

> “Možemo li pouzdano izvući tekst iz PDF-a i spremiti ga page-by-page?”

---

## Predloženi commit nakon Step 1

Ako koristiš Git:

```bash
git init
git add README.md requirements.txt scripts/extract_pages.py
git commit -m "Add PDF page extraction smoke test"
```

Ne bih commit-a-o velike vendor PDF-ove bez razmišljanja.

Za sada možeš dodati u `.gitignore`:

```gitignore
.venv/
__pycache__/
data/
docs/*.pdf
```

Ako želiš commitati sample PDF, neka bude mali i bez licensing problema.

---

## Minimalni `.gitignore`

Kreiraj:

```text
.gitignore
```

Sadržaj:

```gitignore
.venv/
__pycache__/
*.pyc

data/
vector_db/

docs/*.pdf
```

Zašto ignorirati `docs/*.pdf`?

Zato što vendor dokumentacija često ima licensing/distribution ograničenja.

Lokalno je koristiš, ali je ne guraš nužno u Git.

---

## README minimalno

U `README.md` možeš staviti:

```md
# Aurix RAG PoC

Minimal pragmatic RAG proof-of-concept for technical PDF documentation.

## Step 1: PDF extraction

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

python scripts/extract_pages.py docs/sample.pdf
```

Output:

```text
data/raw_pages.jsonl
```
```

---

## Kada idemo na Step 2?

Na Step 2 idemo kad imamo:

```text
data/raw_pages.jsonl
```

i kad ručno potvrdimo:

> “Tekst izgleda dovoljno čitljivo za chunking.”

Step 2 će biti:

> `raw_pages.jsonl` → `chunks.jsonl`

Tada uvodimo:

- chunk size;
- overlap;
- basic metadata;
- chunk IDs;
- page ranges;
- kasnije section detection.

---

## Sažetak

Step 1 je mali, ali važan.

Output nije teorija.

Output je file:

```text
data/raw_pages.jsonl
```

Ako to imamo, možemo nastaviti prema pravom RAG pipelineu.

Pragmatični redoslijed:

```text
PDF
  ↓
extract_pages.py
  ↓
raw_pages.jsonl
  ↓
Step 2: chunk_pages.py
```
