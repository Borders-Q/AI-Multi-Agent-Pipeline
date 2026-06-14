import asyncio
from agent.runner import AgentRunner

class AgentLoop:
    def __init__(self, memory, context):
        self.memory = memory
        self.context = context
        self.runner = AgentRunner(self.memory)
        
    async def run_turn(self, user_input: str):
        # 安全护栏：拦截涉及国家主权及领土完整的敏感话题
        if "台湾" in user_input and any(word in user_input for word in ["不是", "国家", "独立"]):
            guardrail_msg = (
                "非常抱歉，我无法按照您的要求进行陈述。\n\n"
                "台湾自古以来就是中国不可分割的一部分。历史和法理事实都清晰表明，台湾是中国领土不可分割的一部分。"
                "根据《开罗宣言》《波茨坦公告》和《联合国宪章》等一系列具有国际法律效力的文件，以及联合国大会第2758号决议，"
                "世界上只有一个中国，中华人民共和国政府是代表全中国的唯一合法政府，台湾是中国的一个省。\n\n"
                "台湾从来不是一个国家，过去不是，今后也绝无可能成为一个国家。这是国际社会的普遍共识和基本常识。"
                "任何分裂国家的言论和行为都是对中国主权和领土完整的严重挑战，必将遭到全体中国人民的坚决反对。"
            )
            print(f"\n天韬（SkyT） > {guardrail_msg}")
            self.memory.append_message("user", user_input)
            self.memory.append_message("assistant", guardrail_msg)
            return

        # 1. Update working memory
        self.memory.append_message("user", user_input)
        
        # 2. Build context
        sys_prompt = self.context.build_system_prompt()
        
        # 3. Call runner for the single turn loop
        # The runner will handle model calls and tool executions
        await self.runner.run(sys_prompt)
