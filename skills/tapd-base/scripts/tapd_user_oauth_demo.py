#!/usr/bin/env python3
"""Minimal TAPD user OAuth demo with a local callback server."""

from __future__ import annotations

import argparse
import base64
import json
import secrets
import sys
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from tapd_oauth_common import (
    DEFAULT_API_BASE_URL,
    DEFAULT_AUTH_BASE_URL,
    DEFAULT_REDIRECT_URI,
    ConfigError,
    get_token_cache_path,
    load_env_file,
    redact_secret,
    validate_runtime_config,
)

DEFAULT_SCOPES = "user story#read story#write"
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass
class OAuthCallbackResult:
    code: str
    state: str
    resource: Any


def extract_workspace_id(resource: Any) -> str | None:
    if not isinstance(resource, dict):
        return None

    for key in ("workspace_id", "workspaceId", "WorkspaceId", "workspace_uid", "workspaceUid", "WorkspaceUid"):
        value = resource.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def merge_authorized_resource(
    *,
    token_resource: Any,
    callback_resource: Any = None,
    workspace_id: str | None = None,
) -> Any:
    resource = callback_resource if callback_resource is not None else token_resource
    if workspace_id:
        if isinstance(resource, dict):
            merged = dict(resource)
            merged["workspace_id"] = str(workspace_id)
            merged.setdefault("type", "workspace")
            return merged
        return {"type": "workspace", "workspace_id": str(workspace_id)}
    return resource


def build_auth_url(client_id: str, redirect_uri: str, scopes: str, state: str, auth_base_url: str) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "auth_by": "user",
        }
    )
    return f"{auth_base_url}?{query}"


def make_basic_auth_header(client_id: str, client_secret: str) -> str:
    joined = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(joined).decode("ascii")


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


def exchange_code_for_token(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    api_base_url: str,
) -> dict[str, Any]:
    payload = urlencode(
        {
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
    ).encode("utf-8")
    req = Request(
        f"{api_base_url}/tokens/request_token",
        data=payload,
        method="POST",
        headers={
            "Authorization": make_basic_auth_header(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    response = request_json(req)
    if response.get("status") != 1:
        raise RuntimeError(f"TAPD token exchange failed: {json.dumps(response, ensure_ascii=False)}")
    return response["data"]


def fetch_current_user(access_token: str, api_base_url: str) -> dict[str, Any]:
    req = Request(
        f"{api_base_url}/users/info",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    response = request_json(req)
    if response.get("status") != 1:
        raise RuntimeError(f"TAPD user info request failed: {json.dumps(response, ensure_ascii=False)}")
    return response["data"]


def try_fetch_current_user(access_token: str, api_base_url: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return fetch_current_user(access_token, api_base_url), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def save_session(
    token_data: dict[str, Any],
    user_data: dict[str, Any] | None,
    cache_path: Path,
    *,
    authorized_resource: Any,
) -> None:
    now = int(time.time())
    workspace_id = extract_workspace_id(authorized_resource) or extract_workspace_id(token_data.get("resource"))
    session = {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", ""),
        "resource": authorized_resource,
        "token_resource": token_data.get("resource"),
        "workspace_id": workspace_id,
        "obtained_at": now,
        "expires_in": token_data.get("expires_in"),
        "expires_at": now + int(token_data.get("expires_in", 0)),
        "user": user_data,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_resource_param(resource_raw: str) -> Any:
    if not resource_raw:
        return None
    try:
        return json.loads(resource_raw)
    except json.JSONDecodeError:
        return resource_raw


def run_callback_server(expected_state: str, redirect_uri: str, timeout_seconds: int) -> OAuthCallbackResult:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        raise ConfigError("TAPD_REDIRECT_URI must use http for this local demo")
    if not parsed.hostname or not parsed.port:
        raise ConfigError("TAPD_REDIRECT_URI must include an explicit host and port")

    done = Event()
    result: dict[str, Any] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path != parsed.path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            params = parse_qs(request.query)
            code = params.get("code", [""])[0]
            state = params.get("state", [""])[0]
            resource_raw = params.get("resource", [""])[0]

            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code")
                result["error"] = "Missing code in TAPD callback"
                done.set()
                return

            if state != expected_state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid state")
                result["error"] = "State mismatch in TAPD callback"
                done.set()
                return

            result["callback"] = OAuthCallbackResult(
                code=code,
                state=state,
                resource=parse_resource_param(resource_raw),
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("TAPD authorization received. Return to the terminal.".encode("utf-8"))
            done.set()

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = HTTPServer((parsed.hostname, parsed.port), CallbackHandler)

    def serve() -> None:
        while not done.is_set():
            server.handle_request()

    thread = Thread(target=serve, daemon=True)
    thread.start()

    if not done.wait(timeout_seconds):
        server.server_close()
        raise TimeoutError(f"Timed out after {timeout_seconds} seconds waiting for TAPD callback")

    server.server_close()
    if "error" in result:
        raise RuntimeError(result["error"])
    callback = result.get("callback")
    if not isinstance(callback, OAuthCallbackResult):
        raise RuntimeError("TAPD callback completed without a usable result")
    return callback


def authorize(args: argparse.Namespace) -> int:
    config = validate_runtime_config(require_secret=True)
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    redirect_uri = config["redirect_uri"]
    scopes = config["scopes"] or DEFAULT_SCOPES
    auth_base_url = config["auth_base_url"] or DEFAULT_AUTH_BASE_URL
    api_base_url = config["api_base_url"] or DEFAULT_API_BASE_URL
    cache_path = get_token_cache_path()
    state = secrets.token_urlsafe(24)

    auth_url = build_auth_url(client_id, redirect_uri, scopes, state, auth_base_url)
    print("Open this TAPD authorization URL in a browser:")
    print(auth_url)
    print("")
    if args.open:
        opened = webbrowser.open(auth_url)
        if opened:
            print("Browser open requested successfully.")
        else:
            print("Browser open request failed, open the URL manually.")
        print("")
    print(f"Waiting for TAPD callback on {redirect_uri} ...")

    callback = run_callback_server(state, redirect_uri, args.timeout)
    token_data = exchange_code_for_token(
        code=callback.code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        api_base_url=api_base_url,
    )
    authorized_resource = merge_authorized_resource(
        token_resource=token_data.get("resource"),
        callback_resource=callback.resource,
    )
    user_data, user_warning = try_fetch_current_user(token_data["access_token"], api_base_url)
    save_session(token_data, user_data, cache_path, authorized_resource=authorized_resource)

    print("")
    print(f"Token cached at: {cache_path}")
    print(f"Token scope: {token_data.get('scope', '')}")
    print(f"Authorized resource: {json.dumps(authorized_resource, ensure_ascii=False)}")
    if user_data is not None:
        print(f"Current user: {user_data.get('name') or user_data.get('nick')} ({user_data.get('id')})")
    elif user_warning:
        print(f"User profile lookup skipped: {user_warning}")
    return 0


def exchange_code(args: argparse.Namespace) -> int:
    config = validate_runtime_config(require_secret=True)
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    redirect_uri = config["redirect_uri"]
    api_base_url = config["api_base_url"] or DEFAULT_API_BASE_URL
    cache_path = get_token_cache_path()

    callback_resource = parse_resource_param(args.resource) if args.resource else None
    token_data = exchange_code_for_token(
        code=args.code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        api_base_url=api_base_url,
    )
    authorized_resource = merge_authorized_resource(
        token_resource=token_data.get("resource"),
        callback_resource=callback_resource,
        workspace_id=args.workspace_id,
    )
    user_data, user_warning = try_fetch_current_user(token_data["access_token"], api_base_url)
    save_session(token_data, user_data, cache_path, authorized_resource=authorized_resource)

    print(f"Token cached at: {cache_path}")
    print(f"Token scope: {token_data.get('scope', '')}")
    print(f"Authorized resource: {json.dumps(authorized_resource, ensure_ascii=False)}")
    if args.workspace_id:
        print(f"Workspace override: {args.workspace_id}")
    if user_data is not None:
        print(f"Current user: {user_data.get('name') or user_data.get('nick')} ({user_data.get('id')})")
    elif user_warning:
        print(f"User profile lookup skipped: {user_warning}")
    return 0


def show_auth_url(_: argparse.Namespace) -> int:
    config = validate_runtime_config(require_secret=False)
    client_id = config["client_id"]
    redirect_uri = config["redirect_uri"]
    scopes = config["scopes"] or DEFAULT_SCOPES
    auth_base_url = config["auth_base_url"] or DEFAULT_AUTH_BASE_URL
    state = secrets.token_urlsafe(24)
    print(build_auth_url(client_id, redirect_uri, scopes, state, auth_base_url))
    return 0


def check_config(_: argparse.Namespace) -> int:
    env_path = load_env_file()
    config = validate_runtime_config(require_secret=True)

    print("TAPD OAuth configuration is ready.")
    print(f"Loaded env file: {env_path or '(none, using process environment only)'}")
    print(f"TAPD_CLIENT_ID: {config['client_id']}")
    print(f"TAPD_CLIENT_SECRET: {redact_secret(config['client_secret'])}")
    print(f"TAPD_REDIRECT_URI: {config['redirect_uri']}")
    print(f"TAPD_SCOPES: {config['scopes'] or DEFAULT_SCOPES}")
    print(f"TAPD_AUTH_BASE_URL: {config['auth_base_url'] or DEFAULT_AUTH_BASE_URL}")
    print(f"TAPD_API_BASE_URL: {config['api_base_url'] or DEFAULT_API_BASE_URL}")
    print(f"TAPD_TOKEN_CACHE: {config['token_cache']}")
    print("")
    print("Suggested flow:")
    print('1. export TAPD_SKILLS_ROOT="${TAPD_SKILLS_ROOT:-$HOME/.codex/skills}"')
    print('2. python3 "$TAPD_SKILLS_ROOT/tapd-base/scripts/tapd_user_oauth_demo.py" authorize')
    print('3. python3 "$TAPD_SKILLS_ROOT/tapd-base/scripts/tapd_user_api.py" /users/info')
    return 0


def print_env_template(_: argparse.Namespace) -> int:
    print("TAPD_CLIENT_ID=your_client_id")
    print("TAPD_CLIENT_SECRET=your_client_secret")
    print(f"TAPD_REDIRECT_URI={DEFAULT_REDIRECT_URI}")
    print(f"TAPD_SCOPES={DEFAULT_SCOPES}")
    print("TAPD_TOKEN_CACHE=~/.codex/memories/tapd-base/session.json")
    print(f"TAPD_AUTH_BASE_URL={DEFAULT_AUTH_BASE_URL}")
    print(f"TAPD_API_BASE_URL={DEFAULT_API_BASE_URL}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check-config", help="Validate TAPD OAuth configuration and print the flow")
    check_parser.set_defaults(func=check_config)

    template_parser = subparsers.add_parser("print-env", help="Print a starter .env template")
    template_parser.set_defaults(func=print_env_template)

    exchange_parser = subparsers.add_parser("exchange-code", help="Exchange a TAPD code directly and cache the token")
    exchange_parser.add_argument("--code", required=True, help="Authorization code from a TAPD entry page callback")
    exchange_parser.add_argument("--workspace-id", help="Optional TAPD workspace ID to persist as TestX namespace")
    exchange_parser.add_argument(
        "--resource",
        help="Optional raw TAPD resource JSON from the callback, for example '{\"type\":\"workspace\",\"workspace_id\":123}'",
    )
    exchange_parser.set_defaults(func=exchange_code)

    authorize_parser = subparsers.add_parser("authorize", help="Run the local TAPD OAuth flow")
    authorize_parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Seconds to wait for the TAPD callback (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    authorize_parser.add_argument(
        "--open",
        action="store_true",
        help="Open the TAPD authorization URL in the default browser automatically",
    )
    authorize_parser.set_defaults(func=authorize)

    show_url_parser = subparsers.add_parser("show-url", help="Print the TAPD authorization URL")
    show_url_parser.set_defaults(func=show_auth_url)

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
    except TimeoutError as exc:
        print(f"Timeout: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
