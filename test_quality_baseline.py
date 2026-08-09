import unittest

from quality_baseline import build_report, is_generic_summary


class QualityBaselineTests(unittest.TestCase):
    def test_generic_summary_is_not_editorial_approval(self):
        self.assertTrue(is_generic_summary("以「測試」為主題，分享攝影、器材或創作上的觀察與經驗。"))
        self.assertFalse(is_generic_summary("【已校對】影片比較兩個焦段在同一場景的人像視角差異。"))

    def test_report_keeps_coverage_separate_from_quality(self):
        report = build_report(
            {"categories": [{"videos": [{"title": "測試影片", "ai_summary": "以「測試影片」為主題，整理設定選擇、拍攝條件與實作判斷。"}]}]},
            {"counts": {"complete": 1, "no_transcript_expected": 0}},
            {"paragraphs": [{"needs_audio_review": True, "raw_text": "接拍", "candidate_text": "街拍"}]},
            {"one": {"asr": {"small": "街拍"}}},
            {"decisions": {}},
        )
        self.assertEqual(report["public_video_text"]["approved_evidence_backed_summaries"], 0)
        self.assertEqual(report["public_video_text"]["generic_template_summaries"], 1)
        self.assertEqual(report["audio_review"]["reviewed_with_all_required_models"], 0)
        self.assertFalse(report["quality_gate"]["transcripts_ready_for_95_percent_claim"])


if __name__ == "__main__":
    unittest.main()
