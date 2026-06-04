import os
import subprocess
import sqlite3
import json
from agent.skills import tool_manager

def project_scaffolder(project_name: str, template_type: str, target_dir: str = ".") -> str:
    """
    Generate a basic project scaffold (Flask, FastAPI, or React).
    """
    base_path = os.path.join(target_dir, project_name)
    if os.path.exists(base_path):
        return f"Error: Directory {base_path} already exists."
        
    try:
        os.makedirs(base_path)
        
        if template_type.lower() == "flask":
            with open(os.path.join(base_path, "app.py"), "w") as f:
                f.write("from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef hello():\n    return 'Hello, World!'\n\nif __name__ == '__main__':\n    app.run(debug=True)\n")
            with open(os.path.join(base_path, "requirements.txt"), "w") as f:
                f.write("Flask==3.0.0\n")
            return f"Flask project '{project_name}' scaffolded successfully at {base_path}."
            
        elif template_type.lower() == "fastapi":
            with open(os.path.join(base_path, "main.py"), "w") as f:
                f.write("from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'Hello': 'World'}\n")
            with open(os.path.join(base_path, "requirements.txt"), "w") as f:
                f.write("fastapi\nuvicorn\n")
            return f"FastAPI project '{project_name}' scaffolded successfully at {base_path}."
            
        else:
            return f"Template type '{template_type}' is not supported yet. Try 'flask' or 'fastapi'."
            
    except Exception as e:
        return f"Error scaffolding project: {str(e)}"

def git_operator(repo_path: str, command: str) -> str:
    """
    Execute basic git commands in a repository.
    Allowed commands: status, log, diff, branch
    """
    if not os.path.exists(repo_path) or not os.path.isdir(os.path.join(repo_path, ".git")):
        return f"Error: '{repo_path}' is not a valid git repository."
        
    allowed_commands = ["status", "log", "diff", "branch"]
    cmd_parts = command.split()
    
    if not cmd_parts or cmd_parts[0] not in allowed_commands:
        return f"Error: Command '{command}' not allowed. Allowed commands: {', '.join(allowed_commands)}"
        
    try:
        full_command = ["git"] + cmd_parts
        result = subprocess.run(full_command, cwd=repo_path, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout or "Command executed successfully with no output."
        else:
            return f"Git error:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out."
    except Exception as e:
        return f"Error executing git command: {str(e)}"

def database_query(db_path: str, query: str) -> str:
    """
    Execute a read-only SQL query against an SQLite database and return JSON results.
    """
    if not os.path.exists(db_path):
        return f"Error: Database file {db_path} does not exist."
        
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        
        return json.dumps(results, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Database error: {str(e)}"

tool_manager.register_tool(
    func=project_scaffolder,
    name="project_scaffolder",
    description="一键生成基础项目脚手架（如 Flask, FastAPI）。",
    params_schema={
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "项目名称"},
            "template_type": {"type": "string", "description": "模板类型 (flask, fastapi)", "enum": ["flask", "fastapi"]},
            "target_dir": {"type": "string", "description": "目标目录", "default": "."}
        },
        "required": ["project_name", "template_type"]
    }
)

tool_manager.register_tool(
    func=git_operator,
    name="git_operator",
    description="执行基础 Git 命令（status, log, diff, branch）。",
    params_schema={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Git 仓库路径"},
            "command": {"type": "string", "description": "要执行的 Git 命令（如 'status', 'diff HEAD~1'）"}
        },
        "required": ["repo_path", "command"]
    }
)

tool_manager.register_tool(
    func=database_query,
    name="database_query",
    description="直接连接 SQLite 数据库并执行只读 SELECT 查询，返回 JSON 结果。",
    params_schema={
        "type": "object",
        "properties": {
            "db_path": {"type": "string", "description": "SQLite 数据库文件路径"},
            "query": {"type": "string", "description": "SELECT 查询语句"}
        },
        "required": ["db_path", "query"]
    }
)
