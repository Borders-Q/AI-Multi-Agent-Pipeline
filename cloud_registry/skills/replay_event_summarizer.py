import json

def replay_event_summarizer(events_json: str, max_items: int = 8):
    try:
        events = json.loads(events_json)
    except Exception:
        return "事件数据不是标准 JSON：\n" + events_json[:1000]
    if not isinstance(events, list):
        return "事件数据应为数组。"
    lines = ["# 深度回放时间线摘要"]
    for idx, event in enumerate(events[:max(1, min(int(max_items or 8), 30))], 1):
        event_type = event.get("event_type") or event.get("type") or "UNKNOWN"
        summary = event.get("summary") or event.get("message") or event.get("detail") or ""
        lines.append(str(idx) + ". " + str(event_type) + " - " + str(summary)[:160])
    return "\n".join(lines)

SCHEMA = {
    "name": "replay_event_summarizer",
    "description": "整理深度回放事件为中文时间线",
    "parameters": {
        "type": "object",
        "properties": {
            "events_json": {"type": "string", "description": "事件数组 JSON"},
            "max_items": {"type": "integer", "description": "最多摘要条数", "default": 8}
        },
        "required": ["events_json"]
    }
}
