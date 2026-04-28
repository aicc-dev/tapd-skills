#!/usr/bin/env python3
"""Helpers for TAPD story and story comment workflows."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BASE_SCRIPTS = Path(__file__).resolve().parents[2] / "tapd-base" / "scripts"
if str(BASE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BASE_SCRIPTS))

from tapd_oauth_common import (  # noqa: E402
    DEFAULT_API_BASE_URL,
    DEFAULT_STORY_FIELDS,
    ConfigError,
    get_token_cache_path,
    load_env_file,
)
from tapd_user_api import call_api, ensure_token_valid, load_session  # noqa: E402


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


def add_query_param(query: list[str], name: str, value: Any) -> None:
    if value is None:
        return
    query.append(f"{name}={value}")


def html_to_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def story_get(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path="/stories",
        query=[
            f"workspace_id={args.workspace_id}",
            f"id={args.story_id}",
            f"fields={args.fields}",
        ],
    )
    print_json(response)
    return 0


def build_story_update_body(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_object_payload(args.payload_file, root_key="Story")
    payload["id"] = str(args.story_id)
    payload["workspace_id"] = str(args.workspace_id)
    return payload


def story_update(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path="/stories",
        method="POST",
        body=build_story_update_body(args),
    )
    print_json(response)
    return 0


def design_story_get(args: argparse.Namespace) -> int:
    response = call_cached_api(
        path=f"/api/testx/design/v2/namespaces/{args.workspace_id}/workspaces/{args.workspace_id}/stories",
        query=[f"Ids={args.story_id}"],
    )
    print_json(response)
    return 0


def story_change_list(args: argparse.Namespace) -> int:
    query: list[str] = []
    add_query_param(query, "workspace_id", args.workspace_id)
    add_query_param(query, "story_id", args.story_id)
    add_query_param(query, "need_parse_changes", args.need_parse_changes)
    add_query_param(query, "limit", args.limit)
    add_query_param(query, "page", args.page)
    add_query_param(query, "order", args.order)
    add_query_param(query, "fields", args.fields)
    response = call_cached_api(path="/story_changes", query=query)
    print_json(response)
    return 0


def comment_list(args: argparse.Namespace) -> int:
    query: list[str] = []
    add_query_param(query, "workspace_id", args.workspace_id)
    add_query_param(query, "id", args.comment_id)
    add_query_param(query, "entry_type", args.entry_type if args.entry_id else None)
    add_query_param(query, "entry_id", args.entry_id)
    add_query_param(query, "description", args.description)
    add_query_param(query, "limit", args.limit)
    add_query_param(query, "page", args.page)
    add_query_param(query, "order", args.order)
    add_query_param(query, "fields", args.fields)
    response = call_cached_api(path="/comments", query=query)
    print_json(response)
    return 0


def comment_find(args: argparse.Namespace) -> int:
    query: list[str] = []
    add_query_param(query, "workspace_id", args.workspace_id)
    add_query_param(query, "entry_type", args.entry_type if args.entry_id else None)
    add_query_param(query, "entry_id", args.entry_id)
    add_query_param(query, "limit", args.limit)
    add_query_param(query, "page", args.page)
    add_query_param(query, "order", args.order)
    add_query_param(query, "fields", args.fields)
    response = call_cached_api(path="/comments", query=query)
    keyword = args.keyword
    data = response.get("data", []) if isinstance(response, dict) else []
    if isinstance(data, list):
        response["data"] = [
            item
            for item in data
            if keyword in str(item.get("Comment", {}).get("description", ""))
            or keyword in html_to_text(item.get("Comment", {}).get("description", ""))
        ]
    print_json(response)
    return 0


def comment_add(args: argparse.Namespace) -> int:
    if not args.entry_id:
        raise ValueError("--story-id or --entry-id is required for comment-add")
    body = {
        "workspace_id": str(args.workspace_id),
        "entry_type": str(args.entry_type),
        "entry_id": str(args.entry_id),
        "description": args.description,
        "author": args.author,
    }
    if args.root_id:
        body["root_id"] = str(args.root_id)
    if args.reply_id:
        body["reply_id"] = str(args.reply_id)
    response = call_cached_api(path="/comments", method="POST", body=body)
    print_json(response)
    return 0


def comment_update(args: argparse.Namespace) -> int:
    body = {
        "workspace_id": str(args.workspace_id),
        "id": str(args.comment_id),
        "description": args.description,
    }
    if args.change_creator:
        body["change_creator"] = args.change_creator
    response = call_cached_api(path="/comments", method="POST", body=body)
    print_json(response)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    story_get_parser = subparsers.add_parser("story-get", help="Read a TAPD story by workspace and story ID")
    story_get_parser.add_argument("--workspace-id", required=True)
    story_get_parser.add_argument("--story-id", required=True)
    story_get_parser.add_argument("--fields", default=DEFAULT_STORY_FIELDS)
    story_get_parser.set_defaults(func=story_get)

    story_update_parser = subparsers.add_parser("story-update", help="Update a TAPD story from a JSON payload file")
    story_update_parser.add_argument("--workspace-id", required=True)
    story_update_parser.add_argument("--story-id", required=True)
    story_update_parser.add_argument("--payload-file", required=True)
    story_update_parser.set_defaults(func=story_update)

    design_story_parser = subparsers.add_parser(
        "design-story-get",
        help="Read a story through the TestX design endpoint using the correct workspace path",
    )
    design_story_parser.add_argument("--workspace-id", required=True)
    design_story_parser.add_argument("--story-id", required=True)
    design_story_parser.set_defaults(func=design_story_get)

    story_change_parser = subparsers.add_parser("story-change-list", help="Read TAPD story change history")
    story_change_parser.add_argument("--workspace-id", required=True)
    story_change_parser.add_argument("--story-id", required=True)
    story_change_parser.add_argument("--need-parse-changes", type=int, default=1)
    story_change_parser.add_argument("--limit", type=int)
    story_change_parser.add_argument("--page", type=int)
    story_change_parser.add_argument("--order")
    story_change_parser.add_argument("--fields")
    story_change_parser.set_defaults(func=story_change_list)

    comment_list_parser = subparsers.add_parser("comment-list", help="Read TAPD comments, defaulting to story comments")
    comment_list_parser.add_argument("--workspace-id", required=True)
    comment_list_parser.add_argument("--comment-id")
    comment_list_parser.add_argument("--entry-type", default="stories")
    comment_list_parser.add_argument("--entry-id")
    comment_list_parser.add_argument("--story-id", dest="entry_id")
    comment_list_parser.add_argument("--description")
    comment_list_parser.add_argument("--limit", type=int)
    comment_list_parser.add_argument("--page", type=int)
    comment_list_parser.add_argument("--order")
    comment_list_parser.add_argument("--fields")
    comment_list_parser.set_defaults(func=comment_list)

    comment_find_parser = subparsers.add_parser("comment-find", help="Find comments by plain-text keyword after reading comments")
    comment_find_parser.add_argument("--workspace-id", required=True)
    comment_find_parser.add_argument("--entry-type", default="stories")
    comment_find_parser.add_argument("--entry-id")
    comment_find_parser.add_argument("--story-id", dest="entry_id")
    comment_find_parser.add_argument("--keyword", required=True)
    comment_find_parser.add_argument("--limit", type=int, default=200)
    comment_find_parser.add_argument("--page", type=int)
    comment_find_parser.add_argument("--order", default="created desc")
    comment_find_parser.add_argument(
        "--fields",
        default="id,description,author,entry_type,entry_id,created,workspace_id",
    )
    comment_find_parser.set_defaults(func=comment_find)

    comment_add_parser = subparsers.add_parser("comment-add", help="Add a TAPD comment, defaulting to a story comment")
    comment_add_parser.add_argument("--workspace-id", required=True)
    comment_add_parser.add_argument("--entry-type", default="stories")
    comment_add_parser.add_argument("--entry-id")
    comment_add_parser.add_argument("--story-id", dest="entry_id")
    comment_add_parser.add_argument("--description", required=True)
    comment_add_parser.add_argument("--author", required=True)
    comment_add_parser.add_argument("--root-id")
    comment_add_parser.add_argument("--reply-id")
    comment_add_parser.set_defaults(func=comment_add)

    comment_update_parser = subparsers.add_parser("comment-update", help="Update a TAPD comment")
    comment_update_parser.add_argument("--workspace-id", required=True)
    comment_update_parser.add_argument("--comment-id", required=True)
    comment_update_parser.add_argument("--description", required=True)
    comment_update_parser.add_argument("--change-creator")
    comment_update_parser.set_defaults(func=comment_update)

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
