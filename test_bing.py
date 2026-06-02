import urllib.request
import urllib.parse
import re

query = 'python'
url = f'https://cn.bing.com/search?q={urllib.parse.quote(query)}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        # Simple extraction for bing
        snippets = re.findall(r'<div class="b_caption">.*?<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        if not snippets:
            snippets = re.findall(r'<p class="b_paractl"[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        
        results = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:5]]
        print('Results:', results)
except Exception as e:
    print(e)
