import json

def token_usage_summarizer(token_usage_json: str):
    try:
        data = json.loads(token_usage_json)
    except Exception:
        return "Token 数据不是标准 JSON：\n" + token_usage_json[:1000]
    api = data.get("api_tokens", 0)
    local = data.get("local_tokens", 0)
    total = data.get("total_tokens", api + local)
    source = data.get("source") or data.get("token_source") or "未知"
    return "\n".join([
        "# Token 消耗摘要",
        "- API Token：" + str(api),
        "- 本地 Token：" + str(local),
        "- 总计：" + str(total),
        "- 来源：" + str(source),
        "- 建议：优先让本地 GPU 做上下文压缩，再把高价值上下文交给 API。"
    ])

SCHEMA = {
    "name": "token_usage_summarizer",
    "description": "整理 API / 本地 GPU Token 消耗",
    "parameters": {
        "type": "object",
        "properties": {
            "token_usage_json": {"type": "string", "description": "Token usage JSON"}
        },
        "required": ["token_usage_json"]
    }
}
