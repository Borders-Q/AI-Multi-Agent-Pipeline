def get_todo_tool():
    return {
        "type": "function",
        "function": {
            "name": "update_todos",
            "description": "Updates the frontend todo list for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tasks to show on the UI"
                    }
                },
                "required": ["todos"]
            }
        }
    }

def handle_update_todos(todos: list):
    # In a full implementation, this could send a websocket message to the frontend,
    # or write to a memory file that the frontend polls.
    # For now, 天韬（SkyT） extracts todos directly from the <PLAN> tag via SSE.
    return "Todos updated successfully."
