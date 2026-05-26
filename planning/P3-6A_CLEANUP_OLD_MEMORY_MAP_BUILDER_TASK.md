# P3-6A Task — Cleanup Old Memory-Map-Specific Table Builder

## Purpose

This task removes the old memory-map-specific table-aware chunk builder after P3-5 introduced a generalized builder.

This is a **cleanup-only task**.

Do **not** add new retrieval ideas.
Do **not** change answer generation.
Do **not** run model/API calls.
Do **not** modify the normal ingest pipeline.

---

## Background

P3-2 introduced a memory-map-specific experimental table-aware chunk builder:

```text
scripts/build_memory_map_table_chunks.py
```

P3-5 introduced a generalized experimental table-aware chunk builder:

```text
scripts/build_table_aware_chunks.py
```

P3-5 validation showed that the generalized builder preserves the old behavior:

```text
old vs new output: 0 differences except chunk_id
bm25:              80 / 80 / 100
bm25_table_boost:  80 / 100 / 100
```

Therefore the old memory-map-specific script is now superseded.

The new canonical builder is:

```text
scripts/build_table_aware_chunks.py
```

---

## Goal

Remove the old memory-map-specific builder safely.

Preferred outcome:

```text
scripts/build_memory_map_table_chunks.py is deleted
```

All documentation should point to the generalized builder instead:

```text
scripts/build_table_aware_chunks.py
```

---

## Very Important Rules

Follow these rules strictly.

### Allowed changes

You may change:

```text
scripts/build_memory_map_table_chunks.py
docs/*.md
README.md
```

You may delete:

```text
scripts/build_memory_map_table_chunks.py
```

You may update documentation that still references the old script.

### Forbidden changes

Do **not** change:

```text
scripts/chunk_pages.py
scripts/ingest_document.py
scripts/ask_chunks.py
scripts/embed_chunks.py
scripts/eval_retrieval.py
```

Do **not** add new retrieval modes.

Do **not** modify answer generation.

Do **not** commit generated files under:

```text
data/
vector_db/
```

Do **not** commit:

```text
data/chunks_table_aware_memory_map.jsonl
data/chunks_memory_map_baseline_300_60.jsonl
vector_db/chroma
```

---

## Step 1 — Inspect Current Git State

Run:

```bash
git status --short
```

Expected clean-ish state before work:

```text
(no output)
```

or only files you intentionally know about.

If there are unrelated modified files, stop and report them.

---

## Step 2 — Search for References to the Old Script

Run:

```bash
grep -R "build_memory_map_table_chunks" -n . \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=vector_db \
  --exclude="*.pyc"
```

Look for references in:

```text
docs/
README.md
scripts/
```

Also run:

```bash
grep -R "chunks_table_aware_memory_map" -n docs scripts README.md 2>/dev/null || true
```

This second command is not necessarily a problem. The output file name may still be valid. We only need to make sure the command that generates it uses the new generalized builder.

---

## Step 3 — Update Documentation References

Wherever documentation tells users to run:

```bash
.venv/bin/python scripts/build_memory_map_table_chunks.py
```

replace it with the generalized builder command:

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

Likely files to check:

```text
docs/MEMORY_MAP_TABLE_AWARE_EXPERIMENT.md
docs/TABLE_AWARE_BUILDER_INTERFACE.md
docs/MEMORY_MAP_TABLE_RANKING_EXPERIMENT.md
docs/TABLE_RETRIEVAL_DESIGN_DECISION.md
docs/PHASE2_SUMMARY.md
RAG_ROADMAP_TO_SPACESHIP.md
README.md
```

Only edit files that actually contain old or outdated references.

If a document mentions the old script historically, keep that history only if useful, but make the current instruction clear:

```text
The old memory-map-specific builder was replaced by scripts/build_table_aware_chunks.py.
```

---

## Step 4 — Delete the Old Script

After documentation is updated, delete the old script:

```bash
git rm scripts/build_memory_map_table_chunks.py
```

Do not leave two implementations unless deletion breaks an important documented command.

The goal is to avoid duplicate code paths.

---

## Step 5 — Verify the New Canonical Builder Still Works

Run syntax check:

```bash
.venv/bin/python -m py_compile scripts/build_table_aware_chunks.py
```

Expected result:

```text
(no output)
```

If there is a syntax error, fix it before continuing.

---

## Step 6 — Run the Generalized Builder Smoke Test

Run:

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

Expected output should be similar to:

```text
Wrote 102 chunks to data/chunks_table_aware_memory_map.jsonl
  table_row_group chunks : 91  (298 rows)
  generic_residual chunks: 11
  pages covered          : [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102]
  segment markers        : accepted=31 skipped=0
```

The exact formatting may differ, but the important values are:

```text
102 chunks
91 table_row_group chunks
11 generic_residual chunks
pages 90-102 covered
```

If the generated chunk counts are very different, stop and report the difference.

---

## Step 7 — Embed the Generated Chunks

Run:

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

Expected result should include something like:

```text
Collection count: 102
```

If the collection count is not 102, stop and report it.

---

## Step 8 — Run Retrieval Eval

Run the table-boost eval:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Expected result:

```text
hit@1: 8/10 = 80.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

If the result differs slightly, report it.
If `hit@3` drops below 100%, do not commit until reviewed.

Also run plain BM25:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25 \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Expected result:

```text
hit@1: 8/10 = 80.00%
hit@3: 8/10 = 80.00%
hit@5: 10/10 = 100.00%
```

---

## Step 9 — Confirm Generated Files Are Ignored

Run:

```bash
git check-ignore -v data/chunks_table_aware_memory_map.jsonl vector_db/chroma
```

Expected: both paths should be ignored.

If `data/chunks_table_aware_memory_map.jsonl` is not ignored, do not add it to git.

Also check status:

```bash
git status --short
```

Expected changed files should include only source/docs, for example:

```text
D  scripts/build_memory_map_table_chunks.py
M  docs/MEMORY_MAP_TABLE_AWARE_EXPERIMENT.md
M  docs/TABLE_AWARE_BUILDER_INTERFACE.md
```

There may be fewer or more docs depending on references found.

There should be no staged or unstaged generated files under:

```text
data/
vector_db/
```

---

## Step 10 — Check Formatting

Run:

```bash
git diff --check
```

Expected:

```text
(no output)
```

If there are whitespace errors, fix them.

---

## Step 11 — Review Final Diff

Run:

```bash
git diff --stat
```

Expected:

```text
scripts/build_memory_map_table_chunks.py deleted
some docs updated
```

Also run:

```bash
git diff -- scripts/build_memory_map_table_chunks.py
```

This should show deletion only.

Run:

```bash
git diff -- docs
```

Check that docs now point to:

```text
scripts/build_table_aware_chunks.py
```

and not to:

```text
scripts/build_memory_map_table_chunks.py
```

---

## Step 12 — Stage Changes

Use:

```bash
git add docs
git rm scripts/build_memory_map_table_chunks.py
```

If `git rm` was already run earlier, this is okay.

Do **not** run:

```bash
git add data
git add vector_db
git add .
```

Avoid `git add .` in this task.

---

## Step 13 — Final Status Check Before Commit

Run:

```bash
git status --short
```

Expected staged files:

```text
D  scripts/build_memory_map_table_chunks.py
M  docs/...
```

Maybe also:

```text
M  README.md
```

Only if README actually changed.

No `data/` files.
No `vector_db/` files.

---

## Step 14 — Commit

Commit with:

```bash
git commit -m "Remove superseded memory map table builder"
```

---

## Step 15 — Report Back

Return a short report with:

```text
- deleted files
- updated docs
- verification commands run
- retrieval result
- git commit hash
```

Example:

```text
Deleted:
- scripts/build_memory_map_table_chunks.py

Updated:
- docs/MEMORY_MAP_TABLE_AWARE_EXPERIMENT.md
- docs/TABLE_AWARE_BUILDER_INTERFACE.md

Verification:
- py_compile OK
- generalized builder produced 102 chunks
- embed collection count 102
- bm25_table_boost: 80 / 100 / 100
- plain bm25: 80 / 80 / 100
- git diff --check OK

Commit:
- <hash> Remove superseded memory map table builder
```

---

## Done Criteria

This task is done only when all conditions are true:

```text
scripts/build_memory_map_table_chunks.py is removed
documentation no longer instructs users to run the old script
scripts/build_table_aware_chunks.py is the canonical table-aware builder
memory_map retrieval result is preserved
generated JSONL files are not committed
vector DB files are not committed
normal ingest pipeline remains unchanged
commit is created
```

---

## Stop Conditions

Stop and report instead of committing if any of these happen:

```text
generalized builder fails
generated chunk count is very different from 102
embedding collection count is not 102
bm25_table_boost hit@3 drops below 100%
generated data/ or vector_db/ files appear staged
docs still point users to the old script
unrelated files are modified
```
