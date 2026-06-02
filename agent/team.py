import os
import json

class TeamManager:
    def __init__(self, workspace_dir="."):
        self.team_dir = os.path.join(workspace_dir, ".team")
        self.inbox_dir = os.path.join(self.team_dir, "inbox")
        os.makedirs(self.inbox_dir, exist_ok=True)
        self.config_path = os.path.join(self.team_dir, "config.json")
        
        if not os.path.exists(self.config_path):
            self._save_config({"members": []})

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def _save_config(self, data):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def register_member(self, name: str, role: str):
        config = self._load_config()
        # Update or add member
        for m in config["members"]:
            if m["name"] == name:
                m["role"] = role
                m["status"] = "idle"
                self._save_config(config)
                return
                
        config["members"].append({"name": name, "role": role, "status": "idle"})
        self._save_config(config)

    def set_status(self, name: str, status: str):
        config = self._load_config()
        for m in config["members"]:
            if m["name"] == name:
                m["status"] = status
                self._save_config(config)
                return

    def get_members(self):
        return self._load_config()["members"]

    def send_message(self, to_name: str, from_name: str, content: str):
        inbox_file = os.path.join(self.inbox_dir, f"{to_name}.jsonl")
        msg = {"from": from_name, "content": content}
        with open(inbox_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    def read_messages(self, name: str):
        inbox_file = os.path.join(self.inbox_dir, f"{name}.jsonl")
        if not os.path.exists(inbox_file):
            return []
            
        msgs = []
        with open(inbox_file, "r", encoding="utf-8") as f:
            for line in f:
                msgs.append(json.loads(line.strip()))
                
        # Clear inbox after reading
        os.remove(inbox_file)
        return msgs

team_manager = TeamManager()
