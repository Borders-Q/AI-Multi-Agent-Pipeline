def requirements_generator(project_type: str = "flask"):
    key = project_type.lower()
    deps = ["python-dotenv", "requests"]
    if "fastapi" in key:
        deps = ["fastapi", "uvicorn", "pydantic", "python-dotenv", "requests"]
    elif "flask" in key:
        deps = ["flask", "jinja2", "python-dotenv", "requests"]
    elif "ai" in key or "agent" in key:
        deps = ["fastapi", "uvicorn", "openai", "requests", "python-dotenv", "pydantic"]
    return "\n".join(deps)

SCHEMA = {
    "name": "requirements_generator",
    "description": "生成基础 Python requirements.txt 建议",
    "parameters": {
        "type": "object",
        "properties": {
            "project_type": {"type": "string", "description": "项目类型，例如 flask / fastapi / ai-agent", "default": "flask"}
        }
    }
}
