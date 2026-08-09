from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from migrate_project_model_caches import migration_plan


class CacheMigrationTests(unittest.TestCase):
    def test_plan_only_contains_known_existing_whisper_models(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "legacy"
            destination = root / "project"
            (source / "models--Systran--faster-whisper-small").mkdir(parents=True)
            (source / "unrelated-user-model").mkdir()

            plan = migration_plan(source, destination)

            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0][0].name, "models--Systran--faster-whisper-small")
            self.assertEqual(plan[0][1].parent, destination)


if __name__ == "__main__":
    unittest.main()
