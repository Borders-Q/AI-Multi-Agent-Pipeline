import os
import json
from datetime import datetime

class MemorySystem:
    def __init__(self, workspace_dir="."):
        # 动态相对路径解析：定位到当前工程文件夹的上一级（同级记忆库）
        abs_workspace = os.path.abspath(workspace_dir)
        parent_dir = os.path.dirname(abs_workspace)
        dynamic_memory_dir = os.path.join(parent_dir, "记忆")
        
        try:
            os.makedirs(dynamic_memory_dir, exist_ok=True)
            self.memory_dir = dynamic_memory_dir
            print(f"> [MemorySubsystem] Memory path successfully set to dynamic parent directory: {self.memory_dir}")
        except Exception as e:
            self.memory_dir = os.path.join(abs_workspace, "memory")
            os.makedirs(self.memory_dir, exist_ok=True)
            print(f"> [MemorySubsystem] Failed to use {dynamic_memory_dir}, fallback to workspace memory: {e}")
            
        self.memory_md_path = os.path.join(self.memory_dir, "MEMORY.md")
        self.history_jsonl_path = os.path.join(self.memory_dir, "history.jsonl")
        self.tokens_jsonl_path = os.path.join(self.memory_dir, "tokens.jsonl")
        
        # Initialize memory files if they don't exist
        if not os.path.exists(self.memory_md_path):
            soul_content = ""
            user_content = ""
            soul_path = os.path.join(workspace_dir, "templates", "SOUL.md")
            user_path = os.path.join(workspace_dir, "templates", "USER.md")
            
            if os.path.exists(soul_path):
                try:
                    with open(soul_path, "r", encoding="utf-8") as f:
                        soul_content = f.read().strip()
                except Exception as e:
                    print(f"Error reading SOUL template: {e}")
            if os.path.exists(user_path):
                try:
                    with open(user_path, "r", encoding="utf-8") as f:
                        user_content = f.read().strip()
                except Exception as e:
                    print(f"Error reading USER template: {e}")
                    
            try:
                with open(self.memory_md_path, "w", encoding="utf-8") as f:
                    f.write("# Long-Term Memory (长期记忆)\n\n")
                    if soul_content:
                        f.write("## 智能体核心设定 (Agent Core Profile)\n")
                        f.write(soul_content + "\n\n")
                    if user_content:
                        f.write("## 用户偏好档案 (User Preferences)\n")
                        f.write(user_content + "\n\n")
                    f.write("## 对话记忆日志 (Episodic Logs)\nNo memories yet.\n")
            except Exception as e:
                print(f"Error initializing MEMORY.md: {e}")
                
        # Working memory
        self.history = []
        self._load_unarchived_history()

    def _load_unarchived_history(self):
        """Loads unarchived history from previous session if it didn't reach compaction threshold."""
        if not os.path.exists(self.history_jsonl_path):
            return
            
        unarchived = []
        try:
            with open(self.history_jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get("type") == "compact_event":
                        unarchived = [] # Reset on compaction
                    else:
                        unarchived.append(data)
            self.history = unarchived
        except Exception as e:
            print(f"Error loading history: {e}")

    def append_message(self, role, content, tool_calls=None, tool_call_id=None, name=None):
        msg = {"role": role, "content": content}
        if tool_calls:
            serialized_calls = []
            for tc in tool_calls:
                if hasattr(tc, 'model_dump'):
                    serialized_calls.append(tc.model_dump())
                elif hasattr(tc, 'dict'):
                    serialized_calls.append(tc.dict())
                elif type(tc) is dict:
                    serialized_calls.append(tc)
                else:
                    serialized_calls.append({
                        "id": getattr(tc, "id", ""),
                        "type": getattr(tc, "type", "function"),
                        "function": {
                            "name": getattr(tc.function, "name", "") if hasattr(tc, "function") else "",
                            "arguments": getattr(tc.function, "arguments", "") if hasattr(tc, "function") else ""
                        }
                    })
            msg["tool_calls"] = serialized_calls
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if name:
            msg["name"] = name
            
        self.history.append(msg)
        
        # Append to jsonl
        with open(self.history_jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    def get_working_memory(self):
        return self.history

    def get_long_term_memory_content(self):
        try:
            with open(self.memory_md_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""

    def save_episodic_memory(self, content):
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.memory_dir, f"{date_str}.md")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n## Entry at {datetime.now().strftime('%H:%M:%S')}\n")
            f.write(content + "\n")

    def update_long_term_memory(self, content):
        with open(self.memory_md_path, "w", encoding="utf-8") as f:
            f.write(content)

    def append_long_term_memory(self, title, content):
        try:
            with open(self.memory_md_path, "a", encoding="utf-8") as f:
                f.write(f"\n### 📌 自动蒸馏经验: {title}\n")
                f.write(content + "\n")
        except Exception as e:
            print(f"Error appending to MEMORY.md: {e}")
