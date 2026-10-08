import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from zettel_eval.retrieval import dense


class CacheDirectoryTests(unittest.TestCase):
    def test_default_is_package_relative_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            package = root / "relocated package"
            module = package / "src/zettel_eval/retrieval/dense.py"
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"ZETTEL_EVAL_CACHE_DIR": ""}), patch.object(dense, "__file__", str(module)):
                    actual = dense._get_cache_dir()
                    self.assertEqual(actual, package / "output/.cache")
                    self.assertTrue(actual.is_dir())
                    self.assertEqual(dense._get_cache_dir(), actual)
            finally:
                os.chdir(old_cwd)

    def test_explicit_cache_directory_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "custom cache" / "nested"
            with patch.dict(os.environ, {"ZETTEL_EVAL_CACHE_DIR": str(target)}):
                self.assertEqual(dense._get_cache_dir(), target)
                self.assertTrue(target.is_dir())

    def test_home_relative_override_is_expanded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"HOME": tmp, "ZETTEL_EVAL_CACHE_DIR": "~/embedding cache"}):
                expected = Path(tmp) / "embedding cache"
                self.assertEqual(dense._get_cache_dir(), expected)
                self.assertTrue(expected.is_dir())


if __name__ == "__main__":
    unittest.main()
