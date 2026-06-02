import os
import ast
from agent.skills import tool_manager

def code_analyzer(file_path: str) -> str:
    """
    静态分析 Python/JS 代码的圈复杂度、函数数量、行数统计。
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} does not exist."
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        total_lines = len(lines)
        empty_lines = len([line for line in lines if not line.strip()])
        
        # Simple analysis for Python
        if file_path.endswith('.py'):
            tree = ast.parse(content)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
            
            return (f"Code Analysis for {file_path}:\n"
                    f"- Total Lines: {total_lines}\n"
                    f"- Empty Lines: {empty_lines}\n"
                    f"- Classes: {len(classes)} {classes}\n"
                    f"- Functions: {len(functions)} {functions}\n"
                    f"- Imports: {len(imports)} {imports}")
        else:
            return (f"Code Analysis for {file_path}:\n"
                    f"- Total Lines: {total_lines}\n"
                    f"- Empty Lines: {empty_lines}\n"
                    f"- Note: AST parsing is only supported for Python files currently.")
    except Exception as e:
        return f"Error analyzing code: {str(e)}"

def file_tree_viewer(dir_path: str, max_depth: int = 3) -> str:
    """
    递归列出项目目录树结构。
    """
    if not os.path.exists(dir_path):
        return f"Error: Directory {dir_path} does not exist."
    if not os.path.isdir(dir_path):
        return f"Error: {dir_path} is not a directory."
        
    tree = []
    
    def walk_dir(current_path, current_depth, prefix=""):
        if current_depth > max_depth:
            return
            
        try:
            items = os.listdir(current_path)
            # Filter out hidden files and common ignore directories
            items = [item for item in items if not item.startswith('.') and item not in ['node_modules', '__pycache__', 'venv', 'env']]
            items.sort()
            
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                item_path = os.path.join(current_path, item)
                
                connector = "└── " if is_last else "├── "
                tree.append(f"{prefix}{connector}{item}")
                
                if os.path.isdir(item_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk_dir(item_path, current_depth + 1, new_prefix)
        except PermissionError:
            tree.append(f"{prefix}└── [Permission Denied]")
            
    tree.append(os.path.basename(os.path.abspath(dir_path)) or dir_path)
    walk_dir(dir_path, 1)
    
    return "\n".join(tree)

tool_manager.register_tool(
    func=code_analyzer,
    name="code_analyzer",
    description="静态分析 Python/JS 代码的圈复杂度、函数数量、行数统计。用于深入理解本地代码结构。",
    params_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要分析的代码文件绝对路径"}
        },
        "required": ["file_path"]
    }
)

tool_manager.register_tool(
    func=file_tree_viewer,
    name="file_tree_viewer",
    description="递归列出项目目录树结构，用于快速了解项目宏观架构（排除node_modules等）。",
    params_schema={
        "type": "object",
        "properties": {
            "dir_path": {"type": "string", "description": "要查看的目录绝对路径"},
            "max_depth": {"type": "integer", "description": "遍历的最大深度", "default": 3}
        },
        "required": ["dir_path"]
    }
)
