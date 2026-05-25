# RAG Answer Model Comparison

Focused index: Interrupt routing  
Retrieval mode: hybrid  
top_k: 3  
candidate_k: 8  
Endpoint: OpenAI-compatible API  

## Summary

This comparison checks whether smaller/cheaper models can answer grounded technical-documentation questions when retrieval already provides the correct context.

## Results

| Question | gpt-5.5 | gpt-5.4-mini | gpt-5.4-nano | Notes |
|---|---|---|---|---|
| What does the SRPN field define in the SRC register? | PASS | PASS | PASS | All models used the relevant `[S2]` source. |
| What sequence is required to change SRC TOS or SRPN for an enabled Service Request Node? | PASS | PASS | PASS+ | `gpt-5.4-nano` gave the most explicit step-by-step answer among the smaller models. |
| What is the purpose of SETR and CLRR in the Service Request Control Register? | PASS | PASS | PASS+ | `gpt-5.4-nano` included more detailed bit behavior. |

## Observations

- Smaller models performed well when the relevant context was present in top 3.
- `gpt-5.4-mini` produced shorter but acceptable answers.
- `gpt-5.4-nano` produced surprisingly complete answers on the tested questions.
- No obvious hallucinations were observed in these runs.
- Citation behavior was acceptable across all tested models.
- Retrieval quality remains the key dependency.

## Preliminary conclusion

For simple and medium technical RAG questions, a smaller/cheaper model may be sufficient if hybrid retrieval reliably places the relevant source in the context window.

This is not yet a general conclusion. The next stress tests should include:
- questions requiring multi-page synthesis,
- table-heavy content,
- memory-map/address-range lookup,
- insufficient-context questions.
