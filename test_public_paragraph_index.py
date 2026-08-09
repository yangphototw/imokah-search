import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import build_public_paragraph_index
from build_public_paragraph_index import load_approved_punctuation, prefer_current_transcripts, public_paragraphs
from restore_transcript_punctuation import source_sha256


class PublicParagraphIndexTests(unittest.TestCase):
    def test_current_transcript_replaces_stale_rag_chunks(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            corrected_chunks = [{"text": "local transcript text"}]
            (directory / "video123_transcript.json").write_text(
                json.dumps(corrected_chunks), encoding="utf-8"
            )
            sources = {"video123": [{"text": "stale RAG text"}]}

            prefer_current_transcripts(sources, directory)

            self.assertEqual(sources["video123"], corrected_chunks)

    def test_uses_accepted_punctuation_when_source_hash_matches(self):
        raw_text = "abcdefghijklmnopqrstuvwxyz"
        chunks = [{"start": 0, "text": raw_text}]
        punctuation = {
            "video123:0": {
                "source_sha256": source_sha256(raw_text),
                "display_text": "abc,defghijklmnopqrstuvwxyz.",
            }
        }

        entries = public_paragraphs("video123", chunks, approved={}, punctuation=punctuation)

        self.assertEqual(entries[0]["transcript"], "abc,defghijklmnopqrstuvwxyz.")

    def test_ignores_stale_or_non_punctuation_ledger_text(self):
        raw_text = "abcdefghijklmnopqrstuvwxyz"
        chunks = [{"start": 0, "text": raw_text}]
        stale = {
            "video123:0": {
                "source_sha256": "outdated",
                "display_text": "abc,defghijklmnopqrstuvwxyz.",
            }
        }
        changed_words = {
            "video123:0": {
                "source_sha256": source_sha256(raw_text),
                "display_text": "abc,defghijklmnopqrstuvwxqz.",
            }
        }

        self.assertEqual(public_paragraphs("video123", chunks, {}, stale)[0]["transcript"], raw_text)
        self.assertEqual(public_paragraphs("video123", chunks, {}, changed_words)[0]["transcript"], raw_text)

    def test_draft_punctuation_ledger_cannot_reach_the_public_builder(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "ledger.json"
            path.write_text(json.dumps({
                "publication_status": "draft",
                "records": {"video:0": {"status": "accepted", "source_sha256": "hash", "display_text": "text。"}},
            }), encoding="utf-8")
            with patch.object(build_public_paragraph_index, "PUNCTUATION_LEDGER", path):
                self.assertEqual(load_approved_punctuation(), {})


if __name__ == "__main__":
    unittest.main()
