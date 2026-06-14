import re
import json

def regex_extractor(text: str, pattern: str, max_results: int = 20):
    try:
        matches = re.findall(pattern, text, flags=re.MULTILINE)
    except Exception as exc:
        return "正则表达式无效：" + str(exc)
    limited = matches[:max(1, min(int(max_results or 20), 100))]
    return json.dumps({"count": len(matches), "results": limited}, ensure_ascii=False, indent=2)

SCHEMA = {
    "name": "regex_extractor",
    "description": "按正则表达式从文本中提取信息",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "待提取文本"},
            "pattern": {"type": "string", "description": "Python re 正则表达式"},
            "max_results": {"type": "integer", "description": "最多返回条数", "default": 20}
        },
        "required": ["text", "pattern"]
    }
}
