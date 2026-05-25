# RAG Roadmap: From PoC to Spaceship

This document captures the high-level roadmap from the current technical-documentation RAG PoC toward a production-grade in-house RAG platform.

It is intentionally written as a practical engineering roadmap, not as a product brochure. The goal is to keep the system measurable, inspectable, and grounded in concrete failures discovered during evaluation.

---

## Current State

We already have a working local RAG pipeline for technical documentation:

- PDF page extraction
- full-document ingest
- focused page-range ingest for eval/debug slices
- page-aware chunking
- configurable chunk size and overlap
- local embeddings
- Chroma vector search
- BM25 keyword search
- hybrid retrieval with RRF
- experimental BM25-first hybrid retrieval for table-heavy slices
- retrieval evaluation with hit@1 / hit@3 / hit@5
- OpenAI-compatible answer generation
- citation-first prompts
- JSONL output for answer runs
- safe answer-output handling with explicit overwrite/append behavior
- manual answer grading reports
- curated eval/debug slice manifest
- per-slice recommended retrieval settings

Current eval/debug slices:

```text
boot_bmhd
interrupt_routing
dma_cache
memory_map
```

The current strongest signal:

```text
Prose and semi-structured technical slices work well with the current pipeline.

Dense table-heavy slices, such as memory maps and address tables, need special retrieval and chunking treatment.

For table-heavy lookup, BM25 and smaller chunks currently outperform vector search and standard RRF hybrid retrieval.
```

The most important current bottleneck is not answer generation. The answer layer usually behaves well when the right context is retrieved. The main weakness is retrieval/context assembly for dense tables, repeated rows, hexadecimal addresses, and flattened PDF table layouts.

---

## Phase 1 — Stabilize the Current PoC

Status: **completed**

Goal: make the current workflow repeatable and less manual.

### Completed outcomes

- Added a batch answer evaluation runner:

```bash
scripts/run_answer_eval.py
```

- Added JSONL output for answer runs.
- Added safe output behavior:
  - default: refuse to overwrite existing output
  - `--overwrite`: replace existing output
  - `--append`: intentionally append
- Added manual grading format.
- Ran answer evaluation on focused technical slices.
- Confirmed that smaller/cheaper models can answer grounded questions when the right context is retrieved.

### Key lesson

Manual single-question testing is not enough. Batch answer evaluation plus manual grading gives a repeatable way to compare retrieval settings, prompts, and models.

---

## Phase 2 — Expand Across Document Slices

Status: **completed as a lab/eval foundation**

Goal: prove the approach is not only working on one easy slice.

### Completed outcomes

- Added repeatable ingest command:

```bash
scripts/ingest_document.py
```

- Clarified ingest modes:
  - full-document ingest is the normal workflow
  - focused page-range ingest is eval/debug mode
- Added curated slice manifest:

```text
configs/slices.json
```

- Clarified that the slice manifest is an eval/debug fixture registry, not the main product workflow.
- Added validation helper for the slice manifest.
- Added current workflow documentation.
- Added per-slice recommended retrieval settings.
- Added a table-heavy stress slice:

```text
memory_map
```

- Diagnosed memory-map retrieval failures.
- Ran a chunk-size experiment for memory-map retrieval.
- Ran memory-map answer batch stress eval.
- Added manual grading for memory-map answers.

### Current eval slices

| Slice | Content type | Recommended chunking | Recommended retrieval mode | Status |
| --- | --- | ---: | --- | --- |
| `boot_bmhd` | startup / Boot Mode Header flow | 800/120 | hybrid | good focused slice |
| `dma_cache` | cacheability / DMA / coherency | 800/120 | hybrid | good focused slice |
| `interrupt_routing` | interrupt router / SRC / TOS | 800/120 | hybrid | good focused slice |
| `memory_map` | dense address-map tables | 300/60 | BM25 or BM25-first hybrid | hard stress slice |

### Memory-map findings

The `memory_map` slice was intentionally selected because it stresses dense table lookup:

- repeated table rows
- repeated Program Flash bank names
- hexadecimal address ranges
- similar alternate SOTA mappings across device families
- flattened PDF table text

Baseline table-heavy retrieval was weak:

```text
800/120 chunks:
vector:             hit@1 20%, hit@3 40%, hit@5 40%
BM25:               hit@1 40%, hit@3 60%, hit@5 70%
hybrid/RRF:          hit@1 40%, hit@3 40%, hit@5 40%
BM25-first hybrid:  hit@1 40%, hit@3 60%, hit@5 70%
```

Smaller chunks improved the table-heavy slice:

```text
300/60 chunks:
vector:             hit@1 30%, hit@3 40%, hit@5 40%
BM25:               hit@1 60%, hit@3 60%, hit@5 80%
hybrid/RRF:          hit@1 30%, hit@3 50%, hit@5 50%
BM25-first hybrid:  hit@1 60%, hit@3 60%, hit@5 80%
```

Memory-map answer grading summary:

```text
PASS:    6
PARTIAL: 2
FAIL:    2
TOTAL:   10
```

Interpretation:

```text
The answer layer is not the primary weakness.
When the correct chunk is present, the model usually answers well.
Failures are mostly retrieval/context/table-layout related.
```

---

## Phase 3 — Improve Table-Heavy Retrieval

Status: **next recommended phase**

Goal: make retrieval robust for technical tables before investing heavily in model logic.

This phase should focus on the known bottleneck discovered in Phase 2: dense tables, memory maps, register tables, bit fields, and repeated numeric rows.

### 1. Table-aware / row-group chunking experiment

Start with the existing extracted text. Do not immediately build a full PDF table parser.

Goal: produce retrieval units that preserve table context, for example:

```text
Table title
Column headers
Row group
Page number
Section title
```

Example target representation:

```text
Table 24 — Address Map of Segments 0 to 14
Columns: Segment, Address Range, Size, Description, Read, Write

Row:
Segment: 8
Address Range: 8000 0000H - 802F FFFFH
Size: 3 Mbyte
Description: Program Flash 0
Read: Access
Write: BBBBE
```

Acceptance signal:

```text
memory_map retrieval improves beyond the current 300/60 BM25 baseline.
```

### 2. Parent-child retrieval

Search smaller child chunks, but return larger parent context.

Example:

```text
child chunk: one row or small row group
parent context: page / table / section containing that row
```

This is likely useful because exact lookup wants small chunks, but answer generation often needs surrounding table headers and context.

### 3. Hex/address normalization

Normalize address variants so queries and extracted text match more reliably.

Examples:

```text
A000 0000H
A000_0000H
0xA0000000
A0000000H
```

Also normalize/expand common table terms:

```text
PF0 <-> Program Flash 0
PFLASH <-> Program Flash
UCB
CFS
BROM <-> Boot ROM
```

### 4. BM25-weighted fusion or reranking

The existing RRF hybrid can degrade BM25 results on dense tables.

Future experiments:

- weighted RRF with stronger BM25 influence
- BM25-first with smarter vector fill
- cross-encoder reranking
- local reranker model

Use reranking only if it clearly improves retrieval and answer quality.

### 5. Keep regression checks

Every Phase 3 retrieval change should be tested against:

```text
boot_bmhd
dma_cache
interrupt_routing
memory_map
```

The goal is to improve table-heavy retrieval without regressing prose/semi-structured slices.

---

## Phase 4 — Improve Parsing and Extraction

Goal: handle real technical PDFs better.

Phase 4 should come after at least one small table-aware chunking experiment. Do not start with a large parser migration unless the simpler table-aware chunking experiment fails.

### 1. Parser benchmark

Compare extraction quality on representative documents:

- current PyMuPDF-based extraction
- PyMuPDF table extraction
- PyMuPDF4LLM
- Docling
- Marker
- Unstructured
- Camelot, where applicable for table-heavy PDFs

Evaluate against:

```text
text quality
table preservation
row/header preservation
page metadata correctness
speed
dependency complexity
offline usability
```

### 2. Table strategy

For table-heavy content, add special handling:

- extract tables separately when reliable
- preserve table rows and headers
- store table chunks with metadata
- support exact lookup for register fields, bit values, and address ranges
- connect table chunks back to surrounding page/section context

### 3. Quality gates

Add automatic checks:

```text
empty pages
very short pages
missing page numbers
suspicious extraction noise
too many broken lines
too many table artifacts
pages with likely tables but poor extraction
```

---

## Phase 5 — Multi-Document RAG

Goal: move from one focused PDF/manual to a real documentation corpus.

### 1. Add document manifest

Example:

```yaml
documents:
  - id: aurix_tc3xx_part1
    path: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
    version: V2.0.0
    vendor: Infineon
    type: user_manual
```

### 2. Add corpus-level indexing

Index multiple documents while preserving:

- document id
- title
- version
- page
- section
- source path
- chunk id
- parser version
- chunking strategy
- embedding model

### 3. Add source filtering

Support queries like:

```text
only this document
only this version
only these sections
only this vendor
only safety-related docs
```

---

## Phase 6 — Evaluation as a First-Class System

Goal: make quality measurable and repeatable.

### 1. Build eval sets per topic

Example:

```text
10 questions per focused slice
50-100 questions per document
hundreds across corpus later
```

### 2. Separate retrieval eval from answer eval

Retrieval eval:

```text
Did we retrieve the right pages/chunks?
```

Answer eval:

```text
Did the model answer correctly using only retrieved context?
```

### 3. Add regression gates

Before changing parser, chunking, embedding, retrieval, or model:

```bash
run retrieval eval
run answer eval
compare results
document regressions
```

### 4. Add model comparison reports

Track:

```text
quality
latency
cost
citation quality
hallucination rate
insufficient-context behavior
```

### 5. Add automated grading later

Manual grading should remain the source of truth for now.

Later, add optional evaluator assistance:

- expected-page checks
- citation presence checks
- insufficient-context behavior checks
- LLM-assisted grading only as a helper, not as the only judge

---

## Phase 7 — Local / In-House Model Serving

Goal: make the system usable in restricted environments.

### 1. OpenAI-compatible abstraction

Keep the answer layer provider-neutral:

```text
OpenAI API from home
local vLLM at work
Ollama for experiments
internal OpenAI-compatible endpoint later
```

### 2. Test local models

Start with:

```text
Qwen
Qwen Coder
Llama
Mistral
DeepSeek
```

Use the same JSONL answer-eval workflow.

### 3. Decide model policy

For each use case:

```text
cheap model for simple grounded lookup
stronger model for multi-source synthesis
strong model for code/design generation
no model answer when retrieval is weak
```

---

## Phase 8 — User-Facing Prototype

Goal: turn scripts into a usable internal tool.

### 1. Simple CLI

Example:

```bash
rag ask "What does the SRPN field define?"
```

### 2. Minimal web UI

Features:

- ask a question
- show answer
- show citations
- show retrieved chunks
- show source document/page
- allow feedback: good/bad/wrong citation

### 3. Admin/debug UI

Show:

- retrieval mode
- scores
- selected chunks
- prompt
- model
- latency
- token usage if available
- parser/chunker/retriever versions

---

## Phase 9 — Production-Grade Architecture

Goal: move from lab scripts to maintainable infrastructure.

### 1. Replace PoC storage where needed

Possible upgrades:

```text
Chroma -> Qdrant / OpenSearch / pgvector
local files -> object storage
JSONL evals -> database-backed eval runs
```

### 2. Add ingestion pipeline

Pipeline stages:

```text
upload document
extract
quality check
chunk
embed
index
run smoke eval
publish corpus version
```

### 3. Add versioning

Track:

```text
document version
parser version
chunker version
embedding model
retrieval config
answer model
prompt version
eval set version
```

### 4. Add permissions

For enterprise use:

```text
document access control
user groups
project spaces
audit logs
restricted documents
```

---

## Phase 10 — “Spaceship” Features

Goal: advanced in-house documentation intelligence platform.

### 1. Agentic documentation assistant

Capabilities:

- answer questions
- cite exact pages
- compare document versions
- explain procedures
- identify contradictions
- summarize sections
- generate checklists
- produce onboarding material

### 2. Design and code assistance

For automotive / embedded workflows:

- answer from user manuals
- answer from AUTOSAR docs
- answer from Vector docs
- assist with detailed design
- generate code skeletons only when supported by docs
- explain generated code with citations

### 3. Continuous documentation intelligence

Features:

- detect changed pages between document versions
- regenerate affected embeddings only
- rerun affected evals
- report quality regressions
- notify when answers may have changed

### 4. Expert feedback loop

Allow engineers to:

- mark wrong answers
- correct expected pages
- add golden answers
- approve trusted answer templates
- improve eval sets over time

### 5. Model routing

Choose model based on task:

```text
cheap model: direct lookup
medium model: procedure extraction
strong model: synthesis / comparison / code reasoning
no answer: insufficient retrieval confidence
```

---

## Guiding Principles

1. Retrieval quality first.
2. Citations are mandatory.
3. Never trust answer quality if retrieval failed.
4. Keep parser, chunker, retriever, model, and prompt versions visible.
5. Prefer small repeatable evals over vague demos.
6. Do not overbuild before measuring failures.
7. Use local/in-house components where work restrictions require it.
8. Treat every model answer as untrusted until grounded and cited.
9. Make failures useful by classifying them.
10. Build thin slices, commit often, and keep the system inspectable.
11. Do not optimize for one slice while silently regressing others.
12. Treat table-heavy retrieval as a separate technical problem, not just “more chunking.”

---

## Recommended Next Concrete Step

The next best implementation slice is:

```text
P3-1 — Table-aware row-group chunking experiment for memory_map
```

Why:

```text
The memory_map stress slice showed that dense tables are the current bottleneck.
BM25 plus smaller chunks improved retrieval, but did not fully solve exact table-row lookup.
The next step should preserve table title/header/row-group context before investing in larger parser migrations or rerankers.
```

Suggested first P3 acceptance signal:

```text
Improve memory_map retrieval beyond the current 300/60 BM25 baseline,
without regressing boot_bmhd, dma_cache, or interrupt_routing.
```
