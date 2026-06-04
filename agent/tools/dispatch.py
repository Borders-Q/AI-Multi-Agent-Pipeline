def get_dispatch_tool():
    return {
        "type": "function",
        "function": {
            "name": "dispatch_subagent",
            "description": "Dispatch a subagent to perform a specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "The identity or role of the subagent."
                    },
                    "task": {
                        "type": "string",
                        "description": "The task instructions for the subagent."
                    }
                },
                "required": ["role", "task"]
            }
        }
    }

def handle_dispatch(role: str, task: str):
    # This would instantiate a new AgentRunner for the subagent
    # For now, we return a mock success
    return f"Subagent '{role}' dispatched with task: {task}"
