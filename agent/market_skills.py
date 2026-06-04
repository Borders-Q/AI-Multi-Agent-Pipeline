MARKET_SKILLS = {
    "Crypto_Price_Tracker": {
        "id": "crypto_tracker",
        "name": "Crypto_Price_Tracker",
        "description": "查询加密货币（如 BTC, ETH）的实时价格 (USD)。",
        "icon": "💰",
        "code": """
import urllib.request
import json

def get_crypto_price(coin_id: str):
    \"\"\"获取指定加密货币的最新美元价格\"\"\"
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if coin_id in data:
                return f"{coin_id.upper()} 当前价格为: ${data[coin_id]['usd']}"
            else:
                return f"未找到代币: {coin_id}"
    except Exception as e:
        return f"查询币价失败: {str(e)}"

SCHEMA = {
    "name": "get_crypto_price",
    "description": "获取指定加密货币的最新美元价格",
    "parameters": {
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "description": "加密货币在CoinGecko上的ID（如 bitcoin, ethereum, dogecoin）"
            }
        },
        "required": ["coin_id"]
    }
}
"""
    },
    "Github_Repo_Analyzer": {
        "id": "github_analyzer",
        "name": "Github_Repo_Analyzer",
        "description": "获取指定 Github 仓库的基础信息（Star数，Forks，描述等）。",
        "icon": "🐙",
        "code": """
import urllib.request
import json

def analyze_github_repo(repo_name: str):
    \"\"\"获取 Github 仓库信息\"\"\"
    try:
        url = f"https://api.github.com/repos/{repo_name}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return (
                f"仓库: {data.get('full_name')}\\n"
                f"描述: {data.get('description')}\\n"
                f"Stars: {data.get('stargazers_count')} 🌟\\n"
                f"Forks: {data.get('forks_count')} 🍴\\n"
                f"主要语言: {data.get('language')}"
            )
    except Exception as e:
        return f"查询 Github 仓库失败，请确保格式为 'owner/repo' (例如 'facebook/react'): {str(e)}"

SCHEMA = {
    "name": "analyze_github_repo",
    "description": "获取 Github 仓库信息，如Stars和描述",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_name": {
                "type": "string",
                "description": "仓库名称，格式必须是 'owner/repo'"
            }
        },
        "required": ["repo_name"]
    }
}
"""
    }
}
