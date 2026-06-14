import os
import json

REQUIRED_ENV = ['NOTION_TOKEN', 'NOTION_PARENT_PAGE_ID']

def notion_page_sync(payload: str = ""):
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        return (
            "【Notion_Page_Sync】已从云端应用市场拉取，但运行前需要配置凭据。\n"
            "缺少环境变量：" + ", ".join(missing) + "\n"
            "用途：把任务总结或报告同步到 Notion\n"
            "当前未执行外部请求，避免伪造成功结果。"
        )
    return (
        "【Notion_Page_Sync】凭据检查通过。\n"
        "服务：Notion\n"
        "请求载荷摘要：" + (payload[:500] if payload else "未提供 payload") + "\n"
        "说明：该连接器已安装，可在后续版本接入真实业务 API 调用。"
    )

SCHEMA = {
    "name": "notion_page_sync",
    "description": "Notion_Page_Sync 连接器。把任务总结或报告同步到 Notion；未配置凭据时只返回配置提示，不伪造执行成功。",
    "parameters": {
        "type": "object",
        "properties": {
            "payload": {"type": "string", "description": "要发送给 Notion 的文本或 JSON 载荷", "default": ""}
        }
    }
}
