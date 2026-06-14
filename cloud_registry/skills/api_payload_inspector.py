import json

def api_payload_inspector(payload: str):
    size = len(payload.encode("utf-8"))
    try:
        data = json.loads(payload)
    except Exception as exc:
        return "Payload 大小：" + str(size) + " bytes\nJSON 解析失败：" + str(exc)
    if isinstance(data, dict):
        empty = [k for k, v in data.items() if v in (None, "", [], {})]
        return "\n".join([
            "Payload 大小：" + str(size) + " bytes",
            "顶层字段数：" + str(len(data)),
            "顶层字段：" + ", ".join(map(str, data.keys())),
            "空值字段：" + (", ".join(map(str, empty)) if empty else "无明显空值")
        ])
    if isinstance(data, list):
        return "Payload 大小：" + str(size) + " bytes\n数组长度：" + str(len(data))
    return "Payload 大小：" + str(size) + " bytes\nJSON 类型：" + type(data).__name__

SCHEMA = {
    "name": "api_payload_inspector",
    "description": "检查 API Payload 字段、大小和空值",
    "parameters": {
        "type": "object",
        "properties": {
            "payload": {"type": "string", "description": "JSON 或文本 Payload"}
        },
        "required": ["payload"]
    }
}
