# Grounded RAG Answer Stress Tests

Focused index: Interrupt routing  
Retrieval mode: hybrid  
Model: gpt-5.4-nano  
Endpoint: OpenAI-compatible API  

## Results

| Test | Question | Result | Notes |
|---|---|---|---|
| Insufficient context | What is the maximum CAN bus bitrate supported by this device? | PASS | Correctly refused to answer from unrelated interrupt context. |
| Multi-source synthesis | How are service requests routed from an SRN to a CPU or DMA service provider? | PASS | Combined SRC.TOS, SRC.SRPN, CPU/DMA handling, and ICU arbitration. |
| Table lookup | Which TOS encodings map service requests to CPU0, DMA, CPU1, CPU2, CPU3, CPU4, and CPU5? | PASS | Correctly listed TOS encodings from the retrieved table. |

## Conclusion

`gpt-5.4-nano` produced grounded, cited answers for simple, medium, insufficient-context, multi-source, and table-lookup questions when hybrid retrieval placed relevant context in the top results.

This does not prove general quality across all documents, but it is a good signal for the current interrupt-routing slice.
