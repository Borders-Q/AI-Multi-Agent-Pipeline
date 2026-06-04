import asyncio
import os
from agent.loop import AgentLoop
from agent.memory import MemorySystem
from agent.context import ContextBuilder

async def main():
    print("===========================================")
    print("        Ai Multi Agent - 主控控制台")
    print("        (基于时间换空间的架构理念)")
    print("===========================================")
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    memory = MemorySystem(workspace_dir)
    context = ContextBuilder(workspace_dir)
    loop = AgentLoop(memory, context)
    
    print("\nAi Multi Agent 系统已就绪。请输入您的指令 (输入 'exit' 退出):")
    
    while True:
        try:
            user_input = input("\n用户 > ")
            if user_input.strip().lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
                
            await loop.run_turn(user_input)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"系统遇到异常: {e}")

if __name__ == "__main__":
    asyncio.run(main())
