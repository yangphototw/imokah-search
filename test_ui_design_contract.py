"""Low-cost regression checks for the static visual system."""

import json
import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).parent
HTML = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "public" / "style.css").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")
WIKI_BUILDER = (ROOT / "books" / "aiok-photography-knowledge" / "tools" / "build_channel_knowledge_wiki.py").read_text(encoding="utf-8")
WIKI_APP = (ROOT / "public/wiki/wiki.js").read_text(encoding="utf-8")
WIKI_DATA_RAW = (ROOT / "public" / "wiki" / "channel-knowledge-wiki-data.js").read_text(encoding="utf-8")
WIKI_PREFIX = "window.CHANNEL_KNOWLEDGE_WIKI = "
WIKI_DATA = json.loads(WIKI_DATA_RAW.removeprefix(WIKI_PREFIX).rstrip().removesuffix(";"))
CORPUS_MANIFEST = json.loads(
    (ROOT / "books" / "aiok-photography-knowledge" / "corpus" / "manifest.json").read_text(encoding="utf-8")
)


class VisualSystemTests(unittest.TestCase):
    def test_light_is_the_first_visit_theme(self):
        self.assertIn('data-theme="light"', HTML)
        self.assertIn("localStorage.getItem('ppvi-theme') || 'light'", APP)

    def test_type_scale_keeps_the_documented_ratio(self):
        for token in (
            "--type-lvl1: 2.744rem",
            "--type-lvl2: 1.96rem",
            "--type-lvl3: 1.4rem",
            "--type-lvl4: 1rem",
            "--type-lvl5: 0.75rem",
        ):
            self.assertIn(token, CSS)

    def test_timestamped_evidence_has_a_clear_time_label(self):
        self.assertIn('content: "時間 "', CSS)
        self.assertIn("個可定位片段", APP)

    def test_all_category_deduplicates_before_rendering(self):
        self.assertIn("videos = Array.from(uniqueMap.values())", APP)

    def test_browse_lists_are_sorted_by_newest_publish_date(self):
        self.assertIn("function compareVideosByPublishDate(a, b)", APP)
        self.assertIn("videos.sort(compareVideosByPublishDate);", APP)
        self.assertIn("dateB.localeCompare(dateA)", APP)

    def test_site_identity_has_a_named_tab_and_custom_icon(self):
        self.assertIn("<title>複習都OK | 我都OK啊頻道資料庫</title>", HTML)
        self.assertIn('href="favicon.svg?v=20260830"', HTML)
        self.assertTrue((ROOT / "public" / "favicon.svg").is_file())

    def test_hero_and_online_status_use_the_review_identity(self):
        self.assertIn("<h1 class=\"type-lvl-1\">複習都OK</h1>", HTML)
        self.assertIn('data-video-count', HTML)
        self.assertIn('data-updated-date', HTML)
        self.assertRegex(HTML, r'src="app\.js\?v=[^"]+"')
        self.assertIn("querySelector('[data-video-count]')", APP)
        self.assertIn("querySelector('[data-updated-date]')", APP)
        self.assertIn("latestPublishDate.replaceAll('-', '/')", APP)

    def test_hot_tag_labels_submit_the_same_search_words(self):
        self.assertIn('data-tag="ISO 感光度">ISO 感光度</button>', HTML)
        self.assertIn('data-tag="HSL 調色">HSL 調色</button>', HTML)

    def test_random_video_control_has_dice_on_both_sides(self):
        self.assertIn("隨機影片", HTML)
        self.assertEqual(HTML.count('class="random-dice"'), 2)
        self.assertIn("height: 1.3rem", CSS)

    def test_wiki_distinguishes_catalogue_from_processed_knowledge(self):
        stats = WIKI_DATA["stats"]
        self.assertGreaterEqual(stats["total_videos"], stats["processed_videos"])
        self.assertEqual(
            stats["total_videos"],
            stats["processed_videos"] + stats["pending_pipeline_videos"],
        )
        self.assertEqual(
            stats["processed_videos"],
            stats["approved_summaries"] + stats["review_exceptions"],
        )
        self.assertIn("資料同步中", WIKI_APP)
        self.assertIn("支完成知識處理", WIKI_APP)

    def test_wiki_uses_the_corpus_passage_count(self):
        self.assertEqual(
            WIKI_DATA["stats"]["passage_count"],
            CORPUS_MANIFEST["indexed_passages"],
        )

    def test_mutable_search_data_is_revalidated(self):
        self.assertIn("fetch('/catalog.json', { cache: 'no-cache' })", APP)
        self.assertIn("json.gz?v=6`, { cache: 'no-cache' })", APP)
        self.assertIn("/paragraph-index/${shardId}.json.gz`, { cache: 'no-cache' })", APP)
        review = (ROOT / "public/review.js").read_text(encoding="utf-8")
        self.assertIn("window.location.protocol === 'file:'", review)
        self.assertIn("fetch('approved-video-summaries.json', { cache: 'no-cache' })", review)
        review_page = (ROOT / "public/review.html").read_text(encoding="utf-8")
        self.assertIn('src="review.js?v=20260904-revalidate"', review_page)

    def test_wiki_script_url_tracks_its_content(self):
        version = hashlib.sha256(WIKI_DATA_RAW.encode("utf-8")).hexdigest()[:16]
        html = (ROOT / "public/wiki/index.html").read_text(encoding="utf-8")
        self.assertIn(f'channel-knowledge-wiki-data.js?v={version}', html)

    def test_deployment_does_not_cache_mutable_data_as_immutable(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        rules = {rule["source"]: rule["headers"] for rule in config["headers"]}
        for source in ("/catalog.json", "/search-index/(.*)", "/paragraph-index/(.*)",
                       "/approved-video-summaries.json", "/approved-video-summaries.js", "/wiki/(.*)"):
            self.assertIn({"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"}, rules[source])


if __name__ == "__main__":
    unittest.main()
