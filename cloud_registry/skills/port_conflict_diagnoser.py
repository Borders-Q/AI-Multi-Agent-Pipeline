def port_conflict_diagnoser(port: int, log_text: str = ""):
    port = int(port)
    return "\n".join([
        "# 端口冲突诊断",
        "- 目标端口：" + str(port),
        "- 常见原因：旧服务未关闭、端口被系统进程占用、服务启动后立即崩溃。",
        "- 建议命令：netstat -ano | findstr :" + str(port),
        "- 建议策略：不要强杀未知进程，优先切换到下一个可用端口并更新右侧预览地址。",
        "## 日志片段",
        (log_text[:800] if log_text else "未提供日志。")
    ])

SCHEMA = {
    "name": "port_conflict_diagnoser",
    "description": "生成端口占用排查建议",
    "parameters": {
        "type": "object",
        "properties": {
            "port": {"type": "integer", "description": "端口号"},
            "log_text": {"type": "string", "description": "可选日志文本", "default": ""}
        },
        "required": ["port"]
    }
}
