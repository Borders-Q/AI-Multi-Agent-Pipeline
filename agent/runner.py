import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from agent.llm_client import llm
from agent.tools.fs_tools import FS_TOOLS_SCHEMA, write_file, read_file, run_command

# Simplified placeholder for actual tool schema matching OpenAI format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "dispatch_subagent",
            "description": "派遣一个特定身份的子代理去执行独立任务。支持并发。",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "enum": ["RouterAgent", "PlannerAgent", "ResearcherAgent", "ReporterAgent", "DeveloperAgent"]},
                    "task": {"type": "string", "description": "要执行的具体任务"}
                },
                "required": ["agent_type", "task"]
            }
        }
    }
] + FS_TOOLS_SCHEMA

class AgentRunner:
    def __init__(self, memory, log_callback=None):
        self.memory = memory
        self.log_callback = log_callback
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    async def emit_log(self, msg: str):
        print(msg)
        if self.log_callback:
            await self.log_callback(msg)

    async def run(self, sys_prompt: str):
        # 组装消息
        messages = [{"role": "system", "content": sys_prompt}] + self.memory.get_working_memory()
        
        await self.emit_log("> 系统思考中...")
        response = await llm.chat_completion(messages, tools=TOOLS)
        msg = response.choices[0].message
        
        self.memory.append_message("assistant", msg.content, msg.tool_calls)
        
        if msg.content:
            await self.emit_log(f"> 系统回复已生成。")
            
        if msg.tool_calls:
            await self.emit_log(f"> [调度] 系统启动工具调用: {len(msg.tool_calls)} 个...")
            # 并发执行工具
            tasks = []
            for tool_call in msg.tool_calls:
                await self.emit_log(f"  - 调度子代理: {tool_call.function.name}")
                tasks.append(self.execute_tool(tool_call))
                
            results = await asyncio.gather(*tasks)
            
            # 回填结果到 memory
            for tool_call, result in zip(msg.tool_calls, results):
                self.memory.append_message("tool", result, tool_call_id=tool_call.id, name=tool_call.function.name)
                await self.emit_log(f"  - [工具返回] {tool_call.function.name} 汇报完毕。")
                
            # 工具执行完后，再让系统总结一次
            await self.run(sys_prompt)
            
    async def execute_tool(self, tool_call):
        # 运行在独立线程或协程中
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        if func_name == "dispatch_subagent":
            return await self.dispatch_subagent(args["agent_type"], args["task"])
        elif func_name == "write_file":
            await self.emit_log(f"> [文件系统] 正在写入文件: {args.get('path')}")
            return write_file(args.get("path", ""), args.get("content", ""), args.get("workspace"))
        elif func_name == "read_file":
            await self.emit_log(f"> [文件系统] 正在读取文件: {args.get('path')}")
            return read_file(args.get("path", ""), args.get("workspace"))
        elif func_name == "run_command":
            await self.emit_log(f"> [终端执行] 正在执行命令: {args.get('command')}")
            return run_command(args.get("command", ""), args.get("cwd"), args.get("workspace"))
        elif func_name == "import_local_skill":
            from agent.tools.fs_tools import import_local_skill
            await self.emit_log(f"> [技能扩展] 正在动态加载本地技能: {args.get('path')}")
            return import_local_skill(args.get("path", ""))
        elif func_name == "ask_user_for_directory":
            from agent.tools.fs_tools import ask_user_for_directory
            await self.emit_log(f"> [交互] 正在弹窗等待用户选择文件夹...")
            return ask_user_for_directory()
            
        return "Unknown tool"
        
    async def dispatch_subagent(self, agent_type, task):
        # 这是一个模拟的子代理派遣过程，实际应该是一个新的 AgentRunner 实例
        await self.emit_log(f"> [小队] 正在唤醒子代理 {agent_type}，委派任务: {task[:20]}...")
        await asyncio.sleep(2) # 模拟工作时间
        return f"{agent_type} 回报: 任务 [{task}] 已办妥。"
