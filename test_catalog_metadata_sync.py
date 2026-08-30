import unittest

from catalog_metadata_sync import iso_date, merge_publish_dates, missing_publish_date_ids


class CatalogMetadataSyncTests(unittest.TestCase):
    def test_only_complete_youtube_dates_become_iso_dates(self):
        self.assertEqual(iso_date("20260824"), "2026-08-24")
        self.assertEqual(iso_date("2026-08-24"), "")
        self.assertEqual(iso_date(""), "")

    def test_merge_only_fills_blank_existing_catalog_dates(self):
        catalog = {
            "categories": [{"videos": [
                {"id": "blank", "publish_date": ""},
                {"id": "known", "publish_date": "2026-08-01"},
            ]}],
        }
        date_map = {"known": "2026-08-01"}

        changed = merge_publish_dates(
            catalog,
            date_map,
            {"blank": "2026-08-24", "known": "2026-08-25", "absent": "2026-08-26"},
        )

        self.assertEqual(changed, ["blank"])
        self.assertEqual(missing_publish_date_ids(catalog), [])
        self.assertEqual(catalog["categories"][0]["videos"][1]["publish_date"], "2026-08-01")
        self.assertEqual(date_map, {"blank": "2026-08-24", "known": "2026-08-01"})


if __name__ == "__main__":
    unittest.main()
