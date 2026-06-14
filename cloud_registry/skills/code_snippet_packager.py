def code_snippet_packager(file_name: str, code: str, language: str = ""):
    language = language.strip() or (file_name.rsplit(".", 1)[-1] if "." in file_name else "")
    return "```" + language + " " + file_name + "\n" + code.rstrip() + "\n```"

SCHEMA = {
    "name": "code_snippet_packager",
    "description": "把代码片段包装为带文件名的 Markdown 代码块",
    "parameters": {
        "type": "object",
        "properties": {
            "file_name": {"type": "string", "description": "文件名，例如 app.py"},
            "code": {"type": "string", "description": "代码内容"},
            "language": {"type": "string", "description": "代码语言，可选", "default": ""}
        },
        "required": ["file_name", "code"]
    }
}
