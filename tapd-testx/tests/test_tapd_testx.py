import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tapd-base" / "scripts"))

import tapd_testx


class TapdTestxCommandTests(unittest.TestCase):
    def parse(self, *argv: str) -> argparse.Namespace:
        return tapd_testx.build_parser().parse_args(list(argv))

    def write_payload(self, payload: dict) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "payload.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_parser_accepts_repo_get_command(self) -> None:
        args = self.parse("repo-get", "--workspace-id", "32131908", "--repo-uid", "17090")

        self.assertEqual(args.command, "repo-get")
        self.assertIs(args.func, tapd_testx.repo_get)

    @patch("tapd_testx.call_cached_api")
    def test_repo_get_calls_repo_detail_endpoint(self, call_cached_api) -> None:
        call_cached_api.return_value = {"Data": {"Uid": "17090"}}
        args = argparse.Namespace(workspace_id="32131908", repo_uid="17090")

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_testx.repo_get(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/api/testx/case/v1/namespaces/32131908/repos/17090"
        )

    def test_parser_accepts_case_list_command(self) -> None:
        args = self.parse(
            "case-list",
            "--workspace-id",
            "32131908",
            "--repo-uid",
            "17090",
            "--version-uid",
            "18158",
        )

        self.assertEqual(args.command, "case-list")
        self.assertIs(args.func, tapd_testx.case_list)

    @patch("tapd_testx.call_cached_api")
    def test_case_list_uses_search_endpoint_with_case_item_type(self, call_cached_api) -> None:
        call_cached_api.return_value = {"Data": {"Cases": []}}
        args = argparse.Namespace(
            workspace_id="32131908",
            repo_uid="17090",
            version_uid="18158",
            folder_uid="12572042",
            story_id="1132131908001006860",
            offset=10,
            limit=30,
            show_mode="FLAT",
            include_descendants=True,
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_testx.case_list(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/api/testx/case/v1/namespaces/32131908/repos/17090/versions/18158/cases/search",
            method="POST",
            body={
                "PageInfo": {"Offset": 10, "Limit": 30},
                "Filter": {"ItemType": "CASE", "Issues": ["1132131908001006860"]},
                "ShowMode": "FLAT",
                "IncludeDescendants": True,
                "FolderUid": "12572042",
            },
        )

    @patch("tapd_testx.call_cached_api")
    def test_folder_update_wraps_folder_payload(self, call_cached_api) -> None:
        call_cached_api.return_value = {"Data": {"Uid": "12572042"}}
        payload_file = self.write_payload(
            {
                "Folder": {
                    "Uid": "12572042",
                    "Name": "回归目录",
                    "Description": "更新后的描述",
                    "Owners": ["tester_a"],
                }
            }
        )
        args = argparse.Namespace(
            workspace_id="32131908",
            repo_uid="17090",
            version_uid="18158",
            folder_uid="12572042",
            payload_file=payload_file,
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_testx.folder_update(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/api/testx/case/v1/namespaces/32131908/repos/17090/versions/18158/folders/12572042",
            method="PUT",
            body={
                "Uid": "12572042",
                "Name": "回归目录",
                "Description": "更新后的描述",
                "Owners": ["tester_a"],
            },
        )

    @patch("tapd_testx.call_cached_api")
    def test_case_update_merges_story_issue_into_payload(self, call_cached_api) -> None:
        call_cached_api.return_value = {"Data": {"Uid": "12572047"}}
        payload_file = self.write_payload(
            {
                "Case": {
                    "Uid": "12572047",
                    "FolderUid": "12572042",
                    "Name": "版本展示",
                    "Priority": "P1",
                    "Issues": [
                        {
                            "IssueUid": "legacy-1",
                            "Type": "BUG",
                            "Source": "TAPD",
                        }
                    ],
                }
            }
        )
        args = argparse.Namespace(
            workspace_id="32131908",
            repo_uid="17090",
            version_uid="18158",
            case_uid="12572047",
            payload_file=payload_file,
            story_id="1132131908001006860",
            story_workspace_id="32131908",
            story_name="Plus 模型版本展示为 3.6",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            result = tapd_testx.case_update(args)

        self.assertEqual(result, 0)
        call_cached_api.assert_called_once_with(
            path="/api/testx/case/v1/namespaces/32131908/repos/17090/versions/18158/cases/12572047",
            method="PUT",
            body={
                "Uid": "12572047",
                "FolderUid": "12572042",
                "Name": "版本展示",
                "Priority": "P1",
                "Issues": [
                    {
                        "IssueUid": "legacy-1",
                        "Type": "BUG",
                        "Source": "TAPD",
                    },
                    {
                        "IssueUid": "1132131908001006860",
                        "IssueName": "Plus 模型版本展示为 3.6",
                        "IssueUrl": "32131908",
                        "WorkspaceUid": "32131908",
                        "Type": "STORY",
                        "Source": "TAPD",
                    },
                ],
            },
        )

if __name__ == "__main__":
    unittest.main()
