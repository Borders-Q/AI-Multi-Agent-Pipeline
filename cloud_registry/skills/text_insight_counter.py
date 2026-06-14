def text_insight_counter(text: str, keyword: str = ""):
    lines = text.splitlines()
    non_empty = [line for line in lines if line.strip()]
    chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_words = len([part for part in text.replace("\n", " ").split(" ") if part.strip()])
    result = [
        "总字符数：" + str(len(text)),
        "中文字符数：" + str(chinese_chars),
        "英文/符号词片段数：" + str(ascii_words),
        "总行数：" + str(len(lines)),
        "非空行数：" + str(len(non_empty)),
    ]
    if keyword:
        result.append("关键词 `" + keyword + "` 出现次数：" + str(text.count(keyword)))
    return "\n".join(result)

SCHEMA = {
    "name": "text_insight_counter",
    "description": "统计文本字数、行数、关键词频次",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "待统计文本"},
            "keyword": {"type": "string", "description": "可选关键词", "default": ""}
        },
        "required": ["text"]
    }
}
