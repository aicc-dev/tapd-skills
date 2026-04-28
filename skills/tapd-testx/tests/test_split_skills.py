import argparse
import contextlib
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = ROOT / "skills"
BASE_SCRIPTS = SKILLS_ROOT / "tapd-base" / "scripts"
STORY_SCRIPTS = SKILLS_ROOT / "tapd-story" / "scripts"
TESTX_SCRIPTS = SKILLS_ROOT / "tapd-testx" / "scripts"


for path in (BASE_SCRIPTS, STORY_SCRIPTS, TESTX_SCRIPTS):
    sys.path.insert(0, str(path))


tapd_story = importlib.import_module("tapd_story")
tapd_testx = importlib.import_module("tapd_testx")
tapd_oauth_common = importlib.import_module("tapd_oauth_common")


class SplitSkillCommandTests(unittest.TestCase):
    def parse_story(self, *argv: str) -> argparse.Namespace:
        return tapd_story.build_parser().parse_args(list(argv))

    def parse_testx(self, *argv: str) -> argparse.Namespace:
        return tapd_testx.build_parser().parse_args(list(argv))

    def test_story_skill_owns_story_update_command(self) -> None:
        args = self.parse_story(
            "story-update",
            "--workspace-id",
            "32131908",
            "--story-id",
            "1132131908001006860",
            "--payload-file",
            "/tmp/story.json",
        )

        self.assertEqual(args.command, "story-update")
        self.assertIs(args.func, tapd_story.story_update)

    def test_testx_skill_does_not_accept_story_update_command(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parse_testx(
                    "story-update",
                    "--workspace-id",
                    "32131908",
                    "--story-id",
                    "1132131908001006860",
                    "--payload-file",
                    "/tmp/story.json",
                )

    @patch("tapd_story.call_cached_api")
    def test_design_story_get_uses_testx_design_workspace_path(self, call_cached_api) -> None:
        call_cached_api.return_value = {"Data": []}
        args = argparse.Namespace(workspace_id="32131908", story_id="1132131908001006860")

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_story.design_story_get(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/api/testx/design/v2/namespaces/32131908/workspaces/32131908/stories",
            query=["Ids=1132131908001006860"],
        )

    def test_base_default_token_cache_uses_tapd_base_name(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        env_path = Path(temp_dir.name) / ".codex" / "config" / "tapd-base.env"
        env_path.parent.mkdir(parents=True)
        env_path.write_text("TAPD_CLIENT_ID=codex-client\n", encoding="utf-8")

        with patch.dict("os.environ", {"HOME": temp_dir.name}, clear=True):
            tapd_oauth_common.load_env_file()
            token_cache = tapd_oauth_common.get_token_cache_path()

            self.assertEqual(Path(temp_dir.name) / ".codex" / "memories" / "tapd-base" / "session.json", token_cache)


if __name__ == "__main__":
    unittest.main()
