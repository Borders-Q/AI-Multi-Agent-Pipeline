def markdown_report_outline(title: str, context: str = ""):
    title = title.strip() or "天韬（SkyT）任务报告"
    return "\n".join([
        "# " + title,
        "## 1. 任务背景",
        context[:500] if context else "说明任务来源、目标和约束。",
        "## 2. 执行过程",
        "- 需求理解",
        "- 工作流编排",
        "- 工具调用与验证",
        "## 3. 产出结果",
        "- 生成文件",
        "- 运行地址",
        "- 报告结论",
        "## 4. 风险与后续优化",
        "- 需要人工确认的内容",
        "- 后续可扩展方向",
    ])

SCHEMA = {
    "name": "markdown_report_outline",
    "description": "生成中文 Markdown 报告大纲",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "报告标题"},
            "context": {"type": "string", "description": "任务上下文", "default": ""}
        },
        "required": ["title"]
    }
}
