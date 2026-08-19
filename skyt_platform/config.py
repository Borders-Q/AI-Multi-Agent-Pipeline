from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=False)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    environment: str
    auth_enabled: bool
    access_token: str
    access_cookie_name: str
    allowed_origins: tuple[str, ...]
    max_request_bytes: int
    task_poll_seconds: float
    task_lease_seconds: int
    task_max_attempts: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    workspace_root: Path
    allow_absolute_paths: bool


def _load_access_token() -> str:
    token = os.getenv("SKYT_ACCESS_TOKEN", "").strip()
    if token:
        return token

    token = secrets.token_urlsafe(32)
    local_env = PROJECT_ROOT / ".env.local"
    existing = local_env.read_text(encoding="utf-8") if local_env.exists() else ""
    if "SKYT_ACCESS_TOKEN=" not in existing:
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        local_env.write_text(
            f"{existing}{prefix}SKYT_ACCESS_TOKEN={token}\n",
            encoding="utf-8",
        )
    os.environ["SKYT_ACCESS_TOKEN"] = token
    return token


def load_settings() -> Settings:
    origin_text = os.getenv(
        "SKYT_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    origins = tuple(item.strip() for item in origin_text.split(",") if item.strip())
    return Settings(
        environment=os.getenv("SKYT_ENV", "development").strip().lower(),
        auth_enabled=_env_bool("SKYT_AUTH_ENABLED", True),
        access_token=_load_access_token(),
        access_cookie_name=os.getenv("SKYT_ACCESS_COOKIE", "skyt_access").strip() or "skyt_access",
        allowed_origins=origins,
        max_request_bytes=_env_int("SKYT_MAX_REQUEST_BYTES", 8 * 1024 * 1024),
        task_poll_seconds=float(os.getenv("SKYT_TASK_POLL_SECONDS", "0.5")),
        task_lease_seconds=_env_int("SKYT_TASK_LEASE_SECONDS", 300),
        task_max_attempts=_env_int("SKYT_TASK_MAX_ATTEMPTS", 3),
        rate_limit_requests=_env_int("SKYT_RATE_LIMIT_REQUESTS", 120),
        rate_limit_window_seconds=_env_int("SKYT_RATE_LIMIT_WINDOW_SECONDS", 60),
        workspace_root=Path(os.getenv("SKYT_DEFAULT_WORKSPACE", str(PROJECT_ROOT / "workspace"))).expanduser(),
        allow_absolute_paths=_env_bool("SKYT_ALLOW_ABSOLUTE_PATHS", False),
    )


settings = load_settings()
