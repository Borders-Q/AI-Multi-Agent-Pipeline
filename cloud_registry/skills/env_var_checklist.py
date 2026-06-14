def env_var_checklist(env_names: str):
    names = [name.strip() for name in env_names.replace("\n", ",").split(",") if name.strip()]
    if not names:
        return "未提供环境变量名称。"
    lines = ["# 环境变量检查清单"]
    for name in names:
        lines.append("- [ ] " + name + "：待配置")
    lines.append("\n建议：密钥类变量不要写入仓库，优先放入 .env 或系统环境变量。")
    return "\n".join(lines)

SCHEMA = {
    "name": "env_var_checklist",
    "description": "生成环境变量配置检查清单",
    "parameters": {
        "type": "object",
        "properties": {
            "env_names": {"type": "string", "description": "环境变量名称，逗号或换行分隔"}
        },
        "required": ["env_names"]
    }
}
