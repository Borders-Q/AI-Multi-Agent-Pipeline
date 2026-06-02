import os
import json
from datetime import datetime

class TelemetryManager:
    def __init__(self, workspace_dir="."):
        self.memory_dir = os.path.join(workspace_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        self.tokens_jsonl_path = os.path.join(self.memory_dir, "tokens.jsonl")
        self.COMPACTION_THRESHOLD = 8000

    def log_tokens(self, input_tokens: int, output_tokens: int):
        with open(self.tokens_jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }) + "\n")
            
        self._check_compaction_trigger()

    def _check_compaction_trigger(self):
        """Check if total tokens since last compaction exceed the threshold."""
        if not os.path.exists(self.tokens_jsonl_path):
            return
            
        total = 0
        try:
            with open(self.tokens_jsonl_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Simplified check: just sum up the last N lines until we hit a "compact_event"
                # For a full implementation, you'd track tokens per session cleanly.
                for line in reversed(lines):
                    data = json.loads(line.strip())
                    if data.get("type") == "compact_event":
                        break
                    total += data.get("input_tokens", 0) + data.get("output_tokens", 0)
        except Exception:
            pass
            
        if total > self.COMPACTION_THRESHOLD:
            self._trigger_compaction()
            
    def _trigger_compaction(self):
        # We write a compact_event to tokens to reset the counter
        with open(self.tokens_jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "compact_event",
                "timestamp": datetime.now().isoformat()
            }) + "\n")
            
        # Trigger actual compactor (assuming compactor.py exposes a run() method)
        # In a real async environment, we'd trigger this asynchronously or via a queue.
        try:
            from agent.compactor import run_compactor
            run_compactor()
        except ImportError:
            print("Compactor not available yet.")

telemetry = TelemetryManager()
