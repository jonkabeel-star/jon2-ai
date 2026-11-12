# Large Arabic Dataset Acquisition — Quarantine Only

## Current decision

The acquisition tool supports one large research candidate:

- Dataset: `mittagessen/openiti_chunked`
- Pinned Hugging Face revision: `edb9823fb63b544a5cd7889b835a2f85146f031a`
- Approximate download: 17.9 GB
- Approximate unpacked dataset size: 38.0 GB
- Hub metadata declares CC0-1.0 for the dataset package.
- The underlying OpenITI 2023.1.8 release documentation states CC BY-NC-SA 4.0. The underlying texts are therefore **not cleared for commercial Jon2 training** by the Hub package label.

The tool writes only to a dedicated quarantine directory, creates a provenance manifest, and hard-codes both `training_eligible` and `commercial_use_eligible` to false. It never writes to `ai_engine/training_data` and never modifies the private source-approval manifest.

`ArabicText-Large` is deliberately not downloadable through this tool: its card declares Apache-2.0, but available metadata does not adequately establish rights for every underlying source subset. Obtain written source-level clarification first.

## Run in a private Colab/Drive workspace

1. Check that the target storage has at least 40 GB free. A standard 15 GB Drive allocation is not enough.
2. Install the optional dependency:

   ```python
   !pip install -r requirements-data.txt
   ```

3. Choose a private destination outside the repository's training-data folder. Do not upload the downloaded corpus to GitHub.
4. Run the downloader only if you accept that the result is for rights and quality inspection, not model training:

   ```python
   !python ai_engine/download_arabic_candidate.py \\
     --dataset openiti_chunked \\
     --destination /content/Jon2_AI_Quarantine/openiti_chunked \\
     --confirm-large-download
   ```

5. Keep the generated `acquisition_manifest.json` with the files. Do not change the eligibility flags to bypass the source-approval gate.

## Next gate

A rights reviewer must resolve the mismatch between the Hub package license and the upstream OpenITI release license, identify any source-specific restrictions, and confirm whether the intended use is non-commercial research only. The current Jon2 platform has a possible public/commercial goal, so this dataset remains excluded from its training corpus unless a lawful commercial permission path is documented.
