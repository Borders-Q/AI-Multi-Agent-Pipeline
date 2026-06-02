import json
from agent.skills import tool_manager
import db

def generate_report(title: str, markdown_content: str) -> str:
    """
    Generates a structured Markdown report and saves it to the system's database.
    This should be used when the user asks for a comprehensive analysis, summary, or report.
    """
    try:
        db.save_report(title, markdown_content)
        return f"Report '{title}' successfully generated and saved to the database. The user can view it in the Reports center."
    except Exception as e:
        return f"Failed to save report: {str(e)}"

# Register the tool
tool_manager.register_tool(
    generate_report,
    name="generate_report",
    description="Generates a structured Markdown report and saves it to the system's database.",
    params_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the report (e.g., 'System Performance Analysis')"
            },
            "markdown_content": {
                "type": "string",
                "description": "The full content of the report formatted in Markdown."
            }
        },
        "required": ["title", "markdown_content"]
    }
)
