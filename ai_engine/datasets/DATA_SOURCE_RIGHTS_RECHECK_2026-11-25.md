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


## Bayanat Labs Open Arabic Books

- Dataset: https://huggingface.co/datasets/Bayanat-Labs/open-arabic-books
- Dataset card: https://www.bayanatlabs.com/open/open-arabic-books
- Declared release licence: CC BY 4.0 for dataset rows, metadata and documentation; builder code Apache-2.0.
- Reported release: 1,545 books, 27,544 chapter rows, 54,204,272 body-text words.
- Rights nuance: each book's colophon was read. The card reports 1,212 books with original Arabic text stated public domain and design CC BY 4.0; 332 translations with Arabic translation and design CC BY 4.0; one book with original text CC BY 3.0. Other source-corpus books were excluded for missing/contradictory rights evidence.
- Decision: strong general-Arabic text candidate, not dialogue. Require per-record metadata/colophon filtering, retain all attribution, and review publisher public-domain statements against applicable Egyptian law before approval. Dataset-level CC BY 4.0 is not a substitute for checking each book's source-rights statement. No download or approval.

## Bayanat Labs Arabic Wikipedia Monthly — Egyptian Arabic

- Dataset: https://huggingface.co/datasets/Bayanat-Labs/arabic-wikipedia-monthly
- Dataset card: https://www.bayanatlabs.com/open/arabic-wikipedia-monthly
- Declared licence: CC BY-SA 4.0 for article text; CC BY 4.0 for labels/documentation.
- Reported Egyptian (arz) subset: 1,632,785 articles with running text; 1,580,156 are rule-flagged template-generated and 50,971 rule-flagged individually written. The combined 119,064,440 word count covers Arabic, Egyptian and Moroccan text configs and must not be attributed to Egyptian alone.
- Decision: strong Egyptian-script text candidate, not dialogue. Start review with the individually-written subset only; its generation flag is rule-based and needs sample checks. Preserve exact revision links and attribution. Review ShareAlike implications, vandalism, stale facts, bias, privacy and biographies of living people. No download or approval.


## UBC-NLP LHV-Egypt

- Dataset: https://huggingface.co/datasets/UBC-NLP/nilechat-lhv-egy
- Declared licence: CC BY-NC 4.0; reported size 1.49M rows and 1.98 GB.
- The card describes controlled generation using CohereLabs/c4ai-command-r-plus-08-2024, drawing on local news websites, Wikipedia portals, local cultural/linguistic sources and WVS-based personas. Genres include stories, essays, blogs, reviews and conversations.
- Hugging Face currently requires agreement to share account information before files can be accessed. No agreement or access request was made.
- Decision: promising Egyptian text candidate for private non-commercial research only, subject to exact access terms, teacher-model/source provenance, attribution and quality review. Do not use commercially under the displayed NC licence without separate permission. Do not assume every row is dialogue. No download or approval.

## Prickly Labs 1.9M Egyptian Corpus

- Dataset: https://huggingface.co/datasets/Prickly-Labs/1.9M-Egyptian-Corpus
- Declared licence: CC BY-SA 4.0; 1,922,049 rows. Dataset-card size is approximately 648 MB; another catalog reports approximately 617.7 MB.
- Card says the majority is synthetic (Gemini API / LearnLM) and a minority is scraped from Egyptian Reddit communities.
- The card states that models or datasets derived from this work must be released under CC BY-SA 4.0.
- Decision: quarantine pending Reddit user-content rights, privacy/platform terms, source provenance, and written analysis of the model-weight ShareAlike condition. Synthetic quality and teacher-model provenance also need review. No download or approval.
