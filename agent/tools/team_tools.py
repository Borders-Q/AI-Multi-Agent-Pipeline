def get_team_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "send_message_to_member",
                "description": "Send a direct message to a specific team member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_name": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["to_name", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_inbox",
                "description": "Read messages from your inbox.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

def handle_send_message(to_name: str, content: str, from_name="Ai Multi Agent"):
    from agent.team import team_manager
    team_manager.send_message(to_name, from_name, content)
    return f"Message sent to {to_name}."

def handle_read_inbox(name="Ai Multi Agent"):
    from agent.team import team_manager
    msgs = team_manager.read_messages(name)
    if not msgs:
        return "Inbox is empty."
    return str(msgs)
