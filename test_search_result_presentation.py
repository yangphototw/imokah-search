"""Regression checks for timestamp-first static-search presentation."""

from pathlib import Path
import unittest


APP = Path(__file__).parent / "public" / "app.js"


class SearchResultPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")

    def test_partial_title_only_results_are_not_rendered(self):
        self.assertIn(
            "item.clips.length > 0 || item.titleMatchIsComplete", self.source
        )

    def test_title_match_notice_is_only_for_title_only_results(self):
        self.assertIn(
            "if (item.titleMatch && item.clips.length === 0)", self.source
        )
        self.assertIn("尚未找到可定位的逐字稿時間點", self.source)

    def test_transcript_match_copy_promises_a_real_mention(self):
        self.assertIn("逐字稿提到「${matchedTerms.join('、')}」", self.source)


if __name__ == "__main__":
    unittest.main()
