import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from restore_transcript_punctuation import (
    approve_ledger_for_publication,
    build_ledger,
    is_punctuation_only_change,
    punctuate_text,
    source_sha256,
)


class PunctuationIntegrityTests(unittest.TestCase):
    def test_reconstructs_original_case_after_model_normalises_it(self):
        self.assertEqual(
            punctuate_text("OK大家好", "Ok，大家好。"),
            "OK，大家好。",
        )

    def test_rejects_a_changed_spoken_character(self):
        self.assertIsNone(punctuate_text("我是道慈", "我是到此。"))
        self.assertFalse(is_punctuation_only_change("我是道慈", "我是到此。"))

    def test_rejects_added_or_removed_words(self):
        self.assertIsNone(punctuate_text("這是一段逐字稿", "這是一段完整逐字稿。"))

    def test_keeps_existing_source_punctuation(self):
        self.assertEqual(
            punctuate_text("Sony A7，值得買", "Sony A7，值得買。"),
            "Sony A7，值得買。",
        )

    def test_normalises_model_sentence_marks_for_chinese_display(self):
        self.assertEqual(punctuate_text("提高ISO", "提高ISO."), "提高ISO。")

    def test_ledger_resumes_when_source_hash_has_not_changed(self):
        paragraphs = [{"id": "video:0", "transcript": "OK大家好"}]
        restored = [{
            "raw_text": "OK大家好",
            "display_text": "OK，大家好。",
            "accepted": True,
            "model_output": "Ok，大家好。",
        }]
        with TemporaryDirectory() as temporary_directory:
            ledger_path = Path(temporary_directory) / "ledger.json"
            with patch("restore_transcript_punctuation.current_paragraphs", return_value=paragraphs), patch(
                "restore_transcript_punctuation.load_punctuation_model", return_value=object()
            ), patch("restore_transcript_punctuation.restore_texts", return_value=restored) as restore:
                first = build_ledger(ledger_path=ledger_path, batch_size=1)
                second = build_ledger(ledger_path=ledger_path, batch_size=1)

            payload = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(first["accepted"], 1)
            self.assertEqual(second["pending"], 0)
            self.assertEqual(restore.call_count, 1)
            self.assertEqual(payload["records"]["video:0"]["source_text"], "OK大家好")
            self.assertEqual(payload["records"]["video:0"]["display_text"], "OK，大家好。")

    def test_sample_order_is_stable_and_not_source_order(self):
        paragraphs = [
            {"id": "video-z:0", "transcript": "first paragraph"},
            {"id": "video-a:0", "transcript": "second paragraph"},
        ]
        restored = [{
            "raw_text": "",
            "display_text": "",
            "accepted": True,
            "model_output": "",
        }]
        with TemporaryDirectory() as temporary_directory:
            ledger_path = Path(temporary_directory) / "ledger.json"
            with patch("restore_transcript_punctuation.current_paragraphs", return_value=paragraphs), patch(
                "restore_transcript_punctuation.load_punctuation_model", return_value=object()
            ), patch("restore_transcript_punctuation.restore_texts", return_value=restored) as restore:
                build_ledger(ledger_path=ledger_path, limit=1, sample=True)

        selected_text = restore.call_args.args[0][0]
        expected = min(paragraphs, key=lambda paragraph: source_sha256(paragraph["id"]))
        self.assertEqual(selected_text, expected["transcript"])

    def test_cannot_approve_a_partial_ledger(self):
        paragraphs = [{"id": "video:0", "transcript": "OK大家好"}]
        with TemporaryDirectory() as temporary_directory:
            ledger_path = Path(temporary_directory) / "ledger.json"
            ledger_path.write_text(json.dumps({"schema_version": 2, "records": {}}), encoding="utf-8")
            with patch("restore_transcript_punctuation.current_paragraphs", return_value=paragraphs):
                with self.assertRaisesRegex(RuntimeError, "missing/stale"):
                    approve_ledger_for_publication(ledger_path, "manual review")


if __name__ == "__main__":
    unittest.main()
