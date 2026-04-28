import argparse
import contextlib
import importlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(ROOT / "skills" / "tapd-story" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "tapd-base" / "scripts"))

tapd_story = importlib.import_module("tapd_story")


class TapdStoryCommentCommandTests(unittest.TestCase):
    def parse(self, *argv: str) -> argparse.Namespace:
        return tapd_story.build_parser().parse_args(list(argv))

    def test_parser_accepts_story_comment_list_command(self) -> None:
        args = self.parse(
            "comment-list",
            "--workspace-id",
            "32131908",
            "--story-id",
            "1132131908001006860",
        )

        self.assertEqual(args.command, "comment-list")
        self.assertIs(args.func, tapd_story.comment_list)
        self.assertEqual(args.entry_type, "stories")
        self.assertEqual(args.entry_id, "1132131908001006860")

    @patch("tapd_story.call_cached_api")
    def test_comment_list_reads_story_comments(self, call_cached_api) -> None:
        call_cached_api.return_value = {"data": []}
        args = argparse.Namespace(
            workspace_id="32131908",
            entry_type="stories",
            entry_id="1132131908001006860",
            comment_id=None,
            description="hello from browser",
            limit=50,
            page=2,
            order="created desc",
            fields="id,description,author",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_story.comment_list(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/comments",
            query=[
                "workspace_id=32131908",
                "entry_type=stories",
                "entry_id=1132131908001006860",
                "description=hello from browser",
                "limit=50",
                "page=2",
                "order=created desc",
                "fields=id,description,author",
            ],
        )

    @patch("tapd_story.call_cached_api")
    def test_story_change_list_reads_story_history(self, call_cached_api) -> None:
        call_cached_api.return_value = {"data": []}
        args = argparse.Namespace(
            workspace_id="32131908",
            story_id="1132131908001006872",
            limit=100,
            page=None,
            order="created desc",
            fields="id,comment,field_changes",
            need_parse_changes=1,
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_story.story_change_list(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/story_changes",
            query=[
                "workspace_id=32131908",
                "story_id=1132131908001006872",
                "need_parse_changes=1",
                "limit=100",
                "order=created desc",
                "fields=id,comment,field_changes",
            ],
        )

    @patch("tapd_story.call_cached_api")
    def test_comment_find_filters_comments_by_plain_text(self, call_cached_api) -> None:
        call_cached_api.return_value = {
            "status": 1,
            "data": [
                {"Comment": {"id": "1", "description": "<p>hello from browser</p>"}},
                {"Comment": {"id": "2", "description": "<p>hello from tapd-skills</p>"}},
            ],
            "info": "success",
        }
        args = argparse.Namespace(
            workspace_id="32131908",
            entry_type="stories",
            entry_id="1132131908001006872",
            keyword="hello from browser",
            limit=200,
            page=None,
            order="created desc",
            fields="id,description,author,entry_type,entry_id,created,workspace_id",
        )

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = tapd_story.comment_find(args)

        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual([item["Comment"]["id"] for item in payload["data"]], ["1"])
        call_cached_api.assert_called_once_with(
            path="/comments",
            query=[
                "workspace_id=32131908",
                "entry_type=stories",
                "entry_id=1132131908001006872",
                "limit=200",
                "order=created desc",
                "fields=id,description,author,entry_type,entry_id,created,workspace_id",
            ],
        )

    @patch("tapd_story.call_cached_api")
    def test_comment_add_posts_story_comment(self, call_cached_api) -> None:
        call_cached_api.return_value = {"status": 1}
        args = argparse.Namespace(
            workspace_id="32131908",
            entry_type="stories",
            entry_id="1132131908001006860",
            description="这个需求需要补充验收标准",
            author="tester",
            root_id=None,
            reply_id="1020355782058781915",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_story.comment_add(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/comments",
            method="POST",
            body={
                "workspace_id": "32131908",
                "entry_type": "stories",
                "entry_id": "1132131908001006860",
                "description": "这个需求需要补充验收标准",
                "author": "tester",
                "reply_id": "1020355782058781915",
            },
        )

    @patch("tapd_story.call_cached_api")
    def test_comment_add_requires_entry_id(self, call_cached_api) -> None:
        args = argparse.Namespace(
            workspace_id="32131908",
            entry_type="stories",
            entry_id=None,
            description="这个需求需要补充验收标准",
            author="tester",
            root_id=None,
            reply_id=None,
        )

        with self.assertRaisesRegex(ValueError, "--story-id or --entry-id is required"):
            tapd_story.comment_add(args)

        call_cached_api.assert_not_called()

    @patch("tapd_story.call_cached_api")
    def test_comment_update_posts_comment_change(self, call_cached_api) -> None:
        call_cached_api.return_value = {"status": 1}
        args = argparse.Namespace(
            workspace_id="32131908",
            comment_id="1020355782058781915",
            description="更新后的评论内容",
            change_creator="tester",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_story.comment_update(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/comments",
            method="POST",
            body={
                "workspace_id": "32131908",
                "id": "1020355782058781915",
                "description": "更新后的评论内容",
                "change_creator": "tester",
            },
        )

    def test_parser_does_not_expose_comment_delete_command(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.parse(
                    "comment-delete",
                    "--workspace-id",
                    "32131908",
                    "--comment-id",
                    "1020355782058781915",
                )


if __name__ == "__main__":
    unittest.main()
