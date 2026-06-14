import os
import json

REQUIRED_ENV = ['JIRA_BASE_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN']

def jira_ticket_creator(payload: str = ""):
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        return (
            "【Jira_Ticket_Creator】已从云端应用市场拉取，但运行前需要配置凭据。\n"
            "缺少环境变量：" + ", ".join(missing) + "\n"
            "用途：把失败运行或修复任务转成 Jira 工单\n"
            "当前未执行外部请求，避免伪造成功结果。"
        )
    return (
        "【Jira_Ticket_Creator】凭据检查通过。\n"
        "服务：Jira\n"
        "请求载荷摘要：" + (payload[:500] if payload else "未提供 payload") + "\n"
        "说明：该连接器已安装，可在后续版本接入真实业务 API 调用。"
    )

SCHEMA = {
    "name": "jira_ticket_creator",
    "description": "Jira_Ticket_Creator 连接器。把失败运行或修复任务转成 Jira 工单；未配置凭据时只返回配置提示，不伪造执行成功。",
    "parameters": {
        "type": "object",
        "properties": {
            "payload": {"type": "string", "description": "要发送给 Jira 的文本或 JSON 载荷", "default": ""}
        }
    }
}
