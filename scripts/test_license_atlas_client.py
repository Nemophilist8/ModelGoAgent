"""
LicenseAtlas 客户端与同步检查（需 make sync-atlas 后运行完整集成用例）。
"""
import os
import sys
import unittest

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.license_atlas_client import (  # noqa: E402
    atlas_is_ready,
    fetch_from_atlas,
    resolve_slugs,
    read_body,
)


class TestLicenseAtlasClient(unittest.TestCase):
    def test_resolve_slugs_mit(self):
        slugs = resolve_slugs("MIT")
        self.assertIn("mit", slugs)

    def test_resolve_slugs_apache(self):
        slugs = resolve_slugs("Apache-2.0")
        self.assertIn("apache-2.0", slugs)

    def test_placeholder_skipped(self):
        self.assertEqual(resolve_slugs("foo_license"), [])

    @unittest.skipUnless(atlas_is_ready(), "run make sync-atlas first")
    def test_fetch_mit_body(self):
        text = fetch_from_atlas("MIT")
        self.assertIsNotNone(text)
        self.assertIn("Permission", text)
        self.assertGreater(len(text), 200)

    @unittest.skipUnless(atlas_is_ready(), "run make sync-atlas first")
    def test_read_body_direct(self):
        for slug in resolve_slugs("MIT"):
            text = read_body(slug)
            if text:
                self.assertIn("MIT", text.upper())
                return
        self.fail("no body for MIT")


if __name__ == "__main__":
    unittest.main()
