#!/usr/bin/env python3
"""Shared TAPD OAuth configuration helpers."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_AUTH_BASE_URL = "https://www.tapd.cn/oauth/"
DEFAULT_API_BASE_URL = "https://api.tapd.cn"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"
DEFAULT_SCOPES = "user story#read story#write"
DEFAULT_STORY_FIELDS = "id,name,description,workspace_id,status,priority,iteration_id,owner,developer,created,modified"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODEX_CONFIG_ENV = Path("~/.codex/config/tapd-base.env")
CLAUDE_CONFIG_ENV = Path("~/.claude/config/tapd-base.env")
CODEX_TOKEN_CACHE = Path("~/.codex/memories/tapd-base/session.json")
CLAUDE_TOKEN_CACHE = Path("~/.claude/tapd-base/session.json")


class ConfigError(RuntimeError):
    """Raised when the runtime environment is incomplete."""


def _candidate_env_paths() -> list[Path]:
    paths: list[Path] = []

    configured = os.getenv("TAPD_ENV_FILE", "").strip()
    if configured:
        return [Path(configured).expanduser()]

    codex_config_env = CODEX_CONFIG_ENV.expanduser()
    if codex_config_env not in paths:
        paths.append(codex_config_env)

    claude_config_env = CLAUDE_CONFIG_ENV.expanduser()
    if claude_config_env not in paths:
        paths.append(claude_config_env)

    cwd_env = Path.cwd() / ".env"
    if cwd_env not in paths:
        paths.append(cwd_env)

    project_env = PROJECT_ROOT / ".env"
    if project_env not in paths:
        paths.append(project_env)

    return paths


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()

    if "=" not in stripped:
        raise ConfigError(f"Invalid .env line: {line.rstrip()}")

    name, value = stripped.split("=", 1)
    name = name.strip()
    if not name:
        raise ConfigError(f"Invalid .env line: {line.rstrip()}")

    value = value.strip()
    if value:
        if value[0] not in {"'", '"'} and " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        try:
            parsed = shlex.split(value, comments=False)
        except ValueError as exc:
            raise ConfigError(f"Invalid .env value for {name}: {exc}") from exc
        value = parsed[0] if len(parsed) == 1 else " ".join(parsed)

    return name, value


def load_env_file() -> Path | None:
    for path in _candidate_env_paths():
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if not parsed:
                continue
            name, value = parsed
            os.environ.setdefault(name, value)
        return path

    configured = os.getenv("TAPD_ENV_FILE", "").strip()
    if configured:
        raise ConfigError(f"TAPD_ENV_FILE does not exist: {configured}")
    return None


def getenv_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def get_token_cache_path() -> Path:
    raw = os.getenv("TAPD_TOKEN_CACHE", "").strip()
    if raw:
        return Path(raw).expanduser()
    if CLAUDE_CONFIG_ENV.expanduser().exists() and not CODEX_CONFIG_ENV.expanduser().exists():
        return CLAUDE_TOKEN_CACHE.expanduser()
    return CODEX_TOKEN_CACHE.expanduser()


def get_runtime_config() -> dict[str, Any]:
    redirect_uri = os.getenv("TAPD_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()
    scopes = os.getenv("TAPD_SCOPES", DEFAULT_SCOPES).strip()
    auth_base_url = os.getenv("TAPD_AUTH_BASE_URL", DEFAULT_AUTH_BASE_URL).strip()
    api_base_url = os.getenv("TAPD_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    return {
        "client_id": os.getenv("TAPD_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("TAPD_CLIENT_SECRET", "").strip(),
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "auth_base_url": auth_base_url,
        "api_base_url": api_base_url,
        "token_cache": get_token_cache_path(),
    }


def validate_runtime_config(*, require_secret: bool) -> dict[str, Any]:
    config = get_runtime_config()
    if not config["client_id"]:
        raise ConfigError("Missing required environment variable: TAPD_CLIENT_ID")
    if require_secret and not config["client_secret"]:
        raise ConfigError("Missing required environment variable: TAPD_CLIENT_SECRET")

    parsed = urlparse(config["redirect_uri"])
    if parsed.scheme != "http":
        raise ConfigError("TAPD_REDIRECT_URI must use http for this local demo")
    if not parsed.hostname or not parsed.port:
        raise ConfigError("TAPD_REDIRECT_URI must include an explicit host and port")

    return config


def redact_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 6:
        return "*" * len(secret)
    return f"{secret[:3]}...{secret[-3:]}"


def build_testx_story_issue(*, story_id: str, workspace_id: str, issue_name: str = "") -> dict[str, str]:
    """Build the TestX issue payload shape that has been verified to work in this repo."""

    normalized_story_id = str(story_id).strip()
    normalized_workspace_id = str(workspace_id).strip()
    return {
        "IssueUid": normalized_story_id,
        "IssueName": issue_name,
        # TestX expects the workspace id in both fields. Do not pass a TAPD story URL here.
        "IssueUrl": normalized_workspace_id,
        "WorkspaceUid": normalized_workspace_id,
        "Type": "STORY",
        "Source": "TAPD",
    }
