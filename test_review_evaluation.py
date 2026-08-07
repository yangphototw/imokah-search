import unittest

from evaluate_transcript_reviews import classify


def review(**overrides):
    value = {
        "schema_version": 1, "reviewed_at": "2026-01-01T00:00:00+00:00",
        "video_id": "abc", "start": 0, "end": 1, "audio_path": "audio.webm",
        "clip_start": 0, "clip_end": 1, "raw_text": "原文", "candidate_text": "候選",
        "flags": ["photography term: 焦燈 → 焦段"],
        "asr": {"small": "焦段", "medium": "焦段", "large-v3": "焦段"},
    }
    value.update(overrides)
    return value


class ReviewEvaluationTests(unittest.TestCase):
    models = ["small", "medium", "large-v3"]

    def test_accepts_term_when_all_models_support_it(self):
        self.assertEqual(classify(review(), self.models)["recommendation"], "accept_candidate")

    def test_requires_provenance_for_host_identity(self):
        value = review(
            flags=["name in greeting × 1"],
            asr={"small": "道子", "medium": "道子", "large-v3": "道子"},
        )
        self.assertEqual(
            classify(value, self.models)["recommendation"],
            "accept_candidate_with_channel_identity_provenance",
        )

    def test_marks_missing_model_as_incomplete(self):
        value = review(asr={"small": "焦段"})
        self.assertEqual(classify(value, self.models)["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
