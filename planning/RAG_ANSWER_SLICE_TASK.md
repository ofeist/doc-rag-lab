# TASK: Add First Grounded RAG Answer Slice

## Goal

Implement the first grounded RAG answer flow on top of the existing retrieval pipeline.

The project already has focused retrieval evaluation slices for:

- Boot/BMHD
- DMA/cache
- Interrupt routing

The retrieval pipeline already supports:

- vector retrieval
- BM25 retrieval
- hybrid retrieval using Reciprocal Rank Fusion (RRF)

This task must add a small, local, reproducible answer-generation layer that uses the existing hybrid retrieval results as context and asks a local LLM to answer with citations.

This is not a UI task.
This is not a parser task.
This is not a new retrieval algorithm task.
This is only the first CLI-based grounded answer slice.

---

## Non-goals

Do not change the extraction pipeline.

Do not change chunking.

Do not change the embedding model.

Do not change the vector database implementation.

Do not change the existing retrieval eval metrics.

Do not add a web UI.

Do not introduce cloud APIs.

Do not use proprietary model APIs.

Do not make the answer generation “smart” with agents, planning, or multi-step reasoning.

Do not auto-generate new eval questions.

Do not modify existing baseline results unless a command or path is broken.

---

## Assumptions

The repository already contains scripts similar to:

```text
scripts/extract_pages.py
scripts/chunk_pages.py
scripts/embed_chunks.py
scripts/eval_retrieval.py
scripts/search_chunks.py
```

The current local focused index is rebuilt by running the existing extraction, chunking, and embedding commands.

The answer slice should reuse the current Chroma collection and `data/chunks.jsonl`.

The local LLM should be called through an OpenAI-compatible HTTP endpoint if available.

Default local endpoint:

```text
http://localhost:8000/v1/chat/completions
```

Default model name can be passed by CLI.

Example model placeholder:

```text
local-model
```

The script must also support a dry-run mode so the retrieval/context/prompt can be tested even without a local LLM.

---

## Expected deliverables

Implement these files/changes:

```text
scripts/ask_chunks.py
README.md
examples/rag_answer_questions.txt
```

Optional but useful:

```text
eval/rag_answer_first_baseline.md
```

---

## Required CLI behavior

Create a new script:

```text
scripts/ask_chunks.py
```

It must support this minimum command:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --db vector_db/chroma \
  --collection technical_docs \
  --chunks data/chunks.jsonl \
  --mode hybrid \
  --top-k 5 \
  --model local-model \
  --base-url http://localhost:8000/v1
```

It must also support dry-run:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --db vector_db/chroma \
  --collection technical_docs \
  --chunks data/chunks.jsonl \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

Dry-run must print:

- question
- retrieval mode
- top retrieved chunks
- page ranges
- chunk ids
- prompt that would be sent to the model

Dry-run must not call any model endpoint.

---

## Required CLI arguments

`scripts/ask_chunks.py` must support:

```text
--question        Required. User question.
--db              Default: vector_db/chroma
--collection      Default: technical_docs
--chunks          Default: data/chunks.jsonl
--mode            Choices: vector, bm25, hybrid. Default: hybrid
--top-k           Default: 5
--candidate-k     Default: 10. Used for hybrid candidate retrieval.
--rrf-k           Default: 60
--model           Default: local-model
--base-url        Default: http://localhost:8000/v1
--temperature     Default: 0.0
--max-tokens      Default: 512
--dry-run         If present, do not call the LLM.
--show-context    If present, print full retrieved context.
```

---

## Retrieval implementation requirement

Reuse the existing retrieval logic from `scripts/eval_retrieval.py` as much as possible.

The weak-model executor should prefer copying or extracting these functions rather than inventing a new retrieval implementation:

```text
load_chunks
safe_metadata
tokenize
vector_search
bm25_search
rrf_fuse
```

If code reuse is easy, move shared retrieval helpers into a small module:

```text
scripts/retrieval_utils.py
```

Then update both:

```text
scripts/eval_retrieval.py
scripts/ask_chunks.py
```

to import from it.

If refactoring risks breaking existing eval behavior, do not refactor yet. In that case, duplicate the small helper functions in `ask_chunks.py` and leave a TODO comment.

Priority:

1. Working answer slice
2. No regression in eval
3. Clean refactor only if safe

---

## Prompt format

The prompt sent to the local LLM must be strict and citation-oriented.

Use this system message:

```text
You are a technical documentation assistant.
Answer only using the provided context.
If the provided context is not sufficient, say: "The provided context is not sufficient to answer this question."
Do not use outside knowledge.
Always cite sources using the provided source ids like [S1], [S2].
Keep the answer concise and technical.
```

Use this user message structure:

```text
Question:
<question>

Context:
[S1]
source: <source>
pages: <page_start>-<page_end>
chunk_id: <chunk_index>
text:
<context text>

[S2]
source: <source>
pages: <page_start>-<page_end>
chunk_id: <chunk_index>
text:
<context text>

...

Answer requirements:
- Answer only from the context above.
- Include citations like [S1] or [S2].
- If the context is insufficient, say so explicitly.
```

---

## Output format

The script output must be human-readable.

Example output:

```text
Question:
What does the Interrupt Router module schedule?

Retrieval:
mode: hybrid
top_k: 5

Sources:
[S1] pages 1364-1365 chunk=0 score=...
[S2] pages 1366-1366 chunk=1 score=...

Answer:
The Interrupt Router schedules service requests from peripherals and software to service providers such as CPUs or the DMA module. [S1]
```

If dry-run:

```text
DRY RUN - no model call performed

Question:
...

Sources:
...

Prompt:
...
```

---

## Local LLM API behavior

Use Python standard libraries where reasonable.

Allowed dependency:

```text
requests
```

`requests` is already expected in the project dependencies.

Call:

```text
POST <base-url>/chat/completions
```

Example payload:

```json
{
  "model": "local-model",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.0,
  "max_tokens": 512
}
```

Handle errors clearly:

- connection refused
- HTTP error
- malformed response
- missing answer content

If the model endpoint is unavailable, print a clear error and suggest using `--dry-run`.

Do not crash with a long stack trace for normal endpoint errors.

---

## Suggested first test questions

Create:

```text
examples/rag_answer_questions.txt
```

Include these questions:

```text
What does the Interrupt Router module schedule?
What does the SRPN field define in the SRC register?
Which TOS encoding maps a service request to DMA?
What sequence is required to change SRC TOS or SRPN for an enabled Service Request Node?
Does the PMI provide automatic cache coherency support?
What synchronization instructions are required when changing PMA registers to maintain coherency?
What does the Boot Mode Header contain?
How is a valid Boot Mode Header selected?
```

These questions intentionally reuse already evaluated slices.

---

## README update

Add a section to `README.md`:

```md
## First Grounded RAG Answer
```

Include:

1. how to rebuild a focused index, or reference existing focused index sections
2. how to run dry-run
3. how to run with local LLM endpoint
4. explanation that retrieval eval remains the regression gate
5. warning that answer quality must not be trusted unless citations are present and retrieval hit is good

Example README commands:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --model local-model \
  --base-url http://localhost:8000/v1
```

---

## Optional baseline document

If a local LLM endpoint is available, create:

```text
eval/rag_answer_first_baseline.md
```

Include:

```text
model:
base_url:
retrieval mode:
top_k:
focused index:
questions tested:
observations:
known limitations:
```

If no local LLM endpoint is available, do not fake results.

Instead write:

```text
Answer generation baseline not run because no local LLM endpoint was available.
Dry-run was verified.
```

---

## Verification commands

Run these before finishing:

```bash
python -m py_compile scripts/ask_chunks.py
```

If `python` is not available, use:

```bash
python3 -m py_compile scripts/ask_chunks.py
```

Run dry-run:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

If `python` is not available, use:

```bash
python3 scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

Run existing retrieval evals to ensure no regression:

```bash
python scripts/eval_retrieval.py --mode hybrid --eval eval/boot_bmhd_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/dma_cache_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/interrupt_routing_eval.json
```

If only the current focused index is available, at minimum run the eval that matches the current focused index.

Do not claim all evals passed unless they were actually run against the correct focused indexes.

Run whitespace check:

```bash
git diff --check
```

Check worktree:

```bash
git status --short
```

---

## Acceptance criteria

The task is complete when:

- `scripts/ask_chunks.py` exists.
- `--dry-run` works without any LLM endpoint.
- The script retrieves context using `--mode hybrid` by default.
- The prompt contains source ids `[S1]`, `[S2]`, etc.
- The model instructions require answers only from context.
- The output displays sources and answer separately.
- README contains a short usage section.
- `examples/rag_answer_questions.txt` exists.
- Existing retrieval eval behavior is not intentionally changed.
- No cloud or proprietary model API is introduced.

---

## Suggested commit message

```bash
git commit -m "Add first grounded RAG answer CLI"
```

---

## Final response format for executor

When done, report exactly:

```text
Implemented:
- ...

Verified:
- ...

Results:
- dry-run: pass/fail
- local LLM call: pass/fail/not run
- retrieval eval regression: pass/fail/not run

Changed files:
- ...

Known limitations:
- ...

Commit:
- <commit hash if committed, otherwise not committed>
```
