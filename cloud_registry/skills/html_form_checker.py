import re

def html_form_checker(html: str):
    form_count = len(re.findall(r"<form\b", html, re.I))
    input_count = len(re.findall(r"<input\b|<textarea\b|<select\b", html, re.I))
    label_count = len(re.findall(r"<label\b", html, re.I))
    submit_count = len(re.findall(r"type=['\"]submit['\"]|<button\b", html, re.I))
    return "\n".join([
        "# HTML 表单检查",
        "- form 数量：" + str(form_count),
        "- 输入控件数量：" + str(input_count),
        "- label 数量：" + str(label_count),
        "- 提交按钮线索：" + str(submit_count),
        "- 建议：" + ("结构基本完整。" if form_count and input_count and submit_count else "请补齐 form、输入控件和提交按钮。")
    ])

SCHEMA = {
    "name": "html_form_checker",
    "description": "检查 HTML 表单结构完整性",
    "parameters": {
        "type": "object",
        "properties": {
            "html": {"type": "string", "description": "HTML 文本"}
        },
        "required": ["html"]
    }
}
