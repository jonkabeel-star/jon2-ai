# Jon2 AI — Data preparation

## What this stage does
1. Streams a limited sample of ArabicText-Large instead of downloading its entire multi-gigabyte corpus.
2. Filters short/non-Arabic-heavy rows and removes URLs/formatting noise.
3. Removes exact duplicate articles.
4. Saves the sample locally for the Jon2 training script.

## Important rights gate
The dataset card says Apache-2.0, but sample rows identify Wikipedia as a source. A dataset packaging license does not automatically replace the licenses of underlying source text. The candidate is marked NOT APPROVED in `DATASET_REGISTER.md`. Do not run the downloader for public/commercial training until the underlying rights and obligations have been reviewed and documented.

## Run in Google Colab (no terminal app needed)
1. Open the notebook `Jon2_AI_Data_Stage3.ipynb` from this repository in Google Colab.
2. Read the rights checklist in the first cell.
3. Only if the dataset rights are confirmed for the intended use, change `RIGHTS_REVIEWED = False` to `True` in the notebook.
4. Run the cells from top to bottom. The first sample is capped at 5,000 articles / 2 million characters and is stored in the Colab runtime, not committed to GitHub.
5. Training is a separate next stage. Do not expect this data preparation step to make the model intelligent by itself.

## Files
- `download_arabic_corpus.py`: bounded streaming downloader and basic cleaner.
- `DATASET_REGISTER.md`: source/license audit record.
- `data-requirements.txt`: data preparation dependency.
