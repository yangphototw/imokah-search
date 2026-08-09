import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_public_paragraph_index import prefer_current_transcripts


class PublicParagraphIndexTests(unittest.TestCase):
    def test_current_transcript_replaces_stale_rag_chunks(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "video123_transcript.json").write_text(
                json.dumps([{"text": "校正後逐字稿"}], ensure_ascii=False), encoding="utf-8"
            )
            sources = {"video123": [{"text": "過期 RAG 文字"}]}

            prefer_current_transcripts(sources, directory)

            self.assertEqual(sources["video123"], [{"text": "校正後逐字稿"}])


if __name__ == "__main__":
    unittest.main()
