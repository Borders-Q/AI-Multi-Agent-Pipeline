import re

def log_error_analyzer(log_text: str):
    lines = [line for line in log_text.splitlines() if line.strip()]
    error_lines = [line for line in lines if re.search(r"error|exception|traceback|failed|失败|报错", line, re.I)]
    tail = "\n".join(lines[-20:])
    return "\n".join([
        "# 日志错误分析",
        "错误相关行数：" + str(len(error_lines)),
        "最后一条错误：" + (error_lines[-1] if error_lines else "未识别到明显错误行"),
        "## 最近日志片段",
        tail,
        "## 建议",
        "优先检查最后一条错误附近的文件、端口、依赖和环境变量。"
    ])

SCHEMA = {
    "name": "log_error_analyzer",
    "description": "分析日志错误并输出中文诊断摘要",
    "parameters": {
        "type": "object",
        "properties": {
            "log_text": {"type": "string", "description": "日志文本"}
        },
        "required": ["log_text"]
    }
}
