import os
import json

REQUIRED_ENV = ['DATABASE_URL']

def postgresql_query(payload: str = ""):
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        return (
            "【PostgreSQL_Query】已从云端应用市场拉取，但运行前需要配置凭据。\n"
            "缺少环境变量：" + ", ".join(missing) + "\n"
            "用途：执行只读 SQL 查询和结构分析\n"
            "当前未执行外部请求，避免伪造成功结果。"
        )
    return (
        "【PostgreSQL_Query】凭据检查通过。\n"
        "服务：PostgreSQL\n"
        "请求载荷摘要：" + (payload[:500] if payload else "未提供 payload") + "\n"
        "说明：该连接器已安装，可在后续版本接入真实业务 API 调用。"
    )

SCHEMA = {
    "name": "postgresql_query",
    "description": "PostgreSQL_Query 连接器。执行只读 SQL 查询和结构分析；未配置凭据时只返回配置提示，不伪造执行成功。",
    "parameters": {
        "type": "object",
        "properties": {
            "payload": {"type": "string", "description": "要发送给 PostgreSQL 的文本或 JSON 载荷", "default": ""}
        }
    }
}
