import math
from typing import Any, Dict, Iterable, Optional


LOCAL_MODEL_HINTS = ("ollama", "gemma", "llama", "qwen", "mistral", "deepseek-r1", "local")


def is_local_provider(provider: Optional[str] = None, model: Optional[str] = None) -> bool:
    text = f"{provider or ''} {model or ''}".lower()
    return any(hint in text for hint in LOCAL_MODEL_HINTS)


def _get_value(source: Any, key: str, default: int = 0) -> int:
    if source is None:
        return default
    if isinstance(source, dict):
        value = source.get(key, default)
    else:
        value = getattr(source, key, default)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _get_nested_value(source: Any, parent_key: str, child_key: str, default: int = 0) -> int:
    if source is None:
        return default
    parent = source.get(parent_key) if isinstance(source, dict) else getattr(source, parent_key, None)
    return _get_value(parent, child_key, default)


def estimate_text_tokens(text: Any) -> int:
    if text is None:
        return 0
    if not isinstance(text, str):
        text = str(text)
    compact = text.strip()
    if not compact:
        return 0
    cjk_chars = sum(1 for ch in compact if "\u4e00" <= ch <= "\u9fff")
    other_chars = len(compact) - cjk_chars
    # A conservative deterministic fallback only used when the provider omits usage.
    return max(1, math.ceil(cjk_chars / 1.7 + other_chars / 4))


def estimate_messages_tokens(messages: Optional[Iterable[Dict[str, Any]]]) -> int:
    if not messages:
        return 0
    total = 0
    for message in messages:
        if not isinstance(message, dict):
            total += estimate_text_tokens(message)
            continue
        total += 4
        total += estimate_text_tokens(message.get("role", ""))
        content = message.get("content", "")
        if isinstance(content, list):
            total += sum(estimate_text_tokens(part) for part in content)
        else:
            total += estimate_text_tokens(content)
        if message.get("tool_calls"):
            total += estimate_text_tokens(message.get("tool_calls"))
        if message.get("name"):
            total += estimate_text_tokens(message.get("name"))
    return total


def _normalize_source(real_tokens: int, estimated_tokens: int) -> str:
    if real_tokens > 0 and estimated_tokens > 0:
        return "mixed"
    if real_tokens > 0:
        return "real"
    if estimated_tokens > 0:
        return "estimated"
    return "none"


def build_usage_call(
    *,
    provider: Optional[str],
    model: Optional[str],
    role: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
    source: str = "real",
    is_local: Optional[bool] = None,
) -> Dict[str, Any]:
    total = int(total_tokens or (input_tokens or 0) + (output_tokens or 0))
    local = is_local_provider(provider, model) if is_local is None else bool(is_local)
    estimated = source == "estimated"
    return {
        "provider": provider or "unknown",
        "model": model or "unknown",
        "role": role,
        "source": source,
        "estimated": estimated,
        "is_local": local,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": total,
        "api_tokens": 0 if local else total,
        "local_tokens": total if local else 0,
        "cached_tokens": int(cached_tokens or 0),
        "reasoning_tokens": int(reasoning_tokens or 0),
        "real_tokens": 0 if estimated else total,
        "estimated_tokens": total if estimated else 0,
    }


def usage_from_openai_response(
    response: Any,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    role: str = "llm_call",
    is_local: Optional[bool] = None,
    messages: Optional[Iterable[Dict[str, Any]]] = None,
    output_text: Optional[str] = None,
) -> Dict[str, Any]:
    usage = getattr(response, "usage", None)
    provider = provider or getattr(response, "skyt_provider", None)
    model = model or getattr(response, "model", None) or getattr(response, "skyt_model", None)

    prompt_tokens = _get_value(usage, "prompt_tokens")
    completion_tokens = _get_value(usage, "completion_tokens")
    total_tokens = _get_value(usage, "total_tokens")
    cached_tokens = _get_nested_value(usage, "prompt_tokens_details", "cached_tokens")
    reasoning_tokens = _get_nested_value(usage, "completion_tokens_details", "reasoning_tokens")

    if total_tokens or prompt_tokens or completion_tokens:
        usage_source = "estimated" if (
            isinstance(usage, dict) and usage.get("estimated")
        ) or getattr(usage, "estimated", False) else "real"
        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens
        return build_usage_call(
            provider=provider,
            model=model,
            role=role,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            source=usage_source,
            is_local=is_local,
        )

    input_estimate = estimate_messages_tokens(messages)
    output_estimate = estimate_text_tokens(output_text)
    return build_usage_call(
        provider=provider,
        model=model,
        role=role,
        input_tokens=input_estimate,
        output_tokens=output_estimate,
        total_tokens=input_estimate + output_estimate,
        source="estimated",
        is_local=is_local,
    )


def usage_from_ollama_response(
    data: Dict[str, Any],
    *,
    model: Optional[str],
    role: str,
    messages: Optional[Iterable[Dict[str, Any]]] = None,
    output_text: Optional[str] = None,
) -> Dict[str, Any]:
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    total_tokens = prompt_tokens + completion_tokens

    if total_tokens:
        return build_usage_call(
            provider="ollama",
            model=model,
            role=role,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            source="real",
            is_local=True,
        )

    input_estimate = estimate_messages_tokens(messages)
    output_estimate = estimate_text_tokens(output_text)
    return build_usage_call(
        provider="ollama",
        model=model,
        role=role,
        input_tokens=input_estimate,
        output_tokens=output_estimate,
        total_tokens=input_estimate + output_estimate,
        source="estimated",
        is_local=True,
    )


def empty_token_summary() -> Dict[str, Any]:
    return {
        "api_tokens": 0,
        "local_tokens": 0,
        "total_tokens": 0,
        "real_tokens": 0,
        "estimated_tokens": 0,
        "source": "none",
        "calls": [],
    }


def normalize_token_summary(value: Any) -> Dict[str, Any]:
    if not value:
        return empty_token_summary()
    if isinstance(value, TokenAccumulator):
        return value.to_dict()
    if isinstance(value, dict) and "calls" in value:
        return merge_usage_calls(value.get("calls") or [])
    if isinstance(value, dict) and "total_tokens" in value:
        return merge_usage_calls([value])
    return empty_token_summary()


def merge_usage_calls(calls: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_calls = [call for call in calls if isinstance(call, dict)]
    summary = empty_token_summary()
    summary["calls"] = normalized_calls
    for call in normalized_calls:
        total = int(call.get("total_tokens") or 0)
        real = int(call.get("real_tokens") or 0)
        estimated = int(call.get("estimated_tokens") or 0)
        if total and not real and not estimated:
            if call.get("source") == "real":
                real = total
            else:
                estimated = total
        summary["api_tokens"] += int(call.get("api_tokens") or 0)
        summary["local_tokens"] += int(call.get("local_tokens") or 0)
        summary["total_tokens"] += total
        summary["real_tokens"] += real
        summary["estimated_tokens"] += estimated
    summary["source"] = _normalize_source(summary["real_tokens"], summary["estimated_tokens"])
    return summary


class TokenAccumulator:
    def __init__(self):
        self.calls = []

    def add(self, usage: Any) -> Dict[str, Any]:
        if not usage:
            return self.to_dict()
        if isinstance(usage, dict) and "calls" in usage:
            for call in usage.get("calls") or []:
                if call:
                    self.calls.append(call)
        elif isinstance(usage, dict):
            self.calls.append(usage)
        return self.to_dict()

    def extend(self, summary: Any) -> Dict[str, Any]:
        return self.add(summary)

    def to_dict(self) -> Dict[str, Any]:
        return merge_usage_calls(self.calls)

    @property
    def total_tokens(self) -> int:
        return self.to_dict()["total_tokens"]


def format_token_summary(summary: Any) -> str:
    data = normalize_token_summary(summary)
    suffix = "（估算）" if data["source"] == "estimated" else "（真实+估算）" if data["source"] == "mixed" else ""
    return f"API {data['api_tokens']} · 本地 {data['local_tokens']} · 总计 {data['total_tokens']} tokens{suffix}"
