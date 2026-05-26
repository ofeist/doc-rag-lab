## Next Step: First Grounded RAG Answer Slice

The retrieval evaluation is now strong enough to start testing grounded answer generation.

### Proposed next steps

0. cleanup docs/ folder
	- .MD files shall be moved to more appropriate location

1. Create or improve `ask_chunks.py`.

2. Use hybrid retrieval as the default context source.

3. Pass the top 3 or top 5 retrieved chunks to the local LLM.

4. Test answers using questions from the existing eval sets:
   - Boot/BMHD
   - DMA/cache
   - Interrupt routing

5. Require answers to include citations.

6. Require the model to say “I don’t know” or “The provided context is not sufficient” when the retrieved context does not support an answer.

7. Compare answer quality against retrieval results:
   - Did the correct chunk appear in top 3/top 5?
   - Did the model use the correct source?
   - Did the model hallucinate?
   - Were citations correct?
   - Was the answer useful for a technical user?

8. Keep retrieval eval as the regression gate before trusting answer generation.

9. Model selection note for later:

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


