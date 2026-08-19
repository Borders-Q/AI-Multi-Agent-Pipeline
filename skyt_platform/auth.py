from __future__ import annotations

import secrets
from typing import Any

from fastapi import Request, WebSocket
from fastapi.responses import JSONResponse

from skyt_platform.config import settings


PUBLIC_PATHS = {
    "/",
    "/health/live",
    "/health/ready",
    "/api/auth/login",
    "/api/auth/logout",
}


def _bearer(value: str | None) -> str:
    if not value:
        return ""
    scheme, _, token = value.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def token_from_request(request: Request) -> str:
    return request.cookies.get(settings.access_cookie_name, "") or _bearer(request.headers.get("authorization"))


def token_from_websocket(websocket: WebSocket) -> str:
    return websocket.cookies.get(settings.access_cookie_name, "") or websocket.query_params.get("access_token", "")


def is_token_valid(token: str) -> bool:
    if not settings.auth_enabled:
        return True
    return bool(token) and secrets.compare_digest(token, settings.access_token)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "需要登录后访问 SkyT。", "error_code": "AUTH_REQUIRED"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def set_auth_cookie(response: Any) -> None:
    response.set_cookie(
        settings.access_cookie_name,
        settings.access_token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


def clear_auth_cookie(response: Any) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/")
