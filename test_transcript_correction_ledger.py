import unittest

from build_transcript_correction_ledger import build_ledger


class TranscriptCorrectionLedgerTests(unittest.TestCase):
    def test_only_complete_accepted_review_becomes_pending_correction(self):
        reviews = {
            "accepted": {
                "video_id": "video", "start": 1, "end": 2,
                "raw_text": "接拍", "candidate_text": "街拍",
                "reviewed_at": "2026-01-01T00:00:00Z", "flags": ["術語"],
                "asr": {"small": "街拍", "medium": "街拍", "large-v3": "街拍"},
            },
            "ambiguous": {
                "raw_text": "接拍", "candidate_text": "街拍", "asr": {},
            },
        }
        decisions = {
            "accepted": {"status": "all_models_support_candidate", "recommendation": "accept_candidate", "missing_fields": [], "missing_models": []},
            "ambiguous": {"status": "ambiguous", "missing_fields": [], "missing_models": []},
        }

        ledger = build_ledger(reviews, decisions)

        self.assertEqual(ledger["summary"]["accepted_pending_apply"], 1)
        self.assertEqual(ledger["records"]["accepted"]["status"], "accepted_pending_apply")
        self.assertNotIn("ambiguous", ledger["records"])

    def test_accepted_decision_without_text_change_is_not_applied(self):
        ledger = build_ledger(
            {"same": {"raw_text": "道慈", "candidate_text": "道慈", "asr": {}}},
            {"same": {"status": "channel_identity_supported", "missing_fields": [], "missing_models": []}},
        )
        self.assertEqual(ledger["summary"]["accepted_pending_apply"], 0)
        self.assertEqual(ledger["summary"]["skipped"]["no_text_change"], 1)


if __name__ == "__main__":
    unittest.main()
