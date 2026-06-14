def requirement_summarizer(requirement: str):
    text = requirement.strip()
    tech_keywords = ["flask", "fastapi", "sqlite", "react", "vite", "python", "html", "css", "js", "ts", "typescript", "gpu", "api"]
    matched = [kw for kw in tech_keywords if kw.lower() in text.lower()]
    lines = [
        "# 需求整理",
        "## 原始目标",
        text[:800] if text else "未提供需求。",
        "## 识别到的技术要素",
        "、".join(matched) if matched else "未明确指定技术栈。",
        "## 建议下一步",
        "1. 确认必须落盘的文件范围。",
        "2. 生成可审查计划。",
        "3. 再进入代码生成、检查与报告。",
    ]
    return "\n".join(lines)

SCHEMA = {
    "name": "requirement_summarizer",
    "description": "整理用户需求为结构化 Markdown",
    "parameters": {
        "type": "object",
        "properties": {
            "requirement": {"type": "string", "description": "用户原始需求"}
        },
        "required": ["requirement"]
    }
}
