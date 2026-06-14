import os
from collections import Counter

def file_tree_summarizer(tree_text: str):
    files = []
    for line in tree_text.splitlines():
        token = line.strip().split(" ")[-1].strip("`|+-")
        if "." in token and not token.endswith("."):
            files.append(token)
    ext_counter = Counter(os.path.splitext(name)[1].lower() or "[无扩展名]" for name in files)
    top = "\n".join(["- " + ext + ": " + str(count) for ext, count in ext_counter.most_common(10)])
    return "\n".join([
        "# 目录树摘要",
        "识别文件数：" + str(len(files)),
        "## 扩展名分布",
        top if top else "未识别到文件。",
        "## 建议展示重点",
        "优先展示入口文件、配置文件、模板页面、静态资源和 README。"
    ])

SCHEMA = {
    "name": "file_tree_summarizer",
    "description": "压缩目录树文本并提取文件类型分布",
    "parameters": {
        "type": "object",
        "properties": {
            "tree_text": {"type": "string", "description": "目录树文本"}
        },
        "required": ["tree_text"]
    }
}
