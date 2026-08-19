from dataclasses import replace

from starlette.requests import Request

import skyt_platform.auth as auth
from skyt_platform.config import settings


def _request(host: str, *, cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "headers": headers,
        "client": (host, 1234),
        "query_string": b"",
        "scheme": "http",
        "server": (host, 8000),
    })


def test_local_mode_allows_only_loopback(monkeypatch):
    local_settings = replace(settings, auth_enabled=True, auth_mode="local", access_token="")
    monkeypatch.setattr(auth, "settings", local_settings)

    assert auth.is_request_authorized(_request("127.0.0.1"))
    assert auth.is_request_authorized(_request("::1"))
    assert not auth.is_request_authorized(_request("192.168.1.10"))


def test_token_mode_validates_cookie_without_persisting_anything(monkeypatch):
    token_settings = replace(settings, auth_enabled=True, auth_mode="token", access_token="deployment-secret")
    monkeypatch.setattr(auth, "settings", token_settings)

    assert auth.is_request_authorized(_request("192.168.1.10", cookie="skyt_access=deployment-secret"))
    assert not auth.is_request_authorized(_request("192.168.1.10", cookie="skyt_access=wrong"))
    assert not auth.is_token_valid("")
