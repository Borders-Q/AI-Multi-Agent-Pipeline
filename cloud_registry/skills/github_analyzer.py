import urllib.request
import json

def analyze_github_repo(repo_name: str):
    try:
        url = "https://api.github.com/repos/" + repo_name
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode())
        return (
            "仓库：" + str(data.get("full_name")) + "\n"
            "描述：" + str(data.get("description")) + "\n"
            "Stars：" + str(data.get("stargazers_count")) + "\n"
            "Forks：" + str(data.get("forks_count")) + "\n"
            "主要语言：" + str(data.get("language"))
        )
    except Exception as exc:
        return "查询 GitHub 仓库失败，请确保格式为 owner/repo：" + str(exc)

SCHEMA = {
    "name": "analyze_github_repo",
    "description": "获取 GitHub 仓库信息，如 Stars、Forks 和描述",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_name": {"type": "string", "description": "仓库名称，格式 owner/repo"}
        },
        "required": ["repo_name"]
    }
}
