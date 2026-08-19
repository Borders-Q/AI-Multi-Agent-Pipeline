from __future__ import annotations

from typing import Any


PROFILE_ORDER = {
    "fast": ("ollama", "npu", "deepseek", "openai"),
    "strong": ("openai", "anthropic", "gemini", "deepseek", "ollama"),
    "critic": ("anthropic", "openai", "gemini", "deepseek", "ollama"),
    "fallback": ("openai", "deepseek", "ollama", "gemini", "anthropic"),
    "auto": ("openai", "anthropic", "gemini", "deepseek", "ollama"),
}


class ModelRouter:
    def __init__(self, clients: dict[str, Any] | None = None):
        self.clients = clients or {}

    def select(self, profile: str = "auto", *, preferred: str | None = None, exclude: set[str] | None = None) -> str | None:
        exclude = exclude or set()
        if preferred and preferred in self.clients and preferred not in exclude:
            return preferred
        normalized = str(profile or "auto").lower()
        if normalized in self.clients and normalized not in exclude:
            return normalized
        for provider in PROFILE_ORDER.get(normalized, PROFILE_ORDER["auto"]):
            if provider in self.clients and provider not in exclude:
                return provider
        for provider in self.clients:
            if provider not in exclude:
                return provider
        return None

    def candidates(self, profile: str = "auto", *, exclude: set[str] | None = None) -> list[str]:
        exclude = exclude or set()
        ordered = list(PROFILE_ORDER.get(str(profile or "auto").lower(), PROFILE_ORDER["auto"]))
        ordered.extend(self.clients.keys())
        return list(dict.fromkeys(provider for provider in ordered if provider in self.clients and provider not in exclude))
