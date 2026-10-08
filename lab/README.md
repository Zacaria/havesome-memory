# Morrow Works scenario test

Ten questions about the fictional Morrow Works files, put to five memory systems and a plain keyword search.
Run 7–8 October 2026. This is a small scenario test, not a general benchmark and not a security audit.

## Results

| System | Version | Score | Avg. passages handed to the answer model |
|---|---|---|---|
| Hindsight | 0.10.2 (Docker) | 10/10 | 68 |
| Mem0 OSS | 2.2.1 (library) | 10/10 | 8 |
| OpenViking | 0.4.23 | 10/10 | 5 (whole files) |
| Keyword search (baseline) | `adapters/keyword.py` | 9/10 | 6 |
| Microsoft GraphRAG | 3.2.0 | 7/10 | 7 |
| Supermemory local | 0.0.8 (free "lite" binary) | 6/10 | 2.5 |

Raw answers, citations and every retrieved passage: `results/<system>.json`.

## How it runs

1. `run.py` replays `corpus.json` in `ingested_at` order. Before each question it ingests only files that existed on that date.
2. On 15 May 2027 it deletes S10, as the scenario requires.
3. Each adapter retrieves passages for the question and the reader's role.
4. The same answer model gets the same prompt and only those passages. It returns `status`, `answer` and `citations` in a fixed JSON schema.
5. `score()` applies plain string checks from `questions.json`: expected status, expected values, required citations, and passages that must not appear.

Answer model: `gpt-6.1-sol` through the Codex CLI, the same for every system. Each memory system did its own extraction with `qwen3:14b` served by Ollama. Embeddings came from `nomic-embed-text`, except where a system ships its own local embedder (Hindsight, Supermemory). Everything ran self-hosted on one isolated VM.

## What each adapter adds

- **Roles:** Hindsight tags, Mem0 metadata filters, Supermemory metadata filters, OpenViking retrieval tags. GraphRAG and the keyword baseline have no access control, so they get none.
- **Dates:** Hindsight gets each file's recorded timestamp. Mem0 OSS rejects `timestamp`/`reference_date` (platform-only), so the recorded date is written into the text. OpenViking, Supermemory and GraphRAG also get the date in the text.
- **Deletion:** each system's own delete by document or source. GraphRAG has no per-document delete, so the adapter deletes the input file and rebuilds the index.
- **OpenViking:** search returns file summaries, so the adapter then reads the matched files, the find-then-read flow its docs describe.

## Read the scores with these limits

- **Supermemory's 6 is generous.** Its search returned nothing for 6 of 10 questions. 3 of those still passed, because the expected answer was "unknown" or a refusal. Short keyword queries did find the right files, so its default hybrid search struggles with full-sentence questions on this setup.
- **The test does not separate the top systems.** Keyword search gets 9/10. The deletion and expired-instruction questions only check that the answer says "unknown", which an empty search also produces.
- **Context size is not scored.** Hindsight passed with about 70 passages per question; the others got 5 to 8.
- **One run each.** Extraction uses an LLM, so a rerun can differ.
- **Small local extraction model.** Systems tuned for larger hosted models may do better with them.

## Reproduce

Point the adapters at your own hosts (`memory-lab`, `ollama-host` are placeholders), start each service as described in its adapter header, then run:

```
python3 run.py <adapter>      # keyword | hindsight | mem0 | supermemory | openviking | graphrag
```
