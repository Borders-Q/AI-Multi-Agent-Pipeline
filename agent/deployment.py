import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

from agent.tools.fs_tools import start_background_service


TSINGHUA_PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
TSINGHUA_NPM_REGISTRY = "https://mirrors.tuna.tsinghua.edu.cn/npm/"

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


def _dependency_env(extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env.update({
        "PIP_INDEX_URL": TSINGHUA_PIP_INDEX,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INPUT": "1",
        "npm_config_registry": TSINGHUA_NPM_REGISTRY,
    })
    if extra:
        env.update(extra)
    return env


def _run(command: list[str], cwd: Path, timeout: int = 120, env: dict | None = None) -> dict:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
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
            "import inspect",
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
            "app = getattr(module, 'app', None) or getattr(module, 'application', None)",
            "created_by_factory = False",
            "if app is None:",
            "    create_app = getattr(module, 'create_app', None)",
            "    if callable(create_app):",
            "        app = create_app()",
            "        created_by_factory = True",
            "if app is None:",
            "    raise RuntimeError('Flask app object named app/application or create_app() factory was not found.')",
            "def _init_database_if_needed(app_obj):",
            "    init_db = getattr(module, 'init_db', None)",
            "    if not callable(init_db):",
            "        return",
            "    try:",
            "        signature = inspect.signature(init_db)",
            "        required = [",
            "            p for p in signature.parameters.values()",
            "            if p.default is inspect._empty",
            "            and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)",
            "        ]",
            "        if len(required) == 0:",
            "            init_db()",
            "        else:",
            "            init_db(app_obj)",
            "    except TypeError:",
            "        try:",
            "            init_db(app_obj)",
            "        except TypeError:",
            "            init_db()",
            "if not created_by_factory:",
            "    _init_database_if_needed(app)",
            f"app.run(host='127.0.0.1', port={int(port)}, debug=False, use_reloader=False)",
            "",
        ]),
        encoding="utf-8",
    )
    return launcher


def _fallback_static_css() -> str:
    return """* {
  box-sizing: border-box;
}

:root {
  color-scheme: light;
  font-family: Inter, "Microsoft YaHei", Arial, sans-serif;
  background: #f4f7fb;
  color: #172033;
}

body {
  margin: 0;
  min-height: 100vh;
  background: #f4f7fb;
}

a {
  color: inherit;
  text-decoration: none;
}

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: 232px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px 16px;
  background: #101827;
  color: #e7eefc;
  box-shadow: 10px 0 26px rgba(15, 23, 42, 0.14);
}

.sidebar-header,
.sidebar-footer,
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-title {
  font-size: 1.12rem;
  font-weight: 800;
}

.sidebar-nav {
  display: grid;
  gap: 8px;
}

.nav-item {
  min-height: 42px;
  border-radius: 10px;
  padding: 0 12px;
  color: #c9d5ea;
}

.nav-item:hover,
.nav-item.active {
  background: #2563eb;
  color: #fff;
}

.sidebar-footer {
  margin-top: auto;
  color: #9fb0cf;
  font-size: 0.9rem;
}

.main-content {
  min-height: 100vh;
  margin-left: 232px;
  padding: 28px;
}

.page-header {
  margin-bottom: 22px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: clamp(1.8rem, 4vw, 2.6rem);
}

.text-secondary,
.text-muted {
  color: #64748b;
}

.stats-grid,
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 16px;
}

.dashboard-grid {
  align-items: start;
  margin-top: 18px;
}

.stat-card,
.card,
.panel {
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
}

.stat-card__icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #eaf2ff;
  color: #2563eb;
  font-size: 1.2rem;
}

.stat-card__info {
  display: grid;
  gap: 4px;
}

.stat-card__number {
  font-size: 1.7rem;
  font-weight: 800;
}

.stat-card__label {
  color: #64748b;
}

.card-header {
  padding: 16px 18px;
  border-bottom: 1px solid #edf2f7;
}

.card-header h3 {
  margin: 0;
}

.card-body {
  padding: 18px;
}

.table-responsive {
  overflow: auto;
}

.table,
table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 11px 12px;
  border-bottom: 1px solid #e5ecf4;
  text-align: left;
  white-space: nowrap;
}

.badge {
  display: inline-flex;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 0.78rem;
  font-weight: 700;
}

.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-danger { background: #fee2e2; color: #991b1b; }

.rank-list {
  margin: 0;
  padding-left: 24px;
}

.rank-item {
  margin-bottom: 10px;
}

input,
select,
textarea,
button {
  font: inherit;
}

@media (max-width: 900px) {
  .sidebar {
    position: static;
    width: auto;
    border-radius: 0 0 18px 18px;
  }

  .sidebar-nav {
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  }

  .main-content {
    margin-left: 0;
    padding: 18px;
  }
}
"""


def _fallback_static_js() -> str:
    return """if (!window.Chart) {
  window.Chart = function ChartFallback(canvas, config) {
    const context = canvas && canvas.getContext ? canvas.getContext("2d") : null;
    if (context) {
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = "#eaf2ff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = "#2563eb";
      context.font = "16px Microsoft YaHei, Arial";
      context.fillText((config && config.type ? config.type : "chart") + " preview", 18, 32);
    }
    return { destroy() {} };
  };
}
"""


def _repair_static_assets(app_dir: Path) -> dict:
    templates_dir = app_dir / "templates"
    if not templates_dir.is_dir():
        return {"created_files": [], "referenced_files": []}

    template_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in templates_dir.rglob("*.html")
    )
    referenced = set()
    patterns = [
        r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]",
        r"""["']/static/([^"']+\.(?:css|js))["']""",
    ]
    for pattern in patterns:
        referenced.update(match.group(1).replace("\\", "/").lstrip("/") for match in re.finditer(pattern, template_text, re.IGNORECASE))

    if "style.css" in template_text:
        referenced.add("style.css")
    if "app.js" in template_text:
        referenced.add("app.js")

    created = []
    static_dir = app_dir / "static"
    for rel_path in sorted(referenced):
        if not rel_path.lower().endswith((".css", ".js")):
            continue
        target = (static_dir / rel_path).resolve()
        if os.path.commonpath([str(static_dir.resolve()), str(target)]) != str(static_dir.resolve()):
            continue
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix.lower() == ".css":
            target.write_text(_fallback_static_css(), encoding="utf-8")
        else:
            target.write_text(_fallback_static_js(), encoding="utf-8")
        created.append(rel_path)

    return {"created_files": created, "referenced_files": sorted(referenced)}


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

        asset_repair = _repair_static_assets(app_dir)
        if asset_repair["created_files"]:
            result["steps"].append({
                "name": "repair_missing_static_assets",
                "command": "auto-create missing referenced static css/js",
                "cwd": str(app_dir),
                "returncode": 0,
                "stdout": json.dumps(asset_repair, ensure_ascii=False),
                "stderr": "",
                "ok": True,
            })

        if requirements.exists():
            install = _run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-input",
                    "--timeout",
                    "120",
                    "--retries",
                    "3",
                    "--prefer-binary",
                    "-r",
                    str(requirements),
                    "--index-url",
                    TSINGHUA_PIP_INDEX,
                ],
                app_dir,
                timeout=180,
                env=_dependency_env(),
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
            install = _run(
                [
                    "npm",
                    "install",
                    "--registry",
                    TSINGHUA_NPM_REGISTRY,
                    "--fetch-retries",
                    "3",
                    "--fetch-retry-mintimeout",
                    "10000",
                    "--fetch-timeout",
                    "120000",
                ],
                package_dir,
                timeout=300,
                env=_dependency_env(),
            )
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
