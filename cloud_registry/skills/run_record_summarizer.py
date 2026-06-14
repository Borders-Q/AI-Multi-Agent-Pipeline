import json

def run_record_summarizer(run_data: str):
    try:
        data = json.loads(run_data)
    except Exception:
        data = {"raw": run_data}
    title = data.get("title") or data.get("run_id") or "未命名运行"
    status = data.get("status") or data.get("state") or "未知"
    tokens = data.get("total_tokens") or data.get("tokens") or "未记录"
    return "\n".join([
        "# 运行记录摘要",
        "- 标题：" + str(title),
        "- 状态：" + str(status),
        "- Token：" + str(tokens),
        "- 建议：在深度回放中优先查看失败事件、工具调用和最终报告。"
    ])

SCHEMA = {
    "name": "run_record_summarizer",
    "description": "压缩运行记录为中文工作记录摘要",
    "parameters": {
        "type": "object",
        "properties": {
            "run_data": {"type": "string", "description": "运行记录 JSON 或文本"}
        },
        "required": ["run_data"]
    }
}
