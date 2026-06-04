import requests
import json
from agent.skills import tool_manager

def http_requester(url: str, method: str = "GET", headers: dict = None, data: dict = None) -> str:
    """
    发送 HTTP GET 或 POST 请求并返回响应。
    """
    if headers is None:
        headers = {}
        
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return f"Error: Unsupported HTTP method {method}. Use GET or POST."
            
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
        
        try:
            result["json"] = response.json()
        except json.JSONDecodeError:
            # If not JSON, try to return text (truncate if too long)
            text = response.text
            result["text"] = text[:2000] + ("..." if len(text) > 2000 else "")
            
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except requests.Timeout:
        return f"Error: Request to {url} timed out."
    except requests.RequestException as e:
        return f"Error executing HTTP request: {str(e)}"

tool_manager.register_tool(
    func=http_requester,
    name="http_requester",
    description="发送 HTTP GET 或 POST 请求并返回响应体（支持 JSON 或文本）。可用于调用第三方 API。",
    params_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "请求的 URL"},
            "method": {"type": "string", "description": "HTTP 方法 (GET, POST)", "default": "GET"},
            "headers": {"type": "object", "description": "HTTP Headers 字典", "additionalProperties": True},
            "data": {"type": "object", "description": "POST 的 JSON 数据，或 GET 的 Query Params", "additionalProperties": True}
        },
        "required": ["url"]
    }
)
