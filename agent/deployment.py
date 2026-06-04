import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

from agent.tools.fs_tools import start_background_service


IGNORED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
}


def _rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _run(command: list[str], cwd: Path, timeout: int = 120) -> dict:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": " ".join(command),
            "cwd": str(cwd),
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
            "ok": result.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "cwd": str(cwd),
            "returncode": None,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": "Command timed out.",
            "ok": False,
        }
    except Exception as exc:
        return {
            "command": " ".join(command),
            "cwd": str(cwd),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


def _find_free_port(start_port: int, host: str = "127.0.0.1", limit: int = 120) -> int:
    port = max(1024, int(start_port or 5000))
    for candidate in range(port, port + limit):
        if not _port_open(candidate, host):
            return candidate
    raise RuntimeError(f"No free local port found from {port} to {port + limit - 1}.")


def _write_flask_preview_launcher(app_dir: Path, app_entry: Path, port: int) -> Path:
    launcher = app_dir / ".ai_multi_agent_preview.py"
    launcher.write_text(
        "\n".join([
            "import importlib.util",
            "import sys",
            "from pathlib import Path",
            "",
            f"entry = Path(r'''{str(app_entry)}''')",
            "sys.path.insert(0, str(entry.parent))",
            "spec = importlib.util.spec_from_file_location('ai_multi_agent_preview_app', entry)",
            "module = importlib.util.module_from_spec(spec)",
            "assert spec and spec.loader",
            "spec.loader.exec_module(module)",
            "init_db = getattr(module, 'init_db', None)",
            "if callable(init_db):",
            "    init_db()",
            "app = getattr(module, 'app', None) or getattr(module, 'application', None)",
            "if app is None:",
            "    raise RuntimeError('Flask app object named app/application was not found.')",
            f"app.run(host='127.0.0.1', port={int(port)}, debug=False, use_reloader=False)",
            "",
        ]),
        encoding="utf-8",
    )
    return launcher


def _scan_workspace(workspace: Path) -> dict:
    files = []
    flask_candidates = []
    package_candidates = []
    static_candidates = []

    for root, dirs, names in os.walk(workspace):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        root_path = Path(root)
        rel_root = root_path.relative_to(workspace).as_posix()
        if rel_root == ".":
            rel_root = ""

        for name in names:
            file_path = root_path / name
            rel_file = _rel(file_path, workspace)
            files.append(rel_file)

        if "app.py" in names:
            score = 10
            if "requirements.txt" in names:
                score += 2
            if "templates" in dirs or (root_path / "templates").is_dir():
                score += 2
            if "static" in dirs or (root_path / "static").is_dir():
                score += 1
            flask_candidates.append({"dir": root_path, "entry": root_path / "app.py", "score": score})

        if "package.json" in names:
            package_candidates.append({"dir": root_path, "entry": root_path / "package.json", "score": 10 if root_path.name.lower() == "frontend" else 6})

        if "index.html" in names and "package.json" not in names:
            static_candidates.append({"dir": root_path, "entry": root_path / "index.html", "score": 4})

    flask_candidates.sort(key=lambda item: item["score"], reverse=True)
    package_candidates.sort(key=lambda item: item["score"], reverse=True)
    static_candidates.sort(key=lambda item: item["score"], reverse=True)

    return {
        "files_count": len(files),
        "sample_files": files[:120],
        "flask_candidates": [
            {"dir": _rel(item["dir"], workspace) if item["dir"] != workspace else ".", "entry": _rel(item["entry"], workspace)}
            for item in flask_candidates
        ],
        "package_candidates": [
            {"dir": _rel(item["dir"], workspace) if item["dir"] != workspace else ".", "entry": _rel(item["entry"], workspace)}
            for item in package_candidates
        ],
        "static_candidates": [
            {"dir": _rel(item["dir"], workspace) if item["dir"] != workspace else ".", "entry": _rel(item["entry"], workspace)}
            for item in static_candidates
        ],
        "_flask": flask_candidates,
        "_packages": package_candidates,
        "_static": static_candidates,
    }


def _parse_flask_port(app_py: Path) -> int:
    try:
        text = app_py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 5000
    match = re.search(r"\bport\s*=\s*(\d{2,5})", text)
    if match:
        return int(match.group(1))
    return 5000


def _parse_dev_port(package_json: Path) -> int:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
        joined = json.dumps(data.get("scripts", {}), ensure_ascii=False)
    except Exception:
        joined = ""
    match = re.search(r"--port\s+(\d{2,5})", joined)
    if match:
        return int(match.group(1))
    if "vite" in joined.lower():
        return 5173
    return 3000


def deploy_workspace_preview(workspace: str) -> dict:
    base = Path(workspace or "").expanduser().resolve()
    result = {
        "status": "skipped",
        "workspace": str(base),
        "browser_url": None,
        "steps": [],
        "scan": {},
        "started_services": [],
    }
    if not base.is_dir():
        result["reason"] = "workspace_not_found"
        return result

    scan = _scan_workspace(base)
    result["scan"] = {key: value for key, value in scan.items() if not key.startswith("_")}

    if scan["_flask"]:
        candidate = scan["_flask"][0]
        app_dir = candidate["dir"]
        app_entry = candidate["entry"]
        requirements = app_dir / "requirements.txt"
        requested_port = _parse_flask_port(app_entry)
        port_conflict = _port_open(requested_port)
        port = _find_free_port(requested_port + 1 if port_conflict else requested_port)
        result["runtime"] = "flask"
        result["entry"] = _rel(app_entry, base)
        result["requested_port"] = requested_port
        result["port"] = port
        result["port_conflict"] = port_conflict

        if requirements.exists():
            install = _run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                app_dir,
                timeout=180,
            )
            result["steps"].append({"name": "install_python_requirements", **install})

        compile_check = _run([sys.executable, "-m", "py_compile", str(app_entry)], app_dir, timeout=45)
        result["steps"].append({"name": "python_compile_check", **compile_check})
        if not compile_check["ok"]:
            result["status"] = "failed"
            result["reason"] = "python_compile_failed"
            return result

        url = f"http://127.0.0.1:{port}"
        launcher = _write_flask_preview_launcher(app_dir, app_entry, port)
        command = f'"{sys.executable}" "{launcher.name}"'
        start = start_background_service(command, str(app_dir))
        ok = not start.startswith("Error:")
        result["steps"].append({"name": "start_flask_service", "command": command, "cwd": str(app_dir), "ok": ok, "output": start[-4000:]})
        result["status"] = "success" if ok else "failed"
        result["browser_url"] = url if ok else None
        service_status = "started_on_alternate_port" if ok and port_conflict else ("started" if ok else "failed")
        result["started_services"].append({
            "kind": "flask",
            "url": url,
            "status": service_status,
            "requested_port": requested_port,
            "port": port,
            "port_conflict": port_conflict,
        })
        return result

    if scan["_packages"]:
        candidate = scan["_packages"][0]
        package_dir = candidate["dir"]
        package_json = candidate["entry"]
        requested_port = _parse_dev_port(package_json)
        port_conflict = _port_open(requested_port)
        port = _find_free_port(requested_port + 1 if port_conflict else requested_port)
        result["runtime"] = "node"
        result["entry"] = _rel(package_json, base)
        result["requested_port"] = requested_port
        result["port"] = port
        result["port_conflict"] = port_conflict

        if not (package_dir / "node_modules").exists():
            install = _run(["npm", "install", "--registry", "https://mirrors.tuna.tsinghua.edu.cn/npm/"], package_dir, timeout=240)
            result["steps"].append({"name": "npm_install", **install})
            if not install["ok"]:
                result["status"] = "failed"
                result["reason"] = "npm_install_failed"
                return result

        url = f"http://127.0.0.1:{port}"
        command = f"npm run dev -- --host 127.0.0.1 --port {port}"
        start = start_background_service(command, str(package_dir))
        ok = not start.startswith("Error:")
        result["steps"].append({"name": "start_node_dev_server", "command": command, "cwd": str(package_dir), "ok": ok, "output": start[-4000:]})
        result["status"] = "success" if ok else "failed"
        result["browser_url"] = url if ok else None
        service_status = "started_on_alternate_port" if ok and port_conflict else ("started" if ok else "failed")
        result["started_services"].append({
            "kind": "node",
            "url": url,
            "status": service_status,
            "requested_port": requested_port,
            "port": port,
            "port_conflict": port_conflict,
        })
        return result

    if scan["_static"]:
        candidate = scan["_static"][0]
        static_dir = candidate["dir"]
        port = 5500
        result["runtime"] = "static"
        result["entry"] = _rel(candidate["entry"], base)
        port = _find_free_port(port, limit=120)
        url = f"http://127.0.0.1:{port}"
        command = f'"{sys.executable}" -m http.server {port} --bind 127.0.0.1'
        start = start_background_service(command, str(static_dir))
        ok = not start.startswith("Error:")
        result["steps"].append({"name": "start_static_server", "command": command, "cwd": str(static_dir), "ok": ok, "output": start[-4000:]})
        result["status"] = "success" if ok else "failed"
        result["browser_url"] = url if ok else None
        result["started_services"].append({"kind": "static", "url": url, "status": "started" if ok else "failed"})
        return result

    result["reason"] = "no_runnable_entry_found"
    return result


def format_deployment_summary(result: dict) -> str:
    if not result:
        return ""
    status = result.get("status")
    if status == "success":
        lines = [
            "\n\n## 自动部署与右侧预览",
            f"- 工作区扫描文件数：{result.get('scan', {}).get('files_count', 0)}",
            f"- 运行入口：`{result.get('entry') or result.get('runtime') or 'unknown'}`",
        ]
        for service in result.get("started_services") or []:
            requested_port = service.get("requested_port")
            actual_port = service.get("port")
            port_note = ""
            if service.get("port_conflict") and requested_port and actual_port and requested_port != actual_port:
                port_note = f"（端口 {requested_port} 被占用，已自动使用 {actual_port}）"
            lines.append(f"- 服务：{service.get('kind')} / {service.get('status')} / {service.get('url')}{port_note}")
        if result.get("browser_url"):
            lines.append(f"- 右侧浏览器预览：{result['browser_url']}")
        return "\n".join(lines)
    if status == "failed":
        last_step = (result.get("steps") or [{}])[-1]
        return (
            "\n\n## 自动部署检查失败\n"
            f"- 原因：{result.get('reason') or 'unknown'}\n"
            f"- 最后步骤：{last_step.get('name') or last_step.get('command') or 'unknown'}\n"
            f"- 错误：`{(last_step.get('stderr') or last_step.get('output') or '')[:800]}`"
        )
    return "\n\n## 自动部署检查\n- 未发现可自动启动的 Web 入口。"
