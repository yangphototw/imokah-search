"""Regression checks for timestamp-first static-search presentation."""

from pathlib import Path
import unittest


APP = Path(__file__).parent / "public" / "app.js"


class SearchResultPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")

    def test_partial_title_only_results_are_retained_in_the_title_tiers(self):
        self.assertIn(
            "const groupedVideos = Array.from(groupedMap.values());", self.source
        )

    def test_title_match_label_shows_the_actual_match_count(self):
        self.assertIn(
            "標題命中 ${item.titleMatchedCount}/${item.totalQueryTerms} 個搜尋詞", self.source
        )

    def test_multi_term_sort_keeps_title_tiers_before_transcript_tiers(self):
        self.assertIn(
            "function compareSearchResultTiers(a, b)", self.source
        )
        self.assertIn(
            "(b.matched_count || 0) - (a.matched_count || 0)", self.source
        )

    def test_result_cap_reserves_space_for_each_match_tier(self):
        self.assertIn("function selectSearchResultsByTier(items, totalTerms)", self.source)
        self.assertIn("const perTierLimit = Math.max(1, Math.floor(", self.source)

    def test_title_only_results_explain_when_no_timestamp_exists(self):
        self.assertIn(
            "item.clips.length === 0", self.source
        )
        self.assertIn("尚未找到可定位的逐字稿時間點", self.source)

    def test_transcript_match_copy_promises_a_real_mention(self):
        self.assertIn("逐字稿命中 ${matchedIndexes.length}/${totalTerms} 個搜尋詞", self.source)

    def test_search_results_show_the_curated_video_summary_once_per_video(self):
        self.assertIn("summary: video.ai_summary || ''", self.source)
        self.assertIn('summary-label">影片摘要</div>', self.source)
        self.assertIn("${summaryHtml}", self.source)

    def test_transcript_matches_use_a_compact_keyword_centered_excerpt(self):
        self.assertIn("function createSearchExcerpt(text, matchedTerms)", self.source)
        self.assertIn("item.transcript_excerpt = createSearchExcerpt", self.source)
        self.assertIn("clip.transcript_excerpt || clip.transcript", self.source)
        self.assertNotIn("這段會聽到：", self.source)

    def test_browse_cards_do_not_show_unprovenanced_excerpt_as_a_summary(self):
        # Browse cards remain deliberately compact.  Search cards resolve to
        # the timestamped paragraph index, so a legacy catalog quote cannot be
        # mistaken for either a transcript or a curated listening guide.
        self.assertNotIn("const firstQuote =", self.source)
        self.assertNotIn("逐字稿摘錄：${excerpt", self.source)


if __name__ == "__main__":
    unittest.main()
