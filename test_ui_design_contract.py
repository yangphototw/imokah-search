"""Low-cost regression checks for the static visual system."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parent
HTML = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "public" / "style.css").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")


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


if __name__ == "__main__":
    unittest.main()
