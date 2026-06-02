import asyncio
import json
import db
from agent.workflow import AgentWorkflowEngine
from agent.llm_client import llm

class MockQueue:
    async def put(self, item):
        print("QUEUE:", str(item).encode("gbk", "ignore").decode("gbk"))

async def main():
    keys = db.get_all_api_keys()
    if keys:
        for item in keys:
            provider = item["provider"]
            print(f"Adding key for {provider}")
            llm.add_key(item["api_key"])
            llm.set_active_provider(provider)
            break
            
    engine = AgentWorkflowEngine(provider=llm.active_provider)
    enabled = ["data_visualizer", "web_search"]
    
    print("Executing DAG...")
    result = await engine.execute_dag("帮我画一个华为公司各季度营收的柱状图", MockQueue(), "Cloud API", enabled)
    print("FINAL RESULT:", result)

if __name__ == "__main__":
    asyncio.run(main())
