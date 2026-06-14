import urllib.request
import re

def webpage_title_fetcher(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read(200000).decode("utf-8", errors="ignore")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        desc_match = re.search(r"<meta[^>]+name=['\\\"]description['\\\"][^>]+content=['\\\"](.*?)['\\\"]", html, re.I | re.S)
        title = re.sub(r"\\s+", " ", title_match.group(1)).strip() if title_match else "未找到 title"
        desc = re.sub(r"\\s+", " ", desc_match.group(1)).strip() if desc_match else "未找到 description"
        return "标题：" + title + "\n描述：" + desc
    except Exception as exc:
        return "网页读取失败：" + str(exc)

SCHEMA = {
    "name": "webpage_title_fetcher",
    "description": "联网读取网页标题和描述",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网页 URL"}
        },
        "required": ["url"]
    }
}
