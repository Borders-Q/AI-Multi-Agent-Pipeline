import os
import re
import subprocess
import secrets
import logging
from pathlib import Path

from skyt_platform.config import settings
from skyt_platform.workspace_policy import WorkspaceViolation, canonical_root, resolve_inside

logger = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
PROTECTED_FILENAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
DANGEROUS_COMMAND_PATTERNS = [
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\s]*[fd]",
    r"\bformat\s+[a-z]:",
    r"\bdiskpart\b",
    r"\bRemove-Item\b.*\b-Recurse\b",
    r"\brm\s+-[^\s]*r[^\s]*f\b",
    r"\brmdir\s+/s\b",
    r"\bdel\s+.*\s+/s\b",
    r"\btaskkill\b.*\b/f\b",
    r"\bnpm\s+publish\b",
    r"\btwine\s+upload\b",
    r"\bgit\s+push\b.*\b--force\b",
    r"\bnpm\s+install\s+-g\b",
    r"\bpip\s+install\b.*\s+--user\b",
]

def _approval_required(reason: str, payload: str) -> str:
    approval_id = f"APR_{secrets.token_urlsafe(10)}"
    logger.warning("Approval required id=%s reason=%s", approval_id, reason)
    return (
        "[APPROVAL_REQUIRED]\n"
        f"Approval-ID: {approval_id}\n"
        f"Reason: {reason}\n"
        f"Payload: {payload}\n"
        "天韬（SkyT） stopped before executing this high-risk automatic action. Ask the user to confirm explicitly."
    )

def _is_protected_path(path: str) -> bool:
    normalized = os.path.normpath(path)
    name = os.path.basename(normalized).lower()
    if name in PROTECTED_FILENAMES:
        return True
    return any(part.lower() in {".ssh", ".gnupg"} for part in normalized.split(os.sep))

def _is_dangerous_command(command: str) -> str | None:
    lowered = command.lower()
    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return pattern
    return None

def _resolve_path(path_str: str, workspace: str = None) -> str:
    """Resolve a path and prevent traversal outside the active workspace."""
    root = workspace or WORKSPACE_DIR
    if not os.path.exists(root):
        os.makedirs(root, exist_ok=True)
    root_path = canonical_root(root)
    raw = str(path_str or ".")
    if os.path.isabs(raw) and not settings.allow_absolute_paths:
        target = resolve_inside(root_path, raw)
    else:
        target = resolve_inside(root_path, raw)
    return os.fspath(target)

def write_file(path: str, content: str, workspace: str = None) -> str:
    """Write content to a file. Supports absolute paths or relative to workspace."""
    try:
        abs_path = _resolve_path(path, workspace)
        if _is_protected_path(abs_path):
            return _approval_required("protected file write", abs_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"File '{path}' successfully written to {abs_path}."
    except WorkspaceViolation as e:
        return _approval_required("workspace boundary violation", str(e))
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"

def read_file(path: str, workspace: str = None) -> str:
    """Read content from a file. Supports absolute paths or relative to workspace."""
    try:
        abs_path = _resolve_path(path, workspace)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except WorkspaceViolation as e:
        return _approval_required("workspace boundary violation", str(e))
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

def run_command(command: str, cwd: str = None, workspace: str = None) -> str:
    """Run a shell command in the specified directory or workspace."""
    try:
        dangerous_match = _is_dangerous_command(command)
        if dangerous_match:
            return _approval_required(f"dangerous command matched `{dangerous_match}`", command)
        target_cwd = _resolve_path(cwd or ".", workspace)
        os.makedirs(target_cwd, exist_ok=True)
        result = subprocess.run(
            command,
            cwd=target_cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30 # Prevent hanging forever
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        max_output = 256 * 1024
        if len(output) > max_output:
            output = output[:max_output] + "\n[OUTPUT_TRUNCATED]"
            
        if not output.strip():
            output = "[Command executed successfully with no output]"
            
        return output
    except WorkspaceViolation as e:
        return _approval_required("workspace boundary violation", str(e))
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command '{command}': {str(e)}"

def start_background_service(command: str, cwd: str = None, workspace: str = None) -> str:
    """Start a command in the background (e.g., a web server) and return its PID."""
    try:
        import time
        dangerous_match = _is_dangerous_command(command)
        if dangerous_match:
            return _approval_required(f"dangerous command matched `{dangerous_match}`", command)
        target_cwd = _resolve_path(cwd or ".", workspace)
        os.makedirs(target_cwd, exist_ok=True)
        
        # We use subprocess.Popen to run in background
        process = subprocess.Popen(
            command,
            cwd=target_cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait shortly to see if it crashes immediately
        time.sleep(2)
        if process.poll() is not None:
            # It exited already, likely an error
            _, stderr = process.communicate()
            return f"Error: Background service crashed immediately with exit code {process.returncode}.\nStderr: {stderr}"
            
        return f"Background service started successfully with PID {process.pid}. Command: '{command}'. Please provide the local URL to the user in your final response."
    except WorkspaceViolation as e:
        return _approval_required("workspace boundary violation", str(e))
    except Exception as e:
        return f"Error starting background service '{command}': {str(e)}"

def ask_user_for_directory() -> str:
    """Pop up a native Windows folder selection dialog for the user to pick a folder."""
    try:
        script = (
            "import tkinter as tk\n"
            "from tkinter import filedialog\n"
            "root = tk.Tk()\n"
            "root.withdraw()\n"
            "root.attributes('-topmost', True)\n"
            "path = filedialog.askdirectory(title='请选择一个文件夹用于保存AI生成的文件')\n"
            "print(path)\n"
        )
        # Run in a separate process to avoid tkinter threading issues with FastAPI
        result = subprocess.run(["python", "-c", script], capture_output=True, text=True, timeout=300)
        path = result.stdout.strip()
        if path:
            return path
        else:
            return "Error: User cancelled the folder selection."
    except subprocess.TimeoutExpired:
        return "Error: Folder selection timed out."
    except Exception as e:
        return f"Error opening folder selection dialog: {str(e)}"

def import_local_skill(path: str) -> str:
    """Read a python file and import it into 天韬（SkyT） as a new skill dynamically."""
    try:
        return _approval_required("dynamic Python skill import", path)
        abs_path = _resolve_path(path)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
            
        with open(abs_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        from agent.skills import tool_manager
        namespace = {}
        exec(code, namespace)
        schema = namespace.get("SCHEMA")
        if not schema:
            return f"Error: Missing SCHEMA definition in {path}"
        func_name = schema.get("name")
        func = namespace.get(func_name)
        if not func:
            return f"Error: Function {func_name} not found in {path}"
            
        tool_manager.register_tool(func, name=schema["name"], description=schema["description"], params_schema=schema["parameters"])
        return f"Successfully imported skill '{func_name}' from {path}. You can now call it directly as a tool!"
    except Exception as e:
        return f"Failed to import skill from {path}: {str(e)}"

FS_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file. Use this to generate code or scripts. If the user doesn't specify a folder, you can ask them where to save it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file. If absolute, it saves directly to that location. If relative, it saves in the default workspace."
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete text content to write into the file."
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Optional canonical project workspace. Relative paths are resolved inside it."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file to read."
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Optional canonical project workspace."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command (e.g., 'npm init -y', 'python main.py'). Max timeout is 30s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional. The working directory to execute the command in. If absolute, it uses that directory. If relative, it's relative to the workspace."
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Optional canonical project workspace."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_background_service",
            "description": "Start a long-running process in the background (e.g., a web server, API, or GUI app) and return its PID. It will not block the agent's execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to start the service."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional. The working directory."
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Optional canonical project workspace."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "import_local_skill",
            "description": "Dynamically load a python file and import it into 天韬（SkyT） as a new skill (Tool). The python file must contain a function and a SCHEMA dict.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute or relative path to the python file."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user_for_directory",
            "description": "CRITICAL TOOL: Pop up a native visual Windows folder selection dialog to let the user select a directory. MANDATORY FIRST STEP: You must call this tool FIRST before generating any files or using write_file to ask the user where to save the files. Returns the absolute path of the chosen directory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Auto-register with tool_manager if available
try:
    from agent.skills import tool_manager
    for schema in FS_TOOLS_SCHEMA:
        func_name = schema["function"]["name"]
        func_obj = globals().get(func_name)
        if func_obj:
            tool_manager.register_tool(
                func_obj,
                name=func_name,
                description=schema["function"]["description"],
                params_schema=schema["function"]["parameters"]
            )
except ImportError:
    pass
