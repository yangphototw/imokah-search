import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from review_audio_paragraphs import MAX_NEW_TOKENS, atomic_write_reviews, transcribe_clip


class ReviewAudioPersistenceTests(unittest.TestCase):
    def test_atomic_write_produces_complete_json(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "reviews.json"
            payload = {"example": {"asr": {"small": "街拍"}}}

            atomic_write_reviews(payload, path)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertFalse(list(path.parent.glob(".reviews.*.tmp")))

    def test_transcribe_clip_never_uses_none_for_sensitive_options(self):
        class FakeModel:
            def __init__(self):
                self.audio = None
                self.options = None

            def transcribe(self, audio, **options):
                self.audio = audio
                self.options = options
                return [], object()

        model = FakeModel()
        transcribe_clip(model, "audio.webm", "1.00,8.00")

        self.assertEqual(model.audio, "audio.webm")
        self.assertEqual(model.options["initial_prompt"], "")
        self.assertFalse(model.options["condition_on_previous_text"])
        self.assertEqual(model.options["max_new_tokens"], MAX_NEW_TOKENS)
        self.assertIsInstance(model.options["max_new_tokens"], int)


if __name__ == "__main__":
    unittest.main()
