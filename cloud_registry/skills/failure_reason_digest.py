def failure_reason_digest(error_text: str):
    text = error_text.strip()
    lower = text.lower()
    hints = []
    if "port" in lower or "端口" in text:
        hints.append("端口占用或服务启动冲突")
    if "module not found" in lower or "no module named" in lower:
        hints.append("依赖缺失")
    if "syntaxerror" in lower:
        hints.append("语法错误")
    if "permission" in lower or "access" in lower:
        hints.append("权限或文件占用")
    return "\n".join([
        "# 失败原因归纳",
        "可能原因：" + ("、".join(hints) if hints else "需要结合日志继续确认"),
        "错误片段：",
        text[:1000],
        "建议优先级：1. 复现错误 2. 检查依赖/端口/语法 3. 重新运行验证。"
    ])

SCHEMA = {
    "name": "failure_reason_digest",
    "description": "归纳失败原因和修复优先级",
    "parameters": {
        "type": "object",
        "properties": {
            "error_text": {"type": "string", "description": "错误文本"}
        },
        "required": ["error_text"]
    }
}
