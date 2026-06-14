import os
import json

REQUIRED_ENV = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION', 'AWS_S3_BUCKET']

def aws_s3_manager(payload: str = ""):
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        return (
            "【AWS_S3_Manager】已从云端应用市场拉取，但运行前需要配置凭据。\n"
            "缺少环境变量：" + ", ".join(missing) + "\n"
            "用途：上传或列出工作流产物\n"
            "当前未执行外部请求，避免伪造成功结果。"
        )
    return (
        "【AWS_S3_Manager】凭据检查通过。\n"
        "服务：AWS S3\n"
        "请求载荷摘要：" + (payload[:500] if payload else "未提供 payload") + "\n"
        "说明：该连接器已安装，可在后续版本接入真实业务 API 调用。"
    )

SCHEMA = {
    "name": "aws_s3_manager",
    "description": "AWS_S3_Manager 连接器。上传或列出工作流产物；未配置凭据时只返回配置提示，不伪造执行成功。",
    "parameters": {
        "type": "object",
        "properties": {
            "payload": {"type": "string", "description": "要发送给 AWS S3 的文本或 JSON 载荷", "default": ""}
        }
    }
}
