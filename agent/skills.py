import json
import inspect

class ToolManager:
    def __init__(self):
        self.tools = {}
        
    def register_tool(self, func, name=None, description=None, params_schema=None):
        tool_name = name or func.__name__
        self.tools[tool_name] = {
            "func": func,
            "name": tool_name,
            "description": description or func.__doc__ or "No description",
            "parameters": params_schema or {"type": "object", "properties": {}}
        }
        
    def get_openai_tools(self):
        """返回适用于 OpenAI/Anthropic API 的 tools 列表"""
        tools_list = []
        for name, data in self.tools.items():
            tools_list.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": data["description"],
                    "parameters": data["parameters"]
                }
            })
        return tools_list
        
    async def execute_tool(self, tool_name, kwargs_dict):
        """执行具体的 Tool 并返回字符串结果"""
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found."
            
        try:
            func = self.tools[tool_name]["func"]
            if inspect.iscoroutinefunction(func):
                result = await func(**kwargs_dict)
            else:
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(**kwargs_dict))
                
            # Ensure return is string or json string
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            return f"Error executing '{tool_name}': {str(e)}"
            
# 全局单例
tool_manager = ToolManager()
