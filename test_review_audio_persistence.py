import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from review_audio_paragraphs import atomic_write_reviews


class ReviewAudioPersistenceTests(unittest.TestCase):
    def test_atomic_write_produces_complete_json(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "reviews.json"
            payload = {"example": {"asr": {"small": "街拍"}}}

            atomic_write_reviews(payload, path)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertFalse(list(path.parent.glob(".reviews.*.tmp")))


if __name__ == "__main__":
    unittest.main()
