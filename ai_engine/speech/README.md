# Jon2 AI speech research pipeline

This folder is reserved for a rights-cleared, independently trained Jon2
text-to-speech system. The current website's browser speech feature is only a
temporary device voice; it is not a Jon2 TTS model.

## Data-source candidates (not yet approved for ingestion)

1. **Mozilla Common Voice Scripted Speech 27.0 — Arabic**: the Mozilla Data
   Collective currently lists a 3.30 GB Arabic speech dataset under CC0-1.0.
   It is an ASR-oriented read-speech corpus, not a ready-made Egyptian TTS
   voice. Its terms forbid speaker identification and re-hosting/re-sharing.
   Candidate source: https://mozilladatacollective.com/datasets/cmu5wom3z00ceo107guxtg4xa
2. **Arabic Speech Corpus by Nawar Halabi**: 1,813 WAV recordings, recorded in a
   professional studio in a Damascene/Levantine accent, released under CC BY
   4.0. It is not Egyptian Arabic and is too small to assume it can produce a
   robust natural voice by itself. Candidate source:
   https://www.arabicspeechcorpus.com/

These are candidates for manual review, not approvals. Before use, verify the
current dataset card, underlying recording rights, attribution obligations,
speaker restrictions, allowed ML/TTS use, and redistribution rules. Do not
identify speakers, clone a real person's voice, or publish/re-share source
audio where the source terms prohibit it. No external speech data has been
downloaded or added to this repository.

## Required sample manifest

The validator in ai_engine/speech_dataset.py accepts a reviewed JSON manifest
containing:
- dataset ID, exact license, documented rights basis, reviewer, review date,
  and intended use;
- status APPROVED only after a human rights review;
- speaker_identification_allowed set to false;
- each WAV's relative path, SHA-256, Arabic transcript, and anonymized speaker
  ID.

The validator accepts mono 16-bit PCM WAV files sampled at 16–48 kHz, 0.5–20
seconds per clip. It rejects changed/unlisted files, duplicate paths or
transcripts, missing approvals, invalid transcripts, and unsafe paths. It
reports metadata only and never uploads audio or starts training.

Run it after a source-specific manifest has been reviewed:

    python -c "from pathlib import Path; from ai_engine.speech_dataset import validate_speech_manifest; print(validate_speech_manifest(Path('speech/manifest.json'), Path('speech/audio')))"

A passing structural check is not proof of transcript accuracy, voice consent,
license compatibility, or natural-sounding synthesis. A dedicated TTS model
still needs a separately designed architecture, substantial approved paired
audio/text, training compute, and human pronunciation evaluation.
