# Dataset source-rights recheck — 2026-11-25

This is a research intake note, not legal advice or an approval to download/train. No dataset was downloaded and no gated terms were accepted.

## ShawarmaChats / arabic_multi_dialect_dialogue

- Dataset card: https://huggingface.co/datasets/Kamyar-zeinalipour/arabic_multi_dialect_dialogue
- Declared license: CC BY-SA 4.0.
- Card describes 30,012 six-turn dialogues (28,500 train / 1,512 test) in MSA, Egyptian and Maghrebi.
- Card says source paragraphs are Arabic Wikipedia and dialogue turns were generated with Gemini 2.5 Flash, graded/repaired with GPT-4o, with a small remainder corrected by native speakers.
- Decision: keep as a strong *candidate*, not approved. Preserve official train/test; keep the test split held out. Review ShareAlike consequences for trained weights and downstream distribution, dataset paper, source attribution, exact immutable revision, and whether AI-generated derivative text is compatible with the intended use. No intake until a human records approval in the private manifest.

## Alexandria

- Current dataset card: https://huggingface.co/datasets/UBC-NLP/alexandria
- Current page currently displays CC BY-NC 4.0 and an Egyptian subset of about 1.7K rows.
- A pinned historical README revision: https://huggingface.co/datasets/UBC-NLP/alexandria/blob/fc9d1f14bdc49562e086b21938929ca749153432/README.md displays CC BY-NC-ND 4.0.
- Decision: quarantine because the license declarations conflict across revisions. Do not train, transform, or ingest until the rights holder resolves the exact revision/license in writing. Do not infer that the current badge retroactively changes the pinned revision's terms.

## 4FACTORS Egyptian sample

- Dataset card: https://huggingface.co/datasets/4factors/arabic-egyptian-sample
- Card describes 50 native-written Egyptian Q&A pairs, CC BY-NC 4.0, and attribution/provenance information.
- Current page displays a Request access gate.
- Decision: do not request access, submit personal/account details, or accept terms on the user's behalf. If the owner later grants access and the exact terms are reviewed, this small sample may support a human-reviewed Egyptian smoke test; it is far too small for pretraining.

## Consequence for the project

- No source is approved by this note.
- Keep raw source files out of Git and store any approved material only in private storage.
- The original `jon2-last.pt` remains unchanged.
- Training remains blocked by the separate zero-cost GPU and corpus-capacity gates.
