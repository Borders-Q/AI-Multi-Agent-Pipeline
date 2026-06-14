def competition_demo_script(project_name: str, features: str):
    items = [item.strip() for item in features.replace("\n", "、").split("、") if item.strip()]
    lines = ["# " + project_name + " 演示讲解顺序"]
    lines.append("1. 用一句话说明项目价值。")
    for idx, item in enumerate(items, 2):
        lines.append(str(idx) + ". 展示：" + item)
    lines.append(str(len(items) + 2) + ". 回到运行历史、深度回放和报告，强调可复盘闭环。")
    return "\n".join(lines)

SCHEMA = {
    "name": "competition_demo_script",
    "description": "生成比赛演示讲解顺序",
    "parameters": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "项目名称"},
            "features": {"type": "string", "description": "功能点，顿号或换行分隔"}
        },
        "required": ["project_name", "features"]
    }
}
