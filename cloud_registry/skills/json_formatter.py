import json

def json_formatter(json_text: str, mode: str = "pretty"):
    try:
        data = json.loads(json_text)
    except Exception as exc:
        return "JSON 解析失败：" + str(exc)
    if mode == "compact":
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if mode == "keys":
        if isinstance(data, dict):
            return "顶层字段：" + ", ".join(map(str, data.keys()))
        if isinstance(data, list):
            return "数组长度：" + str(len(data))
        return "JSON 类型：" + type(data).__name__
    return json.dumps(data, ensure_ascii=False, indent=2)

SCHEMA = {
    "name": "json_formatter",
    "description": "格式化、压缩和校验 JSON 文本",
    "parameters": {
        "type": "object",
        "properties": {
            "json_text": {"type": "string", "description": "需要处理的 JSON 字符串"},
            "mode": {"type": "string", "description": "pretty / compact / keys", "enum": ["pretty", "compact", "keys"], "default": "pretty"}
        },
        "required": ["json_text"]
    }
}
