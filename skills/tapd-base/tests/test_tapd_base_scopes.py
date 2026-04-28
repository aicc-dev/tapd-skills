import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(ROOT / "skills" / "tapd-base" / "scripts"))

tapd_oauth_common = importlib.import_module("tapd_oauth_common")
tapd_user_oauth_demo = importlib.import_module("tapd_user_oauth_demo")


class TapdBaseScopeTests(unittest.TestCase):
    def test_default_scopes_include_story_and_comment_permissions(self) -> None:
        scopes = set(tapd_oauth_common.DEFAULT_SCOPES.split())

        self.assertEqual(tapd_oauth_common.DEFAULT_SCOPES, tapd_user_oauth_demo.DEFAULT_SCOPES)
        self.assertGreaterEqual(
            scopes,
            {"user", "story#read", "story#write", "comment#read", "comment#write"},
        )
        self.assertNotIn("comment#delete", scopes)


if __name__ == "__main__":
    unittest.main()
