# First Grounded RAG Answer Baseline

Focused index:

```text
topic: Interrupt routing
retrieval mode: hybrid
top_k: 3
candidate_k: 8
model: gpt-5.5
base_url: https://api.openai.com/v1

# Question:

What does the SRPN field define in the SRC register?

# Retrieved sources:

[S1] pages 1370-1370 chunk=6
[S2] pages 1367-1367 chunk=3
[S3] pages 1371-1371 chunk=8

# Result:

PASS

# Observed answer quality:

- Answer included citations: yes
- Main citation: [S2]
- Answer used retrieved context: yes
- Answer hallucinated: no obvious hallucination
- Citation quality: good
- Repeated run stability: good

# Notes:

The answer correctly explains that SRPN means Service Request Priority Number and defines the priority of a service request relative to other service requests assigned to the same service provider / SRC.TOS configuration.

Both live OpenAI-compatible API runs produced equivalent grounded answers with citations.

Retrieval eval remains the regression gate before trusting answer generation.
