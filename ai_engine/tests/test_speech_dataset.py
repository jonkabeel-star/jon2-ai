"""Tests for rights-first Arabic speech dataset validation."""
import hashlib
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from speech_dataset import validate_speech_manifest


class SpeechDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.wav_path = self.audio / "sample.wav"
        with wave.open(str(self.wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 16000)
        self.manifest = self.root / "manifest.json"
        self._write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def _write_manifest(self, **changes):
        raw = self.wav_path.read_bytes()
        sample = {
            "audio": "sample.wav",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "text": "مرحبًا بك في اختبار الصوت.",
            "speaker_id": "speaker_001",
            "voice_synthesis_consent": True,
        }
        manifest = {
            "status": "APPROVED",
            "dataset_id": "test-owned-fixture",
            "license": "CC0-1.0",
            "rights_basis": "Synthetic test audio created for automated tests.",
            "reviewer": "Test reviewer",
            "review_date": "2026-11-09",
            "intended_use": "research_training",
            "speaker_identification_allowed": False,
            "samples": [sample],
        }
        manifest.update(changes)
        self.manifest.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    def test_valid_approved_wav_dataset_passes(self):
        report = validate_speech_manifest(self.manifest, self.audio)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["sample_count"], 1)
        self.assertEqual(report["total_audio_seconds"], 1.0)
        self.assertFalse(report["speaker_identification_allowed"])
        self.assertFalse(report["training_started"])

    def test_unapproved_dataset_is_blocked(self):
        self._write_manifest(status="PENDING")
        with self.assertRaises(PermissionError):
            validate_speech_manifest(self.manifest, self.audio)

    def test_speaker_identification_must_be_disabled(self):
        self._write_manifest(speaker_identification_allowed=True)
        with self.assertRaises(PermissionError):
            validate_speech_manifest(self.manifest, self.audio)

    def test_voice_synthesis_requires_explicit_consent(self):
        raw = self.wav_path.read_bytes()
        self._write_manifest(samples=[{
            "audio": "sample.wav",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "text": "مرحبًا بك في اختبار الصوت.",
            "speaker_id": "speaker_001",
            "voice_synthesis_consent": False,
        }])
        with self.assertRaises(PermissionError):
            validate_speech_manifest(self.manifest, self.audio)

    def test_audio_hash_mismatch_is_blocked(self):
        self.wav_path.write_bytes(self.wav_path.read_bytes() + b"changed")
        with self.assertRaises(PermissionError):
            validate_speech_manifest(self.manifest, self.audio)

    def test_duplicate_transcripts_for_same_speaker_are_blocked(self):
        second = self.audio / "second.wav"
        second.write_bytes(self.wav_path.read_bytes())
        digest = hashlib.sha256(self.wav_path.read_bytes()).hexdigest()
        self._write_manifest(samples=[
            {
                "audio": "sample.wav", "sha256": digest,
                "text": "مرحبًا بك في اختبار الصوت.",
                "speaker_id": "speaker_001", "voice_synthesis_consent": True,
            },
            {
                "audio": "second.wav", "sha256": digest,
                "text": "مرحبًا بك في اختبار الصوت.",
                "speaker_id": "speaker_001", "voice_synthesis_consent": True,
            },
        ])
        with self.assertRaisesRegex(ValueError, "same speaker"):
            validate_speech_manifest(self.manifest, self.audio)

    def test_same_transcript_from_different_speakers_is_allowed(self):
        second = self.audio / "second.wav"
        second.write_bytes(self.wav_path.read_bytes())
        digest = hashlib.sha256(self.wav_path.read_bytes()).hexdigest()
        self._write_manifest(samples=[
            {
                "audio": "sample.wav", "sha256": digest,
                "text": "مرحبًا بك في اختبار الصوت.",
                "speaker_id": "speaker_001", "voice_synthesis_consent": True,
            },
            {
                "audio": "second.wav", "sha256": digest,
                "text": "مرحبًا بك في اختبار الصوت.",
                "speaker_id": "speaker_002", "voice_synthesis_consent": True,
            },
        ])
        report = validate_speech_manifest(self.manifest, self.audio)
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["speaker_count_anonymized"], 2)

    def test_non_arabic_transcript_is_blocked(self):
        self._write_manifest(samples=[{
            "audio": "sample.wav",
            "sha256": hashlib.sha256(self.wav_path.read_bytes()).hexdigest(),
            "text": "hello there",
            "speaker_id": "speaker_001",
        }])
        with self.assertRaises(ValueError):
            validate_speech_manifest(self.manifest, self.audio)

    def test_path_traversal_is_blocked(self):
        self._write_manifest(samples=[{
            "audio": "../sample.wav",
            "sha256": hashlib.sha256(self.wav_path.read_bytes()).hexdigest(),
            "text": "مرحبًا بك في اختبار الصوت.",
            "speaker_id": "speaker_001",
        }])
        with self.assertRaises(ValueError):
            validate_speech_manifest(self.manifest, self.audio)


if __name__ == "__main__":
    unittest.main()
