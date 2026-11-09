"""Rights-first validation for paired Arabic speech/text data.

This module validates a reviewed manifest and local PCM WAV files. It does not
identify speakers, synthesize speech, train a model, or upload audio.
"""
from __future__ import annotations

import hashlib
import json
import re
import wave
from pathlib import Path, PurePosixPath


_ARABIC = re.compile(r"[\u0621-\u064A\u066E-\u06D3]")
_SPEAKER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError("Every speech sample needs a relative audio path.")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
        or "\\" in value
        or path.suffix.lower() != ".wav"
    ):
        raise ValueError(f"Unsafe or unsupported audio path: {value!r}")
    return path


def _normalize_transcript(text: str) -> str:
    return " ".join(text.strip().split())


def validate_speech_manifest(manifest_path: Path, audio_root: Path) -> dict:
    """Validate exact audio hashes, rights review, Arabic text, and WAV format."""
    manifest_path = Path(manifest_path)
    audio_root = Path(audio_root)
    root = audio_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Speech audio directory not found: {audio_root}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Speech manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Speech manifest must be a JSON object.")
    if manifest.get("status") != "APPROVED":
        raise PermissionError("Speech dataset is blocked until a human rights review is APPROVED.")
    for field in ("dataset_id", "license", "rights_basis", "reviewer", "review_date", "intended_use"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise PermissionError(f"Speech manifest is missing {field}.")
    if manifest["intended_use"] not in {"research_training", "public_model", "commercial_model"}:
        raise PermissionError("Speech manifest has an unsupported intended_use.")
    if manifest.get("speaker_identification_allowed") is not False:
        raise PermissionError("Speaker identification must remain explicitly disabled.")

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Speech manifest must contain a non-empty samples list.")

    listed = set()
    transcripts = set()
    speakers = set()
    total_seconds = 0.0
    sample_rates = set()

    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            raise ValueError(f"Speech sample {index} must be an object.")
        relative = _safe_relative_path(sample.get("audio"))
        name = relative.as_posix()
        if name in listed:
            raise ValueError(f"Duplicate audio path in speech manifest: {name}")
        listed.add(name)

        audio_path = audio_root / Path(*relative.parts)
        if not audio_path.is_file() or not audio_path.resolve().is_relative_to(root):
            raise FileNotFoundError(f"Approved speech audio is missing or outside its root: {name}")
        expected_hash = sample.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError(f"Speech sample {name} requires a lowercase SHA-256.")
        actual_hash = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise PermissionError(f"Speech audio changed after review: {name}")

        transcript = sample.get("text")
        if not isinstance(transcript, str) or not 3 <= len(transcript.strip()) <= 500:
            raise ValueError(f"Speech sample {name} has an empty or out-of-range transcript.")
        if not _ARABIC.search(transcript):
            raise ValueError(f"Speech sample {name} does not contain Arabic script.")
        normalized = _normalize_transcript(transcript)
        if normalized in transcripts:
            raise ValueError(f"Duplicate normalized transcript in speech manifest: {name}")
        transcripts.add(normalized)

        speaker_id = sample.get("speaker_id")
        if not isinstance(speaker_id, str) or not _SPEAKER_ID.fullmatch(speaker_id):
            raise ValueError(f"Speech sample {name} requires an anonymized speaker_id.")
        speakers.add(speaker_id)

        try:
            with wave.open(str(audio_path), "rb") as audio:
                channels = audio.getnchannels()
                sample_width = audio.getsampwidth()
                sample_rate = audio.getframerate()
                frames = audio.getnframes()
                compression = audio.getcomptype()
        except (wave.Error, EOFError) as exc:
            raise ValueError(f"Speech sample {name} is not a valid WAV file.") from exc
        if channels != 1 or sample_width != 2 or compression != "NONE":
            raise ValueError(f"Speech sample {name} must be mono, 16-bit PCM WAV.")
        if not 16000 <= sample_rate <= 48000:
            raise ValueError(f"Speech sample {name} sample rate must be 16–48 kHz.")
        duration = frames / sample_rate
        if not 0.5 <= duration <= 20.0:
            raise ValueError(f"Speech sample {name} duration must be 0.5–20 seconds.")
        sample_rates.add(sample_rate)
        total_seconds += duration

    discovered = {
        path.relative_to(audio_root).as_posix()
        for path in audio_root.rglob("*.wav")
        if path.is_file()
    }
    unlisted = sorted(discovered - listed)
    if unlisted:
        raise PermissionError(f"Unreviewed WAV files are present: {unlisted[:10]}")

    return {
        "status": "PASS",
        "dataset_id": manifest["dataset_id"],
        "license": manifest["license"],
        "sample_count": len(samples),
        "speaker_count_anonymized": len(speakers),
        "total_audio_seconds": round(total_seconds, 3),
        "sample_rates_hz": sorted(sample_rates),
        "speaker_identification_allowed": False,
        "audio_uploaded_or_shared": False,
        "semantic_transcript_review_required": True,
        "training_started": False,
    }
