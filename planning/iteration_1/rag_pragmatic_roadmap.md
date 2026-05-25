# Pragmatični RAG Roadmap — od nule do korisnog PoC-a

## Cilj prve verzije

Cilj nije odmah napraviti enterprise RAG platformu.

Cilj prve verzije je:

> Imam jedan tehnički PDF. Mogu postaviti pitanje. Sustav mi vrati relevantne dijelove dokumenta i kratak odgovor s izvorom.

To je dovoljno za početak.

---

## Big picture: put od nule do korisnog RAG-a

## Faza 0 — Odlučiti prvi mali target

Ne uzimamo odmah:

- Aurix;
- Vector;
- AUTOSAR;
- interne noteove;
- sve PDF-ove odjednom.

Prvi target treba biti mali i mjerljiv:

- 1 PDF;
- 1 tema;
- 20 test pitanja.

Primjer:

- AURIX TC3xx manual;
- tema: cache/DMA ili interrupt/reset;
- cilj: pronaći točne sekcije i stranice.

Output faze:

```text
docs/
  aurix_tc3xx_manual.pdf

eval/
  questions.md
```

Ovo je važno jer ne gradimo samo “chatbot”, nego alat koji možemo provjeriti.

---

## Faza 1 — PDF extraction

Cilj:

> Izvući tekst iz PDF-a i vidjeti je li usable.

Minimalni output:

```text
data/raw_pages.jsonl
```

Svaki red:

```json
{"page": 123, "text": "..."}
```

Tu ne filozofiramo.

Samo želimo znati:

> Možemo li dobiti tekst iz PDF-a?

Ako su tablice loše — zabilježimo, ali ne rješavamo odmah savršeno.

---

## Faza 2 — Chunking

Cilj:

> Razbiti tekst u manje dijelove koje možemo pretraživati.

Minimalni output:

```text
data/chunks.jsonl
```

Primjer chunka:

```json
{
  "chunk_id": "aurix-000123",
  "source": "aurix_manual.pdf",
  "page_start": 312,
  "page_end": 313,
  "text": "..."
}
```

Prva verzija može biti token-based chunking.

Nije idealno, ali dovoljno za PoC.

Kasnije dodajemo section-aware chunking.

---

## Faza 3 — Embeddings + vector store

Cilj:

> Svaki chunk pretvoriti u embedding i spremiti ga u bazu.

Za početak:

- lokalno: ChromaDB;
- embedding: `bge-m3` ili OpenAI embeddings.

Output:

```text
vector_db/
```

Tu prvi put dobivaš semantičku pretragu.

---

## Faza 4 — Retrieval-only test

Ovo je jako bitno.

Prije LLM-a pitamo:

> Kad postavim pitanje, vraća li sustav prave chunkove?

Primjer:

```bash
python search.py "Why can DMA return stale data?"
```

Output:

```text
Top results:
1. page 312 — Cache coherency...
2. page 314 — DMA access...
3. page 290 — Memory subsystem...
```

Ako ovo ne radi, nema smisla dodavati LLM.

---

## Faza 5 — LLM answer

Tek sada dodajemo model.

Pipeline:

```text
question
  ↓
retriever finds chunks
  ↓
chunks go into prompt
  ↓
LLM answers only from provided context
```

Output odgovora mora biti ovakav:

```text
Answer:
DMA can return stale data if cache coherency is not handled correctly...

Sources:
- aurix_manual.pdf, page 312
- aurix_manual.pdf, page 314

Confidence:
Medium

Missing:
The retrieved context does not show the full DMA/cache invalidation procedure.
```

To je pragmatično i sigurnije od generičkog chatbot odgovora.

---

## Faza 6 — Eval set

Cilj:

> Ne vjerujemo osjećaju. Testiramo.

Napraviš 20–30 pitanja.

Primjer:

```text
Q1: What happens during warm reset?
Expected: Reset chapter, pages X-Y

Q2: What controls interrupt priority?
Expected: Interrupt chapter, pages X-Y

Q3: Can DMA read stale cached data?
Expected: Cache/DMA section, pages X-Y
```

Ne treba odmah savršena automatizacija.

Prvo može ručno:

- pitanje;
- expected page/section;
- actual retrieved chunks;
- pass/fail.

To je već dovoljno za prvu ozbiljnu verziju.

---

## Faza 7 — Poboljšanja

Tek kad osnovni flow radi, poboljšavamo:

1. bolji chunking po sekcijama;
2. metadata extraction;
3. hybrid search: keyword + vector;
4. reranker;
5. bolji prompt;
6. handling tablica;
7. verzioniranje dokumenata;
8. dodavanje internih debug noteova;
9. dodavanje Vector/AUTOSAR dokumenata.

Ne ranije.

---

# Prva verzija arhitekture

Najjednostavnije:

```text
PDF
 ↓
extract_pages.py
 ↓
raw_pages.jsonl
 ↓
chunk_pages.py
 ↓
chunks.jsonl
 ↓
embed_chunks.py
 ↓
ChromaDB
 ↓
search.py
 ↓
ask.py
```

To je dovoljno.

Ne treba odmah:

- FastAPI;
- UI;
- auth;
- Docker;
- Kubernetes;
- fancy frontend.

Prvo CLI.

---

# Milestones

## Milestone 1 — Mogu čitati PDF

Output:

```bash
python extract_pages.py docs/manual.pdf
```

Dobiješ:

```text
data/raw_pages.jsonl
```

---

## Milestone 2 — Imam chunkove

Output:

```bash
python chunk_pages.py
```

Dobiješ:

```text
data/chunks.jsonl
```

---

## Milestone 3 — Mogu pretraživati

Output:

```bash
python search.py "DMA stale data cache"
```

Dobiješ top 5 relevantnih chunkova.

---

## Milestone 4 — Imam prvi RAG odgovor

Output:

```bash
python ask.py "Why can DMA return stale data?"
```

Dobiješ odgovor + izvore.

---

## Milestone 5 — Znam koliko dobro radi

Output:

```bash
python eval_manual.py
```

Dobiješ nešto tipa:

```text
20 questions
14 good retrieval
4 partial
2 failed
```

To je već ozbiljan početak.

---

# Što nećemo raditi odmah

Nećemo odmah:

- graditi web aplikaciju;
- trenirati model;
- ubaciti 50 PDF-ova;
- dodavati AUTOSAR;
- raditi fine-tuning;
- raditi kompleksnu arhitekturu;
- raspravljati danima o najboljoj vector bazi.

To kasnije.

Prvo working loop.

---

# Najvažniji princip

Za svaku fazu mora postojati konkretan output.

Ne:

> Naučili smo embeddings.

Nego:

> Imam `chunks.jsonl`, imam `search.py`, i pitanje vraća prave stranice.

To je prava mjera napretka.

---

# Predloženi radni plan

## TASK 0001 — Minimal project skeleton

Napraviti folder strukturu:

```text
aurix-rag/
  docs/
  data/
  scripts/
  eval/
  README.md
  requirements.txt
```

---

## TASK 0002 — PDF extraction

Skripta:

```text
scripts/extract_pages.py
```

Output:

```text
data/raw_pages.jsonl
```

---

## TASK 0003 — Chunking

Skripta:

```text
scripts/chunk_pages.py
```

Output:

```text
data/chunks.jsonl
```

---

## TASK 0004 — Search

Embeddings + Chroma.

Output:

```bash
python scripts/search.py "example question"
```

---

## TASK 0005 — Ask

LLM answer with citations.

Output:

```bash
python scripts/ask.py "example question"
```

---

## TASK 0006 — Eval

20 pitanja, ručna ili djelomično automatska provjera.

Output:

```text
pass / partial / fail
```

---

# Ukratko

Najbolji početak nije savršeni RAG.

Najbolji početak je:

> jedan PDF → tekst → chunkovi → search → odgovor s izvorima → 20 test pitanja.

Kad to radi, tek onda radimo “pro verziju”.
