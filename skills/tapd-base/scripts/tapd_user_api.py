#!/usr/bin/env python3
"""Call a TAPD user-scope API with a cached OAuth access token."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tapd_oauth_common import DEFAULT_API_BASE_URL, ConfigError, get_token_cache_path, load_env_file


def load_session(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        raise FileNotFoundError(f"Token cache does not exist: {cache_path}")
    return json.loads(cache_path.read_text(encoding="utf-8"))


def ensure_token_valid(session: dict[str, Any]) -> None:
    expires_at = int(session.get("expires_at", 0))
    if not expires_at:
        return
    if time.time() >= expires_at:
        raise RuntimeError("Cached TAPD access token has expired. Run authorize again.")


def request_json(req: Request) -> Any:
    try:
        with urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from TAPD: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while calling TAPD: {exc}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from TAPD: {body}") from exc


def call_api(
    *,
    path: str,
    method: str,
    query: list[str],
    body: str | None,
    access_token: str,
    api_base_url: str,
) -> Any:
    normalized_path = path if path.startswith("/") else f"/{path}"
    url = f"{api_base_url}{normalized_path}"
    if query:
        pairs: list[tuple[str, str]] = []
        for item in query:
            if "=" not in item:
                raise ValueError(f"Invalid query parameter {item!r}, expected key=value")
            key, value = item.split("=", 1)
            pairs.append((key, value))
        url += "?" + urlencode(pairs)

    data = body.encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, method=method.upper(), headers=headers)
    return request_json(req)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="/users/info", help="TAPD API path, default: /users/info")
    parser.add_argument("--method", default="GET", help="HTTP method, default: GET")
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Query parameter in key=value form. Repeat the flag to add more.",
    )
    parser.add_argument("--body", help="Optional JSON string request body")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        load_env_file()
        cache_path = get_token_cache_path()
        api_base_url = os.getenv("TAPD_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
        session = load_session(cache_path)
        ensure_token_valid(session)
        response = call_api(
            path=args.path,
            method=args.method,
            query=args.query,
            body=args.body,
            access_token=session["access_token"],
            api_base_url=api_base_url,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
