from agent.llm_client import llm
from agent.memory import MemorySystem

class Compactor:
    def __init__(self, memory: MemorySystem, threshold=140000):
        self.memory = memory
        self.threshold = threshold
        
    async def check_and_compact(self, input_tokens: int):
        if input_tokens >= self.threshold:
            print(f"[Compactor] Threshold reached ({input_tokens} >= {self.threshold}). Compacting history...")
            await self.compact()
            
    async def compact(self):
        # Keep last 10 messages
        history = self.memory.get_working_memory()
        if len(history) <= 10:
            return
            
        to_compact = history[:-10]
        self.memory.history = history[-10:] # Keep last 10
        
        # Prepare compaction prompt
        # In a real setup, we'd load this from templates/agent/compact_prompt.md
        prompt = "Summarize the following conversation into key episodic memory events and an updated long-term memory state. Return JSON format with 'episodic_summary' and 'updated_long_term_memory'.\n\n"
        for msg in to_compact:
            prompt += f"{msg.get('role', 'unknown')}: {msg.get('content', '')}\n"
            
        current_ltm = self.memory.get_long_term_memory_content()
        prompt += f"\n\nCurrent Long Term Memory:\n{current_ltm}"
        
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await llm.chat_completion(messages, response_format={"type": "json_object"})
            result_str = response.choices[0].message.content
            import json
            result = json.loads(result_str)
            
            if "episodic_summary" in result:
                self.memory.save_episodic_memory(result["episodic_summary"])
            if "updated_long_term_memory" in result:
                self.memory.update_long_term_memory(result["updated_long_term_memory"])
                
            self.memory.log_compact_event()
            print("[Compactor] Compaction successful.")
        except Exception as e:
            print(f"[Compactor] Error during compaction: {e}")
