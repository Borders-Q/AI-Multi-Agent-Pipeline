import json
import urllib.request
import urllib.parse
from agent.skills import tool_manager

# -------------------------
# 1. Web Search Skill
# -------------------------
def web_search(query: str, max_results: int = 3):
    """
    Search the web for real-time information.
    """
    import urllib.parse
    import re
    
    results = []
    # Primary: Bing via Headless Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Use the built-in Microsoft Edge to avoid downloading the 180MB chromium binary
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            page.goto(f"https://cn.bing.com/search?q={urllib.parse.quote(query)}", timeout=15000)
            page.wait_for_selector('ol#b_results', timeout=5000)
            
            extracted = page.evaluate('''() => {
                const snippets = [];
                const elements = document.querySelectorAll('.b_caption p, .b_paractl, .b_algo p, .b_algo .b_lineclamp');
                for (let el of elements) {
                    let text = el.innerText.trim();
                    if (text.length > 20 && !snippets.includes(text)) {
                        snippets.push(text);
                    }
                }
                return snippets;
            }''')
            results = extracted
            browser.close()
    except Exception as e:
        print(f"Bing Playwright Search Error: {e}")
        pass
        
    # Fallback: Sogou via urllib
    if not results:
        try:
            import urllib.request
            url = f"https://www.sogou.com/web?query={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snippets = re.findall(r'<div class="vr-summary[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
                if not snippets:
                    snippets = re.findall(r'<div class="fz-mid[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
                
                fallback_results = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
                results = [res.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&#39;', "'") for res in fallback_results if res]
        except Exception as e:
            print(f"Sogou Fallback Error: {e}")

    if not results:
        return "未找到相关搜索结果，或搜索被拦截。"
    
    summary = "\n".join([f"{i+1}. {res}" for i, res in enumerate(results[:max_results])])
    return f"【搜索结果】\n{summary}"

tool_manager.register_tool(
    func=web_search,
    name="web_search",
    description="在互联网上搜索实时新闻、知识和解答。",
    params_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "要搜索的关键词"},
            "max_results": {"type": "integer", "description": "返回的最大结果数量", "default": 3}
        },
        "required": ["query"]
    }
)

# -------------------------
# 2. Data Visualizer Skill
# -------------------------
def data_visualizer(title: str, chart_type: str, labels: list, dataset: list):
    """
    Generate JSON payload for Frontend Echarts visualization.
    """
    payload = {
        "title": title,
        "type": chart_type,
        "labels": labels,
        "dataset": dataset
    }
    # We return a specific XML/JSON block that the frontend can intercept and render as Echarts
    return f"【前端图表指令】\n<ECHARTS_DATA>\n{json.dumps(payload, ensure_ascii=False)}\n</ECHARTS_DATA>\n(已成功生成图表数据，请在回答中引导用户查看图表)"

tool_manager.register_tool(
    func=data_visualizer,
    name="data_visualizer",
    description="生成数据可视化图表（支持 bar, pie, line）。当用户要求绘制图表、对比数据时使用此技能。",
    params_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "图表标题"},
            "chart_type": {"type": "string", "description": "图表类型 (bar, line, pie)", "enum": ["bar", "line", "pie"]},
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "X轴标签或饼图类别"
            },
            "dataset": {
                "type": "array",
                "items": {"type": "number"},
                "description": "对应标签的数值数组"
            }
        },
        "required": ["title", "chart_type", "labels", "dataset"]
    }
)

# -------------------------
# 3. Math Sandbox Skill
# -------------------------
def math_sandbox(expression: str):
    """
    Safely evaluate math expressions.
    """
    try:
        import ast
        import operator
        import math
        
        allowed_operators = {
            ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.Pow: operator.pow, ast.BitXor: operator.xor,
            ast.USub: operator.neg
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return allowed_operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return allowed_operators[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(node)
                
        result = eval_expr(ast.parse(expression, mode='eval').body)
        return f"数学表达式 `{expression}` 的计算结果为: {result}"
    except Exception as e:
        return f"无法计算表达式 '{expression}'，错误: {e}"

tool_manager.register_tool(
    func=math_sandbox,
    name="math_sandbox",
    description="安全计算复杂的数学表达式（支持加减乘除、乘方等 Python 基础算术表达式）。",
    params_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Python 语法的数学表达式，例如 '2 ** 10 + 5'"}
        },
        "required": ["expression"]
    }
)

# -------------------------
# 4. Mindmap Generator Skill
# -------------------------
def mindmap_generator(topic: str, markdown_list: str):
    """
    Generate Mermaid Mindmap payload.
    """
    return f"【前端脑图指令】\n<MERMAID_MINDMAP>\nmindmap\n  root(({topic}))\n{markdown_list}\n</MERMAID_MINDMAP>\n(已成功生成思维导图，请在回答中引导用户查看脑图)"

tool_manager.register_tool(
    func=mindmap_generator,
    name="mindmap_generator",
    description="生成 Mermaid 语法的思维导图/脑图结构。当用户要求总结结构、生成脑图时使用。",
    params_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "脑图中心主题词"},
            "markdown_list": {"type": "string", "description": "使用空格缩进的 markdown 列表结构，例如 '\\n    分支1\\n      子分支\\n    分支2'"}
        },
        "required": ["topic", "markdown_list"]
    }
)
