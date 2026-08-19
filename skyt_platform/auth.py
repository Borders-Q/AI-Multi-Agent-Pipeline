from __future__ import annotations

import ipaddress
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


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_request_source_allowed(request: Request) -> bool:
    if not settings.auth_enabled or settings.auth_mode != "local":
        return True
    return is_loopback_host(request.client.host if request.client else None)


def is_websocket_source_allowed(websocket: WebSocket) -> bool:
    if not settings.auth_enabled or settings.auth_mode != "local":
        return True
    return is_loopback_host(websocket.client.host if websocket.client else None)


def is_token_valid(token: str) -> bool:
    if not settings.auth_enabled:
        return True
    if settings.auth_mode != "token":
        return False
    return bool(token) and secrets.compare_digest(token, settings.access_token)


def is_request_authorized(request: Request) -> bool:
    if not settings.auth_enabled:
        return True
    if settings.auth_mode == "local":
        return is_loopback_host(request.client.host if request.client else None)
    return is_token_valid(token_from_request(request))


def is_websocket_authorized(websocket: WebSocket) -> bool:
    if not settings.auth_enabled:
        return True
    if settings.auth_mode == "local":
        return is_loopback_host(websocket.client.host if websocket.client else None)
    return is_token_valid(token_from_websocket(websocket))


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def unauthorized_response(detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "detail": detail or (
                "SkyT 当前为本机模式，请在运行 SkyT 的电脑上打开。"
                if settings.auth_mode == "local"
                else "需要登录后访问 SkyT。"
            ),
            "error_code": "AUTH_REQUIRED",
            "auth_mode": settings.auth_mode,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def set_auth_cookie(response: Any) -> None:
    if settings.auth_mode != "token" or not settings.access_token:
        return
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
