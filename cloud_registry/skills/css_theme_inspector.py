import re

def css_theme_inspector(css: str):
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    variables = re.findall(r"--[a-zA-Z0-9_-]+", css)
    media = re.findall(r"@media\b", css)
    return "\n".join([
        "# CSS 主题检查",
        "- 十六进制颜色数量：" + str(len(hex_colors)),
        "- CSS 变量数量：" + str(len(set(variables))),
        "- 媒体查询数量：" + str(len(media)),
        "- 建议：核心颜色优先抽成变量，深浅色适配避免写死单一颜色。"
    ])

SCHEMA = {
    "name": "css_theme_inspector",
    "description": "检查 CSS 颜色、变量和响应式线索",
    "parameters": {
        "type": "object",
        "properties": {
            "css": {"type": "string", "description": "CSS 文本"}
        },
        "required": ["css"]
    }
}
