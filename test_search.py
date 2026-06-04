import urllib.request
import urllib.parse
import re

def test_sogou():
    query = 'python'
    url = f'https://www.sogou.com/web?query={urllib.parse.quote(query)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
            # Look for summary snippets
            snippets = re.findall(r'<div class="vr-summary[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
            if not snippets:
                snippets = re.findall(r'<div class="fz-mid[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
            results = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
            print('Sogou:', results[:5])
    except Exception as e:
        print('Sogou error:', e)

test_sogou()
