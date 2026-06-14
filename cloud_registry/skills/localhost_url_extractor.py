import re
import json

def localhost_url_extractor(text: str):
    pattern = r"https?://(?:127\.0\.0\.1|localhost):\d+(?:/[^\s`)]*)?"
    urls = sorted(set(re.findall(pattern, text)))
    return json.dumps({"count": len(urls), "urls": urls}, ensure_ascii=False, indent=2)

SCHEMA = {
    "name": "localhost_url_extractor",
    "description": "提取本地预览 URL",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "输出文本"}
        },
        "required": ["text"]
    }
}
