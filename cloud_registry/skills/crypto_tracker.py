import urllib.request
import json

def get_crypto_price(coin_id: str):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=" + coin_id + "&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode())
        if coin_id in data:
            return coin_id.upper() + " 当前价格为 $" + str(data[coin_id]["usd"])
        return "未找到代币：" + coin_id
    except Exception as exc:
        return "查询币价失败：" + str(exc)

SCHEMA = {
    "name": "get_crypto_price",
    "description": "获取指定加密货币的最新美元价格",
    "parameters": {
        "type": "object",
        "properties": {
            "coin_id": {"type": "string", "description": "CoinGecko ID，如 bitcoin / ethereum"}
        },
        "required": ["coin_id"]
    }
}
