# P3-25 Task - README / CLI Polish for Integrated RAG Workflow

## Goal

Polish the root `README.md` so a new user can run the project without reading
every experiment doc.

Docs-only task.

## Context

Phase 3 integration is complete:

```text
ingest_document.py --chunk-mode mixed
schema-compatible chunks
chunk_type persisted in Chroma metadata
retrieval --mode auto
artifact cleanup and guardrails
pytest coverage
full-document mixed ingest smoke completed
```

Important docs:

```text
docs/PHASE3_INTEGRATION_CHECKPOINT.md
docs/experiments/FULL_DOCUMENT_MIXED_INGEST_SMOKE.md
docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md
```

## Required README Structure

Update `README.md` with practical, current CLI-first sections:

1. Project purpose
2. What currently works
3. Setup
4. Input document
5. Generic ingest
6. Mixed ingest
7. Full-document mixed ingest smoke
8. Retrieval eval
9. Ask chunks / dry-run answer context
10. Answer generation
11. Tests
12. Generated artifacts and cleanup behavior
13. Offline/cache notes
14. Known limitations
15. Useful docs

Keep README concise; do not turn it into an experiment log.

## Required Content Notes

- Use pinned dependency commands:
  - `pip install -r requirements-rag.txt`
  - `pip install -r requirements-dev.txt`
- Input PDF examples use:
  - `docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf`
- Add "Input document location" note:
  - PoC keeps docs + sample/vendor PDF under `docs/`
  - future cleanup may move PDFs to `source_docs/`
- Add link next to the AURIX PDF mention:
  - `https://documentation.infineon.com/aurixtc3xx/docs/qmd1702366622648`
- Document `--mode auto` selection logic and that it is opt-in.
- Document mixed ingest artifact cleanup behavior and `--keep-intermediate-artifacts`.
- Correct `embed_chunks.py` canonical flags (`--chunks`, `--db`, `--collection`, `--reset`).

## Verification

```bash
git diff --check
git status --short
```

No code changes.

## Commit

```bash
git commit -m "Polish README CLI workflow"
```

