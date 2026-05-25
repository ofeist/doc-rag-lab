# RAG Roadmap: From PoC to Spaceship

This document captures the high-level roadmap from the current technical-documentation RAG PoC toward a production-grade in-house RAG platform.

## Current State

We already have a working local RAG pipeline for technical documentation:

- PDF page extraction
- page-aware chunking
- local embeddings
- Chroma vector search
- BM25 keyword search
- hybrid retrieval with RRF
- retrieval evaluation with hit@1 / hit@3 / hit@5
- OpenAI-compatible answer generation
- citation-first prompts
- JSONL output for answer runs
- first manual model comparison on an interrupt-routing slice

The current strongest signal:

```text
Hybrid retrieval consistently places relevant context in top 3 / top 5 for focused technical slices.
Smaller models can answer simple and medium grounded questions when the right context is retrieved.
```

---

## Phase 1 — Stabilize the Current PoC

Goal: make the current workflow repeatable and less manual.

### 1. Add batch answer evaluation runner

Create a script such as:

```bash
scripts/run_answer_eval.py
```

Example usage:

```bash
python scripts/run_answer_eval.py \
  --eval eval/interrupt_routing_eval.json \
  --mode hybrid \
  --top-k 3 \
  --candidate-k 8 \
  --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 \
  --output-jsonl eval/rag_answer_interrupt_gpt54nano_batch.jsonl
```

Purpose:

- run multiple questions without copy/paste
- write one JSONL record per answer
- make model comparison repeatable
- keep grading manual for now

Acceptance criteria:

- supports `--eval`
- supports `--limit`
- supports `--model`
- supports `--base-url`
- supports `--output-jsonl`
- reuses existing retrieval settings
- fails clearly when API key is missing

### 2. Add manual grading format

Create a small human-readable report format:

```text
question
model
retrieved sources
citation present: yes/no
grounded: yes/no
hallucination: yes/no
result: PASS/FAIL
notes
```

Do not automate grading yet.

### 3. Compare models on the same question set

Start with:

```text
gpt-5.5
gpt-5.4-mini
gpt-5.4-nano
```

Later add local or open models:

```text
Qwen 3.5 / 3.6
Qwen Coder
Llama
Mistral
DeepSeek
```

---

## Phase 2 — Expand Across Document Slices

Goal: prove the approach is not only working on one easy slice.

### 1. Repeat answer evaluation on existing retrieval slices

Use focused indexes for:

- Boot / BMHD
- DMA / cache coherency
- Interrupt routing

For each slice:

```text
extract pages
chunk
embed
run retrieval eval
run answer eval
write report
```

### 2. Add harder technical slices

Add stress-test slices:

- memory map / address ranges
- register tables
- safety / SMU / watchdog topics
- peripheral configuration procedures
- cross-reference-heavy sections

### 3. Track failure types

Classify failures:

```text
retrieval miss
bad chunking
bad extraction
wrong expected_pages
model hallucination
bad citation
answer too vague
answer truncated
insufficient context not detected
```

This is more useful than only tracking pass/fail.

---

## Phase 3 — Improve Retrieval Quality

Goal: make the retrieval layer robust enough before investing heavily in model logic.

### 1. Tune hybrid retrieval

Experiment with:

- `top_k`
- `candidate_k`
- `rrf_k`
- vector-only vs BM25-only vs hybrid
- query wording
- focused index vs larger index

### 2. Add reranking

Later, test rerankers:

- cross-encoder reranker
- BGE reranker
- local reranker model
- OpenAI-compatible reranking only if allowed in the environment

Use reranking only if it clearly improves answer quality.

### 3. Improve chunking

Test:

- page-based chunks
- heading-aware chunks
- table-aware chunks
- smaller chunks for tables/registers
- larger chunks for procedural explanations

Keep page metadata reliable.

---

## Phase 4 — Improve Parsing and Extraction

Goal: handle real technical PDFs better.

### 1. Parser benchmark

Compare extraction quality on representative documents:

- current PyMuPDF-based extraction
- PyMuPDF4LLM
- Docling
- Marker
- Unstructured

Evaluate against:

```text
text quality
table preservation
page metadata correctness
speed
dependency complexity
offline usability
```

### 2. Table strategy

For table-heavy content, add special handling:

- extract tables separately
- preserve table rows and headers
- store table chunks with metadata
- support exact lookup for register fields, bit values, and address ranges

### 3. Quality gates

Add automatic checks:

```text
empty pages
very short pages
missing page numbers
suspicious extraction noise
too many broken lines
too many table artifacts
```

---

## Phase 5 — Multi-Document RAG

Goal: move from one focused PDF slice to a real documentation corpus.

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
Qwen 3.5 / 3.6
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

---

## Recommended Next Concrete Step

The next best implementation slice is:

```text
Add batch runner for RAG answer evaluation.
```

Why:

```text
It turns the current manual answer-testing workflow into a repeatable process.
It enables real model comparison.
It prepares the project for local model testing.
It does not require changing retrieval, parser, or chunking yet.
```
