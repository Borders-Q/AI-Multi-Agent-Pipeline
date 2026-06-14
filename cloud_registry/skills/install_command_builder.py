def install_command_builder(python_packages: str = "", npm_packages: str = ""):
    py = " ".join([p.strip() for p in python_packages.replace(",", " ").split() if p.strip()])
    npm = " ".join([p.strip() for p in npm_packages.replace(",", " ").split() if p.strip()])
    lines = ["# 国内网络安装命令"]
    if py:
        lines.append("python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple " + py)
    if npm:
        lines.append("npm install --registry https://mirrors.tuna.tsinghua.edu.cn/npm/ " + npm)
    if not py and not npm:
        lines.append("未提供依赖名称。")
    return "\n".join(lines)

SCHEMA = {
    "name": "install_command_builder",
    "description": "生成清华源 pip/npm 安装命令",
    "parameters": {
        "type": "object",
        "properties": {
            "python_packages": {"type": "string", "description": "Python 包名，空格或逗号分隔", "default": ""},
            "npm_packages": {"type": "string", "description": "npm 包名，空格或逗号分隔", "default": ""}
        }
    }
}
