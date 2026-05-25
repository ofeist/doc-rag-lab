# Manual RAG Answer Evaluation

Model: `gpt-5.5`  
Endpoint: `https://api.openai.com/v1`  
Retrieval mode: `hybrid`  
top_k: `3`  
candidate_k: `8`  

## Summary

This manual evaluation checks whether the first grounded RAG answer path can produce useful, cited, context-grounded answers.

Retrieval remains the regression gate. Answer quality is only meaningful when the relevant source pages are retrieved.

## Results

| ID | Question | Main source page | Citation present | Grounded | Hallucination | Result |
|---|---|---:|---|---|---|---|
| irq-003 | What does the SRPN field define in the SRC register? | 1367 | yes | yes | no obvious hallucination | PASS |
| irq-004 | Which TOS encoding maps a service request to DMA? | 1368 | yes | yes | no obvious hallucination | PASS |
| irq-005 | What sequence is required to change SRC TOS or SRPN for an enabled Service Request Node? | 1370 | yes | yes | no obvious hallucination | PASS |
| irq-007 | What is the purpose of SETR and CLRR in the Service Request Control Register? | 1372 | yes | yes | no obvious hallucination | PASS |

## Observations

- The live OpenAI-compatible answer path works end-to-end.
- Answers include source citations such as `[S1]` and `[S2]`.
- The model correctly uses retrieved context instead of answering from general knowledge.
- Hybrid retrieval is sufficient for answer generation in this focused interrupt-routing slice.
- `hit@3 = 100%` remains the key retrieval signal for this answer workflow.
- The Chroma telemetry warning does not affect retrieval or answer generation.

## Known limitations

- This is still a small manual evaluation.
- Only one focused document slice was tested for answer quality.
- The evaluation is not automated yet.
- Citation correctness is checked manually.
- Future slices should write structured JSONL outputs for easier comparison across models.
