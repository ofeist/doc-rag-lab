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

This task must add a small, reproducible answer-generation layer that uses the existing hybrid retrieval results as context and calls an OpenAI-compatible chat completions endpoint.

The first implementation must support `--dry-run`, so retrieval, context packing, and prompt construction can be tested without calling any model.

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

Do not hardcode Ollama.

Do not assume a local model runtime exists.

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

The model call must use an OpenAI-compatible endpoint.

This may be:

```text
OpenAI API from home
company-local OpenAI-compatible endpoint
vLLM OpenAI-compatible server
Ollama OpenAI-compatible endpoint
any compatible internal gateway
```

The task must not depend on one specific provider.

Default endpoint:

```text
https://api.openai.com/v1
```

Default model placeholder:

```text
gpt-5.5
```

The model and endpoint must be configurable by CLI.

The API key must be read from an environment variable, not hardcoded.

Default environment variable:

```text
OPENAI_API_KEY
```

The script must also support `--dry-run`, so retrieval/context/prompt can be tested even when no endpoint or API key is available.

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
  --model gpt-5.5 \
  --base-url https://api.openai.com/v1
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
--model           Default: gpt-5.5
--base-url        Default: https://api.openai.com/v1
--api-key-env     Default: OPENAI_API_KEY
--temperature     Default: 0.0
--max-tokens      Default: 512
--dry-run         If present, do not call the model.
--show-context    If present, print full retrieved context.
```

Do not add a positional API key argument.

Do not print the API key.

Do not read secrets from `.env` unless the project already has an established `.env` loader.

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

The prompt sent to the model must be strict and citation-oriented.

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

## OpenAI-compatible API behavior

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

For the default OpenAI API base URL, that means:

```text
POST https://api.openai.com/v1/chat/completions
```

Headers:

```text
Authorization: Bearer <value from api-key-env>
Content-Type: application/json
```

Example payload:

```json
{
  "model": "gpt-5.5",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.0,
  "max_tokens": 512
}
```

Handle errors clearly:

- missing API key environment variable
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
3. how to run with an OpenAI-compatible endpoint
4. how to set the API key via environment variable
5. explanation that retrieval eval remains the regression gate
6. warning that answer quality must not be trusted unless citations are present and retrieval hit is good

Example README dry-run command:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

Example README command with OpenAI API:

```bash
export OPENAI_API_KEY="..."

python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --model gpt-5.5 \
  --base-url https://api.openai.com/v1
```

Example README command with another OpenAI-compatible endpoint:

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

If an OpenAI-compatible endpoint is available, create:

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

If no endpoint is available, do not fake results.

Instead write:

```text
Answer generation baseline not run because no OpenAI-compatible endpoint was available.
Dry-run was verified.
```

If OpenAI API is used from home, write that clearly, but do not include API keys or sensitive account details.

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

Optional real model call, only if an endpoint and API key are available:

```bash
export OPENAI_API_KEY="..."

python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --model gpt-5.5 \
  --base-url https://api.openai.com/v1
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
- `--dry-run` works without any model endpoint.
- The script retrieves context using `--mode hybrid` by default.
- The prompt contains source ids `[S1]`, `[S2]`, etc.
- The model instructions require answers only from context.
- The output displays sources and answer separately.
- The OpenAI-compatible endpoint is configurable via `--base-url`.
- The model is configurable via `--model`.
- The API key is read from an environment variable, default `OPENAI_API_KEY`.
- No API key or secret is committed, printed, or hardcoded.
- README contains a short usage section.
- `examples/rag_answer_questions.txt` exists.
- Existing retrieval eval behavior is not intentionally changed.

---

## Model selection note for later

| Step | GPT-5.5? | Note |
|---|---|---|
| Find relevant pages | No | Keyword/PDF search |
| Select page range | Optional | Human decides |
| Extract pages | No | Local script |
| Chunking | No | Local script |
| Embedding/index | No | Local embedding |
| Write 10 questions | Yes, optional | Useful for drafting |
| Verify expected_pages | Not as authority | Human must confirm |
| Run eval | No | Local |
| Debug failures | Optional | Can help interpret results |
| Correct eval targets | Optional | Human confirms |
| Baseline report | Optional | Text only, not metrics |
| README update | Optional | Wording |
| Commit/push | No | Git workflow |

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
- OpenAI-compatible model call: pass/fail/not run
- retrieval eval regression: pass/fail/not run

Changed files:
- ...

Known limitations:
- ...

Commit:
- <commit hash if committed, otherwise not committed>
```
