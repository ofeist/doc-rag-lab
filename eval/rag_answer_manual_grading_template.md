# Manual RAG Answer Grading Template

Use this template for each batch answer-eval JSONL run.

Run metadata:

```text
eval file:
output jsonl:
focused index:
retrieval mode:
top_k:
candidate_k:
rrf_k:
model:
base_url:
date:
grader:
```

Results:

| ID | Question | Model | Retrieved sources | Citation present | Grounded | Hallucination | Result | Notes |
|---|---|---|---|---|---|---|---|---|
| example-id | Example question | example-model | [S1] pX, [S2] pY | yes/no | yes/no/partial | yes/no/unclear | PASS/FAIL/PARTIAL | Short note |

Failure types:

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
endpoint/tooling error
```
