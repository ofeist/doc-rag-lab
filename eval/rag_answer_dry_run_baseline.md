# First Grounded RAG Answer Baseline

model: `phi3:latest`  
base_url: `http://localhost:11434/v1`  
retrieval mode: `hybrid`  
top_k: `2`  
focused index: `Interrupt routing (pages 1364-1397)`  
questions tested:
- `What does the Interrupt Router module schedule?`

observations:
- `--dry-run` works and prints question, sources, and full prompt.
- retrieval and context packing are functioning end-to-end in `scripts/ask_chunks.py`.
- OpenAI-compatible call to local endpoint timed out (read timeout 45s) before answer generation completed.

known limitations:
- Answer generation baseline is not complete yet because the endpoint call timed out.
- Retrieval quality remains the regression gate; answer quality should be trusted only with citations and passing retrieval evals.
