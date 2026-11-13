# Jon2 no-fake-replies policy

This policy applies to every public chat route and the local Safari inference path.

## Absolute rules

1. No canned greetings, hard-coded answers, FAQ question/answer tables, scripted response templates, or fallback text presented as model output.
2. No answer may be returned unless it was generated during that request by the original Jon2 checkpoint that is actually loaded in the runtime.
3. If the checkpoint is absent, not loaded, fails during inference, times out, returns an empty answer, or fails the Arabic output-integrity guard, return exactly:
   `عقل Jon2 غير جاهز للرد`
4. Never substitute a retrieved document, conversation-memory item, placeholder, another model, hosted AI API, or cached answer for Jon2's generation.
5. Conversation history may be passed as context only. It is not an answer bank.
6. A successful code test is not proof of Arabic understanding or factual correctness. Human-reviewed Arabic evaluation is mandatory before public release.

## Arabic quality measurement

- Run the held-out Arabic evaluation set separately from training data.
- Keep MSA and Egyptian Arabic prompts, reasoning, multi-turn context, uncertainty, and safety cases represented.
- Record actual checkpoint SHA-256, tokenizer fingerprint, evaluation prompt-set version, raw generated outputs, and per-question human scores.
- Do not claim a quality improvement unless the same held-out prompts are run against the before/after checkpoints and the results are reviewed.
- The current surface-level output guard detects some malformed/repetitive text only. It does not establish meaning, reasoning, or truth.

## Runtime behavior

The FastAPI chat endpoint calls only `generate_reply` from the original Jon2 runtime. It does not call a canned-response module or retrieval-answer shortcut. The Safari worker rejects failed output instead of displaying it. Runtime and UI failures display the exact not-ready message above.

This policy does not mean the model is ready. It means an unready model stays silent rather than pretending to be intelligent.
