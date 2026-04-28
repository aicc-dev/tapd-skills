#!/usr/bin/env python3
"""High-signal helpers for TAPD TestX and story-linked case workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

BASE_SCRIPTS = Path(__file__).resolve().parents[2] / "tapd-base" / "scripts"
if str(BASE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BASE_SCRIPTS))

from tapd_oauth_common import (
    DEFAULT_API_BASE_URL,
    ConfigError,
    build_testx_story_issue,
    get_token_cache_path,
    load_env_file,
)
from tapd_user_api import call_api, ensure_token_valid, load_session


def call_cached_api(*, path: str, method: str = "GET", query: list[str] | None = None, body: Any = None) -> Any:
    cache_path = get_token_cache_path()
    api_base_url = os.getenv("TAPD_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    session = load_session(cache_path)
    ensure_token_valid(session)
    body_json = None if body is None else json.dumps(body, ensure_ascii=False)
    return call_api(
        path=path,
        method=method,
        query=query or [],
        body=body_json,
        access_token=session["access_token"],
        api_base_url=api_base_url,
    )


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def load_json_file(path: str) -> Any:
    file_path = Path(path).expanduser()
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_object_payload(path: str, *, root_key: str | None = None) -> dict[str, Any]:
    payload = load_json_file(path)
    if root_key and isinstance(payload, dict) and root_key in payload and isinstance(payload[root_key], dict):
        payload = payload[root_key]
    if not isinstance(payload, dict):
        expected = f" containing a '{root_key}' object" if root_key else ""
        raise ValueError(f"Payload file must contain a JSON object{expected}")
    return payload


def repo_list(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos",
        query=[f"Offset={args.offset}", f"Limit={args.limit}"],
    )
    print_json(response)
    return 0


def repo_get(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}"
    )
    print_json(response)
    return 0


def build_case_search_body(
    args: argparse.Namespace,
    *,
    item_type: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "PageInfo": {"Offset": args.offset, "Limit": args.limit},
        "Filter": {"ItemType": item_type},
        "ShowMode": args.show_mode,
        "IncludeDescendants": args.include_descendants,
    }
    if args.folder_uid:
        body["FolderUid"] = args.folder_uid
    if args.story_id:
        body["Filter"]["Issues"] = [args.story_id]
    return body


def folder_list(args: argparse.Namespace) -> int:
    body = build_case_search_body(args, item_type=args.item_type)
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases/search",
        method="POST",
        body=body,
    )
    print_json(response)
    return 0


def folder_create(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {
        "Name": args.name,
        "Description": args.description,
        "Owners": [],
    }
    if args.parent_folder_uid:
        body["FolderUid"] = args.parent_folder_uid
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/folders",
        method="POST",
        body=body,
    )
    print_json(response)
    return 0


def folder_update(args: argparse.Namespace) -> int:
    payload = load_object_payload(args.payload_file, root_key="Folder")
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/folders/{args.folder_uid}",
        method="PUT",
        body=payload,
    )
    print_json(response)
    return 0


def case_get(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases/{args.case_uid}"
    )
    print_json(response)
    return 0


def case_list(args: argparse.Namespace) -> int:
    body = build_case_search_body(args, item_type="CASE")
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases/search",
        method="POST",
        body=body,
    )
    print_json(response)
    return 0


def merge_story_issue(existing_issues: list[dict[str, Any]], story_issue: dict[str, str]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    replaced = False
    target_key = (story_issue["IssueUid"], story_issue["Type"], story_issue["Source"])
    for issue in existing_issues:
        issue_key = (str(issue.get("IssueUid", "")), str(issue.get("Type", "")), str(issue.get("Source", "")))
        if issue_key == target_key:
            merged.append(story_issue)
            replaced = True
        else:
            merged.append(issue)
    if not replaced:
        merged.append(story_issue)
    return merged


def build_case_body(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_object_payload(args.payload_file, root_key="Case")

    if args.story_id:
        if not args.story_workspace_id:
            raise ValueError("--story-workspace-id is required when --story-id is set")
        story_issue = build_testx_story_issue(
            story_id=args.story_id,
            workspace_id=args.story_workspace_id,
            issue_name=args.story_name or "",
        )
        existing_issues = payload.get("Issues", [])
        if not isinstance(existing_issues, list):
            raise ValueError("Case payload field 'Issues' must be a list when present")
        payload["Issues"] = merge_story_issue(existing_issues, story_issue)

    return payload


def case_create(args: argparse.Namespace) -> int:
    payload = build_case_body(args)
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases",
        method="POST",
        body=payload,
    )
    print_json(response)
    return 0


def case_update(args: argparse.Namespace) -> int:
    payload = build_case_body(args)
    response = call_cached_api(
        path=f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases/{args.case_uid}",
        method="PUT",
        body=payload,
    )
    print_json(response)
    return 0


def case_link_story(args: argparse.Namespace) -> int:
    path = f"/api/testx/case/v1/namespaces/{args.workspace_id}/repos/{args.repo_uid}/versions/{args.version_uid}/cases/{args.case_uid}"
    current = call_cached_api(path=path)
    case_data = current["Data"]
    existing_issues = case_data.get("Issues", [])
    if not isinstance(existing_issues, list):
        existing_issues = []
    case_data["Issues"] = merge_story_issue(
        existing_issues,
        build_testx_story_issue(
            story_id=args.story_id,
            workspace_id=args.story_workspace_id,
            issue_name=args.story_name or "",
        ),
    )
    updated = call_cached_api(path=path, method="PUT", body=case_data)
    print_json(updated)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    repo_list_parser = subparsers.add_parser("repo-list", help="List TestX repos under a workspace namespace")
    repo_list_parser.add_argument("--workspace-id", required=True)
    repo_list_parser.add_argument("--offset", type=int, default=0)
    repo_list_parser.add_argument("--limit", type=int, default=20)
    repo_list_parser.set_defaults(func=repo_list)

    repo_get_parser = subparsers.add_parser("repo-get", help="Read a TestX repo by UID")
    repo_get_parser.add_argument("--workspace-id", required=True)
    repo_get_parser.add_argument("--repo-uid", required=True)
    repo_get_parser.set_defaults(func=repo_get)

    folder_list_parser = subparsers.add_parser("folder-list", help="List TestX folders or cases in a repo version")
    folder_list_parser.add_argument("--workspace-id", required=True)
    folder_list_parser.add_argument("--repo-uid", required=True)
    folder_list_parser.add_argument("--version-uid", required=True)
    folder_list_parser.add_argument("--folder-uid")
    folder_list_parser.add_argument("--story-id", help="Optional story ID filter against TestX Issues")
    folder_list_parser.add_argument("--offset", type=int, default=0)
    folder_list_parser.add_argument("--limit", type=int, default=50)
    folder_list_parser.add_argument("--item-type", default="ALL", choices=["ALL", "FOLDER", "CASE"])
    folder_list_parser.add_argument("--show-mode", default="TREE", choices=["TREE", "FLAT"])
    folder_list_parser.add_argument("--include-descendants", action="store_true")
    folder_list_parser.set_defaults(func=folder_list)

    folder_create_parser = subparsers.add_parser("folder-create", help="Create a TestX folder")
    folder_create_parser.add_argument("--workspace-id", required=True)
    folder_create_parser.add_argument("--repo-uid", required=True)
    folder_create_parser.add_argument("--version-uid", required=True)
    folder_create_parser.add_argument("--name", required=True)
    folder_create_parser.add_argument("--description", default="")
    folder_create_parser.add_argument("--parent-folder-uid")
    folder_create_parser.set_defaults(func=folder_create)

    folder_update_parser = subparsers.add_parser("folder-update", help="Update a TestX folder from a JSON payload file")
    folder_update_parser.add_argument("--workspace-id", required=True)
    folder_update_parser.add_argument("--repo-uid", required=True)
    folder_update_parser.add_argument("--version-uid", required=True)
    folder_update_parser.add_argument("--folder-uid", required=True)
    folder_update_parser.add_argument("--payload-file", required=True)
    folder_update_parser.set_defaults(func=folder_update)

    case_get_parser = subparsers.add_parser("case-get", help="Read a TestX case by UID")
    case_get_parser.add_argument("--workspace-id", required=True)
    case_get_parser.add_argument("--repo-uid", required=True)
    case_get_parser.add_argument("--version-uid", required=True)
    case_get_parser.add_argument("--case-uid", required=True)
    case_get_parser.set_defaults(func=case_get)

    case_list_parser = subparsers.add_parser("case-list", help="List TestX cases in a repo version")
    case_list_parser.add_argument("--workspace-id", required=True)
    case_list_parser.add_argument("--repo-uid", required=True)
    case_list_parser.add_argument("--version-uid", required=True)
    case_list_parser.add_argument("--folder-uid")
    case_list_parser.add_argument("--story-id", help="Optional story ID filter against TestX Issues")
    case_list_parser.add_argument("--offset", type=int, default=0)
    case_list_parser.add_argument("--limit", type=int, default=50)
    case_list_parser.add_argument("--show-mode", default="TREE", choices=["TREE", "FLAT"])
    case_list_parser.add_argument("--include-descendants", action="store_true")
    case_list_parser.set_defaults(func=case_list)

    case_create_parser = subparsers.add_parser(
        "case-create",
        help="Create a TestX case from a JSON payload file and optionally attach a TAPD story",
    )
    case_create_parser.add_argument("--workspace-id", required=True)
    case_create_parser.add_argument("--repo-uid", required=True)
    case_create_parser.add_argument("--version-uid", required=True)
    case_create_parser.add_argument("--payload-file", required=True)
    case_create_parser.add_argument("--story-id")
    case_create_parser.add_argument("--story-workspace-id")
    case_create_parser.add_argument("--story-name")
    case_create_parser.set_defaults(func=case_create)

    case_update_parser = subparsers.add_parser(
        "case-update",
        help="Update a TestX case from a JSON payload file and optionally attach a TAPD story",
    )
    case_update_parser.add_argument("--workspace-id", required=True)
    case_update_parser.add_argument("--repo-uid", required=True)
    case_update_parser.add_argument("--version-uid", required=True)
    case_update_parser.add_argument("--case-uid", required=True)
    case_update_parser.add_argument("--payload-file", required=True)
    case_update_parser.add_argument("--story-id")
    case_update_parser.add_argument("--story-workspace-id")
    case_update_parser.add_argument("--story-name")
    case_update_parser.set_defaults(func=case_update)

    case_link_parser = subparsers.add_parser(
        "case-link-story",
        help="Attach a TAPD story to an existing TestX case using the stable TestX issue shape",
    )
    case_link_parser.add_argument("--workspace-id", required=True)
    case_link_parser.add_argument("--repo-uid", required=True)
    case_link_parser.add_argument("--version-uid", required=True)
    case_link_parser.add_argument("--case-uid", required=True)
    case_link_parser.add_argument("--story-id", required=True)
    case_link_parser.add_argument("--story-workspace-id", required=True)
    case_link_parser.add_argument("--story-name")
    case_link_parser.set_defaults(func=case_link_story)

    return parser


def main() -> int:
    parser = build_parser()
    try:
        load_env_file()
        args = parser.parse_args()
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
