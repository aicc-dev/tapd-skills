#!/usr/bin/env python3
"""Helpers for TAPD story read/update workflows."""

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
