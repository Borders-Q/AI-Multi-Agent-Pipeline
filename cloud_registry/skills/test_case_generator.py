def test_case_generator(feature: str):
    return "\n".join([
        "# 测试用例：" + feature,
        "- 正常路径：输入合法数据，确认功能成功。",
        "- 空数据路径：输入为空，确认页面或接口给出提示。",
        "- 异常路径：输入非法数据，确认不会崩溃。",
        "- 回归路径：刷新页面或重启服务后，确认数据仍可用。",
        "- 展示路径：准备一条适合比赛演示的最短闭环。"
    ])

SCHEMA = {
    "name": "test_case_generator",
    "description": "生成简洁测试用例清单",
    "parameters": {
        "type": "object",
        "properties": {
            "feature": {"type": "string", "description": "要测试的功能"}
        },
        "required": ["feature"]
    }
}
