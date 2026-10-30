# Jon2 AI training data folder

Add UTF-8 plain-text files ending in `.txt` here only when Jon2 has the right to use them for model training.

## Before adding any dataset
1. Record the exact source and download date.
2. Read the dataset license and confirm that machine-learning training is permitted.
3. Do not include private messages, personal records, passwords, or confidential material.
4. Keep a copy of the license and attribution requirements outside the training text.
5. Deduplicate and clean the text; remove markup and harmful personal data where appropriate.

## Dataset register
Create or update `DATASET_REGISTER.md` with:
- Dataset name
- Original source / owner
- License and link to license terms
- Date obtained
- Allowed use (including model training)
- Cleaning and filtering performed

The training script reads `.txt` files recursively from this folder. It does not fetch datasets from the internet.
