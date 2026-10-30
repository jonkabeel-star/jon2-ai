# Jon2 Arabic Training Data — Contribution Guide

This folder is reserved for Arabic text that Jon2 is allowed to learn from.

## Do not add data unless all checks pass

1. **Ownership or permission:** The text was written specifically for this project by its contributor, or its license/permission explicitly allows machine-learning training and the intended commercial use.
2. **Privacy:** No private chats, personal records, phone numbers, addresses, passwords, API keys, or identifying details about people.
3. **Quality:** The text is grammatical, useful, non-duplicated, and factually checked where it makes factual claims.
4. **Source record:** Add the source, author/owner, license or written permission, date obtained, and allowed uses to `../DATASET_REGISTER.md`.
5. **Review:** A human reviews the material before it is used for training.

A public URL, a freely downloadable file, or a permissive-looking website notice is not by itself proof that training and commercial use are allowed.

## Preferred formats

### Dialogue examples

Use UTF-8 plain text with one alternating pair per turn:

```text
المستخدم: اشرح مفهومًا محددًا بلغة عربية واضحة.
Jon2: إجابة صحيحة ومباشرة، مع توضيح مناسب.
المستخدم: اسأل سؤال متابعة مرتبطًا.
Jon2: أجب مع الحفاظ على سياق الحوار.
```

Keep the speaker labels exactly as shown. Do not insert a second user line before Jon2 answers.

### Explanatory prose

If adding non-dialogue prose, keep it in a separate clearly named UTF-8 `.txt` file and document its origin and license in the dataset register. Do not disguise copied prose as original dialogue.

## Quality targets

- Modern Standard Arabic by default; avoid accidental language mixing.
- One clear task or subject per example.
- No fabricated citations, quotations, names, or current events.
- State uncertainty when the source material does not support a definite answer.
- Include varied, natural examples; never repeat paragraphs just to reach a character-count threshold.
- Keep training examples separate from held-out evaluation questions.

## Before a dataset is accepted

Run:

```bash
python ai_engine/audit_data.py
```

The audit checks structure and duplicates only. It cannot verify copyright, factual correctness, privacy, or language quality. A passing audit is not approval for training or release.
