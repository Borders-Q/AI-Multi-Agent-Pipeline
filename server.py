import os
import re
import json
import asyncio
import base64
import time
import uuid
import psutil
import urllib.request
import aiohttp
import uvicorn
import subprocess
from typing import Any, Optional
import sys

# Windows 平台下屏蔽 Uvicorn/asyncio 底层无害的 socket.shutdown 报错 (WinError 10022/10054)
if sys.platform == 'win32':
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        def _silenced_call_connection_lost(self, exc):
            try:
                _original_call_connection_lost(self, exc)
            except OSError as e:
                if getattr(e, 'winerror', None) in (10022, 10054, 121):
                    pass
                else:
                    raise
        _ProactorBasePipeTransport._call_connection_lost = _silenced_call_connection_lost
    except ImportError:
        pass

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import db
from agent.llm_client import LANGUAGE_OUTPUT_RULE, llm
from agent.router import build_ollama_messages, is_complex_engineering_task, route_intent, get_prioritized_models
from agent.token_usage import (
    TokenAccumulator,
    empty_token_summary,
    format_token_summary,
    normalize_token_summary,
    usage_from_ollama_response,
    usage_from_openai_response,
)
from agent.tools.native_aci import check_and_kill_port, get_system_resources, check_weather_local
from agent.npu_classifier import npu_engine
from agent.workflow import AgentWorkflowEngine
from agent.markdown_archivist import generate_run_markdown
from agent.code_artifacts import extract_local_urls
from agent.trae_skill_exporter import build_skill_package, build_skill_zip, save_skill_to_workspace
from agent.skill_workflow_importer import import_trae_skill_to_template, tool_schema_to_workflow_template
from agent.skills import tool_manager
import agent.tools.web_skills
import agent.tools.report_tools
from agent.tools.fs_tools import ask_user_for_directory
from agent.distillation_worker import distillation_loop

app = FastAPI(title="Ai Multi Agent API")

@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(distillation_loop())


_fetching_cpu = False

async def fetch_cpu():
    global _fetching_cpu
    if _fetching_cpu: return
    _fetching_cpu = True
    try:
        process = await asyncio.create_subprocess_shell(
            'powershell -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        if stdout:
            SYSTEM_TELEMETRY["cpu_usage"] = float(stdout.decode().strip())
    except Exception:
        pass
    finally:
        _fetching_cpu = False

async def telemetry_loop():
    while True:
        try:
            asyncio.create_task(fetch_cpu())
            mem = psutil.virtual_memory()
            SYSTEM_TELEMETRY["ram_usage"] = mem.percent
            SYSTEM_TELEMETRY["ram_total"] = round(mem.total / (1024 ** 3), 2)
            SYSTEM_TELEMETRY["ram_used"] = round(mem.used / (1024 ** 3), 2)
        except Exception:
            pass
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    # Load all API keys from DB into llm client manager
    keys = db.get_all_api_keys()
    for k in keys:
        llm.add_key(k["api_key"])
    
    # Start NPU model compilation in background (non-blocking)
    npu_engine.warmup_async()
    print("> [Ai Multi Agent] Server ready! NPU models warming up in background...")
    
    # Start GPU idle memory distillation daemon
    asyncio.create_task(distillation_loop())
    
    # Start telemetry cache loop
    asyncio.create_task(telemetry_loop())

# app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class APIKeyRequest(BaseModel):
    api_key: str

class ChatRequest(BaseModel):
    message: str
    provider: str = None
    is_approved: bool = False
    session_id: str = "default"
    is_escalation: bool = False
    location: Optional[dict] = None
    enabled_skills: Optional[list[str]] = None
    workflow_mode: str = "standard"
    force_api: bool = False
    workspace: Optional[str] = None
    autonomy_mode: str = "supervised_auto"
    context_bundle: Optional[dict] = None

class TerminalSessionRequest(BaseModel):
    cwd: Optional[str] = None
    shell: str = "powershell"

class BrowserOpenRequest(BaseModel):
    url: str

class MarkdownGenerateRequest(BaseModel):
    kind: str = "important_work_log"
    workspace: Optional[str] = None

class GPUDraftSaveRequest(BaseModel):
    response_text: str
    workspace: Optional[str] = None
    run_id: Optional[str] = None

@app.post("/api/models/add")
def add_model(req: APIKeyRequest):
    provider, default_model = llm.add_key(req.api_key)
    # Save to database
    db.save_api_key(provider, req.api_key, default_model)
    return {"status": "success", "provider": provider, "model": default_model}

class RemoveModelRequest(BaseModel):
    provider: str

@app.post("/api/models/remove")
def remove_model(req: RemoveModelRequest):
    if req.provider in llm.clients:
        del llm.clients[req.provider]
    # Remove from database
    db.delete_api_key(req.provider)
    return {"status": "success"}

@app.get("/api/models")
def list_models():
    # Fetch from database to include aliases
    keys = db.get_all_api_keys()
    # Format to match existing UI expectations plus alias
    models = []
    db_providers = set()
    for k in keys:
        models.append({
            "provider": k["provider"],
            "model": k["model_name"],
            "alias": k.get("alias")
        })
        db_providers.add(k["provider"])
        
    # Include memory-only clients like 'ollama' that aren't in the DB
    for provider, data in llm.clients.items():
        if provider not in db_providers:
            models.append({
                "provider": provider,
                "model": data.get("model", ""),
                "alias": "Local GPU" if provider == "ollama" else None
            })
            
    return {"models": models}

class UpdateAliasRequest(BaseModel):
    provider: str
    alias: str

@app.post("/api/models/alias")
def update_model_alias(req: UpdateAliasRequest):
    db.update_api_key_alias(req.provider, req.alias)
    return {"status": "success"}

@app.get("/api/sessions")
def get_sessions_endpoint():
    return {"sessions": db.get_sessions()}

@app.get("/api/skills")
def get_skills():

    # We will import web_skills to ensure they are registered



    return {"skills": tool_manager.get_openai_tools()}

class DownloadSkillRequest(BaseModel):
    skill_id: str

class ImportSkillRequest(BaseModel):
    code: str

@app.get("/api/skills/market")
def get_market_skills():

    try:
        url = "http://127.0.0.1:8001/catalog.json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            catalog = json.loads(response.read().decode())
            return {"market_skills": catalog}
    except Exception as e:
        print("Market fetching error:", e)
        return {"market_skills": []}

@app.post("/api/skills/download")
def download_skill(req: DownloadSkillRequest):


    
    # Download code from mock remote registry
    try:
        url = f"http://127.0.0.1:8001/skills/{req.skill_id}.py"
        http_req = urllib.request.Request(url)
        with urllib.request.urlopen(http_req, timeout=5) as response:
            code_str = response.read().decode()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to download skill from registry: {str(e)}")
        
    # Dynamic execution
    try:
        namespace = {}
        exec(code_str, namespace)
        schema = namespace.get("SCHEMA")
        func = namespace.get(schema["name"])
        if func and schema:
            tool_manager.register_tool(func, name=schema["name"], description=schema["description"], params_schema=schema["parameters"])
            return {"status": "success", "message": f"Skill {schema['name']} installed"}
        else:
            raise Exception("Invalid skill code format: missing SCHEMA or function")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to install skill: {str(e)}")

@app.post("/api/skills/import")
def import_skill(req: ImportSkillRequest):

    try:
        namespace = {}
        exec(req.code, namespace)
        schema = namespace.get("SCHEMA")
        if not schema:
            raise Exception("Missing SCHEMA definition")
        func_name = schema.get("name")
        func = namespace.get(func_name)
        if not func:
            raise Exception(f"Function {func_name} not found in code")
            
        tool_manager.register_tool(func, name=schema["name"], description=schema["description"], params_schema=schema["parameters"])
        return {"status": "success", "message": "Custom skill imported"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import skill: {str(e)}")

@app.get("/api/history/{session_id}")
def get_history(session_id: str):
    history = db.get_history(session_id)
    return {"history": history}

@app.post("/api/history/clear/{session_id}")
def clear_history(session_id: str):
    db.clear_history(session_id)
    return {"status": "success"}

class SaveWorkflowRequest(BaseModel):
    workflow_json: Optional[Any] = None

def normalize_workflow_payload(workflow_json):
    if workflow_json is None:
        return None
    if isinstance(workflow_json, str):
        workflow_json = workflow_json.strip()
        return workflow_json or None
    return json.dumps(workflow_json, ensure_ascii=False)

def summarize_workflow_payload(workflow_json):
    if not workflow_json:
        return None
    try:
        data = json.loads(workflow_json) if isinstance(workflow_json, str) else workflow_json
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        meta = data.get("meta") or {}
        return {
            "template_id": meta.get("template_id") or meta.get("id"),
            "template_name": meta.get("template_name") or meta.get("title") or "当前会话工作流",
            "description": meta.get("template_description") or meta.get("description") or "",
            "demo_scene": meta.get("demo_scene") or "",
            "recommended_user_prompt": meta.get("recommended_user_prompt") or "",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "whether_api_needed": bool(meta.get("whether_api_needed", False)),
            "whether_gpu_needed": bool(meta.get("whether_gpu_needed", False)),
            "requires_workspace": bool(meta.get("requires_workspace", False)),
            "artifact_policy": meta.get("artifact_policy") or {},
            "preview_policy": meta.get("preview_policy") or {},
            "official_seed_version": meta.get("official_seed_version") or 0,
        }
    except Exception:
        return {
            "template_id": None,
            "template_name": "当前会话工作流",
            "description": "工作流 JSON 暂时无法解析，但仍会按原始配置保存。",
            "demo_scene": "",
            "recommended_user_prompt": "",
            "node_count": 0,
            "edge_count": 0,
            "whether_api_needed": False,
            "whether_gpu_needed": False,
            "requires_workspace": False,
            "artifact_policy": {},
            "preview_policy": {},
            "official_seed_version": 0,
        }

@app.get("/api/sessions/{session_id}/workflow")
def get_session_workflow(session_id: str):
    wf = db.get_session_workflow(session_id)
    return {"workflow_json": wf, "workflow_summary": summarize_workflow_payload(wf)}

@app.post("/api/sessions/{session_id}/workflow")
def save_session_workflow(session_id: str, req: SaveWorkflowRequest):
    workflow_json = normalize_workflow_payload(req.workflow_json)
    db.save_session_workflow(session_id, workflow_json)
    return {"status": "success", "workflow_json": workflow_json, "workflow_summary": summarize_workflow_payload(workflow_json)}

# --- Workflow Templates & Agents Endpoints ---
@app.get("/api/workflows/templates")
def get_workflows_templates_endpoint():
    try:
        templates = db.get_workflow_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/templates/{template_id}")
def get_workflow_template_endpoint(template_id: str):
    try:
        template = db.get_workflow_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"template": template}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SaveTemplateRequest(BaseModel):
    title: str
    description: str = ""
    stage: str = "Draft"
    tags: str = ""
    author: str = "System"
    workflow_json: str

class ExportTraeSkillRequest(BaseModel):
    mode: str = "download"
    workspace: Optional[str] = None

class ExportCurrentWorkflowSkillRequest(BaseModel):
    title: str = "Ai Multi Agent Workflow Skill"
    description: str = ""
    workflow_json: Any
    mode: str = "download"
    workspace: Optional[str] = None

class ImportTraeSkillTemplateRequest(BaseModel):
    file_name: str
    content_base64: str
    save: bool = True
    template_id: Optional[str] = None
    title_override: Optional[str] = None

class SkillToTemplateRequest(BaseModel):
    save: bool = True
    template_id: Optional[str] = None

def _trae_skill_download_response(package: dict) -> Response:
    zip_bytes = build_skill_zip(package)
    filename = f"{package['skill_name']}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

def _export_trae_skill_response(title: str, description: str, workflow_json: Any, req_mode: str, workspace: Optional[str], template_id: str = ""):
    package = build_skill_package(title, description, workflow_json, template_id=template_id)
    mode = (req_mode or "download").strip().lower()
    if mode == "workspace":
        try:
            saved = save_skill_to_workspace(package, workspace or "")
            return {"status": "success", "mode": "workspace", **saved}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    if mode != "download":
        raise HTTPException(status_code=400, detail="mode must be 'download' or 'workspace'")
    return _trae_skill_download_response(package)

def _save_imported_workflow_template(payload: dict, *, tags: str = "Skill,Imported"):
    db.save_workflow_template(
        payload["template_id"],
        payload["title"],
        payload.get("description") or "",
        "Imported",
        tags,
        "Ai Multi Agent User",
        payload["workflow_json"],
    )

@app.post("/api/workflows/templates/{template_id}")
def save_workflow_template_endpoint(template_id: str, req: SaveTemplateRequest):
    try:
        db.save_workflow_template(
            template_id, req.title, req.description, req.stage, req.tags, req.author, req.workflow_json
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflows/templates/{template_id}/export-trae-skill")
def export_workflow_template_trae_skill_endpoint(template_id: str, req: ExportTraeSkillRequest):
    try:
        template = db.get_workflow_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return _export_trae_skill_response(
            template.get("title") or template_id,
            template.get("description") or "",
            template.get("workflow_json"),
            req.mode,
            req.workspace,
            template_id=template_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflows/export-trae-skill")
def export_current_workflow_trae_skill_endpoint(req: ExportCurrentWorkflowSkillRequest):
    try:
        workflow_json = normalize_workflow_payload(req.workflow_json)
        return _export_trae_skill_response(
            req.title,
            req.description,
            workflow_json,
            req.mode,
            req.workspace,
            template_id="",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflows/import-trae-skill-template")
def import_trae_skill_template_endpoint(req: ImportTraeSkillTemplateRequest):
    try:
        try:
            raw = base64.b64decode(req.content_base64, validate=False)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 content: {exc}")
        payload = import_trae_skill_to_template(
            req.file_name,
            raw,
            template_id=req.template_id or "",
            title_override=req.title_override or "",
        )
        if req.save:
            _save_imported_workflow_template(payload, tags="Skill,Trae,Imported")
        template = db.get_workflow_template(payload["template_id"]) if req.save else {
            "template_id": payload["template_id"],
            "title": payload["title"],
            "description": payload.get("description", ""),
            "workflow_json": payload["workflow_json"],
        }
        return {
            "status": "success",
            "template_id": payload["template_id"],
            "template": template,
            "workflow_json": payload["workflow_json"],
            "warnings": payload.get("warnings", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/workflows/skills/{skill_name}/to-template")
def skill_to_workflow_template_endpoint(skill_name: str, req: SkillToTemplateRequest):
    try:
        tools = tool_manager.get_openai_tools()
        tool = next((item for item in tools if (item.get("function") or {}).get("name") == skill_name), None)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        payload = tool_schema_to_workflow_template(tool, template_id=req.template_id or "")
        if req.save:
            _save_imported_workflow_template(payload, tags="Skill,SystemTool,Imported")
        template = db.get_workflow_template(payload["template_id"]) if req.save else {
            "template_id": payload["template_id"],
            "title": payload["title"],
            "description": payload.get("description", ""),
            "workflow_json": payload["workflow_json"],
        }
        return {
            "status": "success",
            "template_id": payload["template_id"],
            "template": template,
            "workflow_json": payload["workflow_json"],
            "warnings": payload.get("warnings", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/agents")
def get_agents_endpoint():
    try:
        agents = db.get_agents()
        return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple in-memory flag for plan state (In a real app, this belongs in memory.py)
current_plan_state = {"waiting_approval": False, "plan_content": "", "pending_message": ""}

# ==================== Codex-Style Auto File Saver ====================

EXT_MAP = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts", "tsx": ".tsx", "jsx": ".jsx",
    "html": ".html", "css": ".css", "scss": ".scss",
    "java": ".java", "go": ".go", "rust": ".rs",
    "c": ".c", "cpp": ".cpp", "h": ".h",
    "sql": ".sql", "json": ".json",
    "yaml": ".yaml", "yml": ".yml",
    "bash": ".sh", "shell": ".sh", "sh": ".sh", "bat": ".bat",
    "xml": ".xml", "markdown": ".md", "md": ".md",
    "txt": ".txt", "toml": ".toml", "ini": ".ini",
    "dockerfile": "", "makefile": "",
    "flask": ".py", "django": ".py",
}

async def _popup_folder_selector() -> str:
    """Run tkinter folder dialog in a subprocess (non-blocking to async loop)."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ask_user_for_directory)

def _extract_code_blocks(response_text: str) -> list:
    """
    Extract code blocks from an LLM response, intelligently detecting filenames

    Returns: list of dicts [{"filename": str, "lang": str, "code": str}, ...]
    """
    blocks = []
    for match in re.finditer(r'```(\w+)?\n(.*?)```', response_text, re.DOTALL):
        lang = (match.group(1) or "").lower().strip()
        code = match.group(2).strip()
        if not code or len(code) < 5:
            continue

        # Try to extract filename from the text BEFORE this code block
        before_text = response_text[:match.start()]
        last_chunk = before_text[-400:]

        filename = None
        
        # We want the LAST match in the chunk (closest to the code block)
        def get_last_match(pattern):
            matches = list(re.finditer(pattern, last_chunk, re.IGNORECASE))
            return matches[-1] if matches else None

        # Pattern 1: `filename.ext` or 「filename.ext」
        fname_match = get_last_match(r'[`「]([a-zA-Z0-9_\-./\\]+\.\w{1,10})[`」]')
        
        # Pattern 2: ### filename.ext or **filename.ext**
        if not fname_match:
            fname_match = get_last_match(r'(?:#{1,4}\s*|\*\*\s*)([a-zA-Z0-9_\-./\\]+\.\w{1,10})')
            
        # Pattern 3: 创建/文件 filename.ext:
        if not fname_match:
            fname_match = get_last_match(r'(?:创建|文件|file|create|新建|保存)\s*[`"\']?([a-zA-Z0-9_\-./\\]+\.\w{1,10})')
            
        # Pattern 4: A line starting with a filename (like "app.py (核心后端逻辑)")
        if not fname_match:
            lines = last_chunk.split('\n')
            for line in reversed(lines):
                m = re.match(r'^\s*([a-zA-Z0-9_\-./\\]+\.\w{1,10})\b', line)
                if m:
                    fname_match = m
                    break
                    
        if fname_match:
            filename = fname_match.group(1).replace('\\', '/').lstrip('/')
        else:
            ext = EXT_MAP.get(lang, f".{lang}" if lang else ".txt")
            filename = f"file_{len(blocks)+1}{ext}"

        blocks.append({"filename": filename, "lang": lang, "code": code})
    return blocks

async def auto_save_code_blocks(response_text: str, log_cb, provider: str = None, token_tracker: TokenAccumulator = None) -> Optional[str]:
    """
    Core Codex-like engine: detect code blocks in LLM response,
    perform AI self-review to catch runtime/type errors,
    pop up folder selector, save all files.
    Returns a summary string to append to the response, or None.
    """
    blocks = _extract_code_blocks(response_text)
    if not blocks:
        return None

    await log_cb(f"> 🔍 检测到 {len(blocks)} 个代码块，正在触发 AI 自我审查(Self-Review)...")
    
    # === AI Self-Review Step ===
    review_prompt = """请你化身为一位拥有20年以上实战经验、极度强迫症且具备“代码洁癖”的全球顶尖全栈首席架构师（Principal Architect）及高级安全研究员。
你的任务是对以下代码进行“像素级”、“显微镜级别”的极限审查。请拿出“降维打击”的视角，不仅仅停留在语法表面，更要在脑内模拟抽象语法树（AST）、运行时内存分布、高并发抢占执行以及极端网络/边界环境。

你需要做到“举一反三”、“刨根问底”，仔细检查并彻底修复以下各个技术栈的常见且致命的错误（包括但不限于）：

### 1. 🐍【Python 动态类型与生态致命陷阱】
- **类型与隐式转换灾难**：Pygame/OpenCV/PIL 等底层 C/C++ 绑定的图像或 GUI 库中，坐标、尺寸参数必须是强制强整型 `int`，若传入 `float`（如 Python 3 的 `/` 默认返回 float）必定引发 Core Dump 或报错；Tkinter 的 `pack/grid` 混用导致死锁布局。
- **GUI与事件循环卡死**：在 Pygame/Tkinter/PyQt 等 GUI 程序中，如果存在阻塞型死循环（如游戏结束后的等待画面 `while game_over:`）但未在循环体内调用 `pygame.event.get()` 处理事件，将导致整个窗口彻底卡死无响应（Not Responding）且无法关闭。必须确保在任何 GUI 循环内排空事件队列！
- **内存与状态污染**：致命的可变默认参数陷阱（`def func(a=[])` 导致跨调用污染）；深浅拷贝（`copy` vs `deepcopy`）混淆导致的嵌套篡改。
- **作用域与闭包幽灵**：内部函数修改外部不可变变量未声明 `nonlocal`/`global`；在循环中创建闭包引发的延迟绑定（Late Binding）陷阱（如 `lambda` 捕获循环的最终值）。
- **并发与迭代黑洞**：生成器（Generator）耗尽后重复遍历静默无报错返回空数据；多线程 CPU 密集计算受制于 GIL 的假并发；`asyncio` 异步事件循环中混入了同步阻塞 I/O（如 `time.sleep` 或 `requests`）导致全站卡死。
- **精度与异常处理**：金融级浮点数计算未使用 `Decimal` 导致精度丢失；`except Exception: pass` 静默吞噬所有报错打断监控链路。

### 2. ☕【Java/C# JVM与.NET企业级强类型深坑】
- **亿级崩溃元凶 NPE**：极易引发的 `NullPointerException`/`NullReferenceException`。对级联调用或自动拆箱（Unboxing）必须进行防御性判空检查或使用 `Optional`/`?.`。
- **并发与同步死结**：多重锁顺序不一致引发死锁；双重检查锁定（DCL）未加 `volatile` 导致指令重排崩溃；在非线程安全集合遍历时修改引发 `ConcurrentModificationException`；`ThreadLocal` 使用后未在 `finally` 块中显式 `remove()` 造成的内存泄漏与线程复用污染。
- **资源与生命周期**：网络 Socket、文件句柄、数据库 Connection 未在 `finally` 或 `try-with-resources`/`using` 中彻底释放。
- **底层契约破坏**：重写了 `equals()` 却忘记重写 `hashCode()` 导致 HashMap/HashSet 数据彻底击穿；C# 中致命的 `async void` 导致异常被全局吞噬引发崩溃。

### 3. 🌐【JavaScript/TypeScript/大前端与 Node.js 漏洞】
- **框架响应式灾难**：React/Vue 的 Hooks/Watch 依赖数组（Deps）缺失或对象引用频繁突变，引发的“无限重渲染死循环（Infinite Render Loops）”；闭包捕获了过期的脏数据（陈旧闭包 Stale Closure）。
- **异步回调与微任务黑洞**：`Promise` 链断裂、未正确 `await`、缺少 `.catch()` 导致的 `UnhandledPromiseRejection`（会使 Node.js 进程直接挂掉）；在 `forEach` 等普通循环中误用 `await` 导致并发乱序。
- **内存泄漏与上下文丢失**：`this` 指针在回调中丢失；SPA 单页路由跳转时未清理 `setInterval` 或未解绑全局 EventListener 导致的游离 DOM 内存泄漏。
- **类型谎言与污染**：TypeScript 中不负责任地滥用 `any` 或强行 `as` 断言掩盖真实的运行时崩溃风险；原型链污染（Prototype Pollution）。

### 4. ⚙️【C/C++ 底层系统级内存绞肉机】
- **内存与指针大劫**：悬垂指针（Dangling Pointers）、内存泄漏（Memory Leaks）、双重释放（Double Free）、释放后使用（Use-After-Free/UAF）。
- **越界与未定义行为（UB）**：数组越界读写（Buffer Overflow）、Off-by-one（差一错误）；未初始化变量的读取引发随机 UB；隐式有符号整数溢出；破坏严格别名规则（Strict Aliasing）。
- **面向对象隐患**：多态基类的析构函数漏写 `virtual` 导致的派生类内存无法释放；返回局部变量的引用引发野指针。

### 5. 🐹【Go/Rust 现代后端与所有权陷阱】
- **Go 并发漏洞**：Goroutine 泄漏（永远阻塞在无接收者的 Channel 上）；Go 1.22 之前的 `for` 循环变量捕获经典 Bug；未初始化的 `nil` Map 直接写入引发 Panic；多协程无锁并发读写同一个 Map 导致 Fatal Error；在巨型大循环内使用 `defer` 瞬间耗尽文件描述符。
- **Rust 滥用**：在生产环境绕过错误处理滥用 `.unwrap()` 或 `.expect()` 导致线程 Panic；为了逃避借用检查器（Borrow Checker）大量滥用 `unsafe` 块；跨 `.await` 点持有标准库同步锁（`std::sync::Mutex`）引发死锁。

### 6. 💾【数据库、分布式架构与安全死穴】
- **性能杀手与雪崩**：ORM 极其经典的 N+1 查询风暴导致连接池耗尽；缺少索引导致的全表扫描 OOM；在 `for/while` 循环体内密集执行 SQL 查询。
- **分布式与事务**：分布式调用/网络重试缺少幂等性（Idempotency）设计导致的重复扣款或发货；事务边界划分错误或发生异常时未正确 `Rollback`；外部接口调用缺少 Timeout 超时防御机制导致服务雪崩。
- **安全红线**：未经校验的用户输入导致 SQL 注入（未使用参数化预编译查询）、OS 命令注入或目录穿越（Path Traversal）；硬编码明文密码、Token 或 AK/SK（未接入 KMS 或环境变量）；正则表达式灾难性回溯（ReDoS）导致 CPU 挂死。
- **跨平台与时空算术**：写死了特定操作系统的绝对路径（例如 Windows 的 `C:\\` 或 Linux 的 `/root`，未使用 `os.path`/`Pathlib` 处理）；处理时间未统一转化为标准化 UTC 导致跨时区错乱。
- **逻辑黑洞**：明显的逻辑死循环（`While(True)` 缺乏安全可达的退出条件）；除以零（Division by zero）或数组空切片缺乏防范；递归缺少基线终止条件导致栈溢出（StackOverflow）。

=== 🔴 最高执行指令（绝对零容忍纪律）🔴 ===

1. 如果你在审查中发现了上述【任何一个】维度里的隐患、漏洞、崩溃点或不符合生产级最佳实践的代码：
   - 请在开头一针见血地点出致命错误所在（最多用3句简短的话说明）。
   - **紧接着，直接输出修复并全面优化后的【完整可用代码】**。
2. ⚠️ **反截断防偷懒强制约束**：修复后的代码务必【原样、全量】地包含在 Markdown 代码块中！**【绝不允许】使用“...此处省略代码...”、“// 保持不变”、“# 其它逻辑不变”等任何形式的截断占位符！** 你必须交付绝对可以直接全选复制（Copy & Paste）并立刻完美运行的生产级源码！
3. 如果经过你极其严苛、显微镜级别的极限审查后，确信提供的代码健壮如牛、完美无瑕，没有任何一丁点安全隐患、逻辑漏洞、并发风险及语法错误，请你严格并【仅且只】回复这四个字：
审查通过
（不需要任何标点符号，不需要任何额外解释，严禁输出其他废话）。

代码内容：
"""
    for b in blocks:
        review_prompt += f"```{b['lang']}\n{b['code']}\n```\n"
        
    try:
        review_msgs = [{"role": "system", "content": "你是资深的架构师兼测试专家。"}, {"role": "user", "content": review_prompt}]
        review_res = await llm.chat_completion(review_msgs, provider=provider)
        if token_tracker is not None:
            token_tracker.add(getattr(review_res, "skyt_token_usage", None) or usage_from_openai_response(
                review_res,
                provider=provider,
                role="auto_code_review",
                messages=review_msgs,
                output_text=getattr(review_res.choices[0].message, "content", "") if getattr(review_res, "choices", None) else "",
            ))
        review_text = review_res.choices[0].message.content
        
        reviewed_blocks = _extract_code_blocks(review_text)
        if reviewed_blocks and len(reviewed_blocks) >= len(blocks):
            await log_cb("> ⚠️ 审查引擎发现潜在缺陷，已自动应用修复补丁！")
            blocks = reviewed_blocks
            
            # Combine the original text and the review fixes in the summary
            response_text += "\n\n### 🛡️ 自动代码审查机制触发\n已发现原始生成的代码中可能存在类型错误(如坐标非整数)或逻辑缺陷，已为您自动修复并保存最新版本。"
        else:
            await log_cb("> ✅ 审查通过，未发现明显的 Runtime 或 Type 问题。")
    except Exception as e:
        await log_cb(f"> ⚠️ 代码审查过程出现异常，已跳过审查层: {str(e)}")

    await log_cb(f"> 正在弹出文件夹选择器...")

    chosen_dir = await _popup_folder_selector()
    if not chosen_dir or chosen_dir.startswith("Error"):
        await log_cb("> ⚠️ 用户取消了文件夹选择，代码仅展示不保存到本地")
        return None

    await log_cb(f"> 📂 目标文件夹: {chosen_dir}")

    saved_files = []
    for block in blocks:
        filepath = os.path.join(chosen_dir, block["filename"])
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(block["code"])
        saved_files.append(block["filename"])
        await log_cb(f"> 💾 已保存: {block['filename']}")

    summary = f"\n\n---\n📁 **已自动保存 {len(saved_files)} 个审查后的文件到:** `{chosen_dir}`\n"
    for fn in saved_files:
        summary += f"- ✅ `{fn}`\n"
    await log_cb(f"> ✅ 共保存 {len(saved_files)} 个文件到 {chosen_dir}")
    return summary

# =====================================================================

def _safe_code_target_path(target_dir: str, filename: str, index: int) -> tuple[str, str]:
    base_dir = os.path.abspath(target_dir)
    clean_name = (filename or f"file_{index + 1}.txt").replace("\\", "/").lstrip("/")
    clean_name = os.path.normpath(clean_name)
    if clean_name in ("", ".", "..") or clean_name.startswith(".." + os.sep):
        clean_name = os.path.basename(clean_name) or f"file_{index + 1}.txt"
    abs_path = os.path.abspath(os.path.join(base_dir, clean_name))
    if not (abs_path == base_dir or abs_path.startswith(base_dir + os.sep)):
        abs_path = os.path.abspath(os.path.join(base_dir, os.path.basename(clean_name) or f"file_{index + 1}.txt"))
    rel_path = os.path.relpath(abs_path, base_dir).replace("\\", "/")
    return abs_path, rel_path

def _save_code_blocks_to_dir(blocks: list, target_dir: str) -> list[str]:
    os.makedirs(target_dir, exist_ok=True)
    saved_files = []
    used_paths = set()
    for index, block in enumerate(blocks):
        abs_path, rel_path = _safe_code_target_path(target_dir, block.get("filename"), index)
        if rel_path in used_paths:
            stem, ext = os.path.splitext(rel_path)
            rel_path = f"{stem}_{index + 1}{ext}"
            abs_path = os.path.abspath(os.path.join(target_dir, rel_path))
        used_paths.add(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(block.get("code") or "")
        saved_files.append(rel_path)
    return saved_files

@app.post("/api/gpu-draft/save-code")
async def save_gpu_draft_code(req: GPUDraftSaveRequest):
    blocks = _extract_code_blocks(req.response_text or "")
    if not blocks:
        return {"status": "no_code", "saved_files": [], "target_dir": None, "message": "未检测到可保存的 Markdown 代码块。"}

    target_dir = (req.workspace or "").strip()
    if not target_dir:
        target_dir = await _popup_folder_selector()
        if not target_dir or target_dir.startswith("Error"):
            if req.run_id:
                db.save_run_event(req.run_id, "GPU_DRAFT_SAVE", "Workspace", "SKIPPED", "用户取消保存 GPU 代码草稿", json.dumps({
                    "input_payload": {"code_blocks_count": len(blocks)},
                    "output_payload": {"reason": target_dir or "cancelled"},
                }, ensure_ascii=False), 0)
            return {"status": "cancelled", "saved_files": [], "target_dir": None, "message": "已取消保存，代码仍保留在对话中。"}

    target_dir = os.path.abspath(target_dir)
    try:
        saved_files = _save_code_blocks_to_dir(blocks, target_dir)
    except Exception as e:
        if req.run_id:
            db.save_run_event(req.run_id, "GPU_DRAFT_SAVE", "Workspace", "FAILED", f"保存 GPU 代码草稿失败: {str(e)}", json.dumps({
                "input_payload": {"target_dir": target_dir, "code_blocks_count": len(blocks)},
                "output_payload": {"error": str(e)},
            }, ensure_ascii=False), 0)
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

    if req.run_id:
        db.save_run_event(req.run_id, "GPU_DRAFT_SAVE", "Workspace", "SUCCESS", "保存 GPU 代码草稿到本地", json.dumps({
            "input_payload": {"target_dir": target_dir, "code_blocks_count": len(blocks)},
            "output_payload": {"saved_files": saved_files, "target_dir": target_dir},
        }, ensure_ascii=False), 0)

    return {"status": "success", "saved_files": saved_files, "target_dir": target_dir}

@app.post("/api/workspace/bind")
async def bind_workspace():
    # Use the existing background task execution for file dialog
    try:
        path = await _popup_folder_selector()
        if path and not path.startswith("Error"):
            return {"status": "success", "path": path}
        else:
            return {"status": "cancelled", "path": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RunCommandRequest(BaseModel):
    command: str
    workspace: str = None

@app.post("/api/workspace/run")
async def run_workspace_command(req: RunCommandRequest):
    try:
        from agent.tools.fs_tools import start_background_service
        result = start_background_service(req.command, req.workspace)
        urls = extract_local_urls(f"{req.command}\n{result}")
        return {"status": "success", "output": result, "browser_url": urls[0] if urls else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

terminal_sessions = {}

def _safe_terminal_cwd(cwd: Optional[str]) -> str:
    if cwd and os.path.isdir(cwd):
        return os.path.abspath(cwd)
    return os.getcwd()

def _terminal_command(shell: str) -> list[str]:
    normalized = (shell or "powershell").lower()
    if normalized in ("cmd", "cmd.exe"):
        return ["cmd.exe"]
    if normalized in ("pwsh", "pwsh.exe"):
        return ["pwsh.exe", "-NoLogo", "-NoProfile"]
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass"]

@app.post("/api/terminal/sessions")
async def create_terminal_session(req: TerminalSessionRequest):
    cwd = _safe_terminal_cwd(req.cwd)
    session_id = f"TERM_{uuid.uuid4().hex[:10].upper()}"
    terminal_sessions[session_id] = {
        "cwd": cwd,
        "shell": req.shell or "powershell",
        "process": None,
    }
    return {"session_id": session_id, "cwd": cwd, "shell": terminal_sessions[session_id]["shell"]}

@app.delete("/api/terminal/sessions/{session_id}")
async def close_terminal_session(session_id: str):
    session = terminal_sessions.pop(session_id, None)
    process = session.get("process") if session else None
    if process and process.returncode is None:
        process.terminate()
    return {"status": "closed"}

@app.websocket("/api/terminal/sessions/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = terminal_sessions.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "data": "Terminal session not found."})
        await websocket.close()
        return
    await websocket.send_json({"type": "ready", "cwd": session["cwd"], "pid": None})

    command_buffer = ""
    active_process = None

    async def pump_stream(stream, stream_type: str):
        while True:
            chunk = await stream.readline()
            if not chunk:
                break
            await websocket.send_json({
                "type": stream_type,
                "data": chunk.decode("utf-8", errors="replace")
            })

    async def run_terminal_command(command: str):
        nonlocal active_process
        command = command.strip()
        if not command:
            await websocket.send_json({"type": "prompt", "cwd": session["cwd"]})
            return

        cd_match = re.match(r"^(cd|Set-Location)\s+(.+)$", command, re.IGNORECASE)
        if cd_match:
            target = cd_match.group(2).strip().strip('"').strip("'")
            next_cwd = target if os.path.isabs(target) else os.path.abspath(os.path.join(session["cwd"], target))
            if os.path.isdir(next_cwd):
                session["cwd"] = next_cwd
                await websocket.send_json({"type": "stdout", "data": f"{session['cwd']}\r\n"})
            else:
                await websocket.send_json({"type": "stderr", "data": f"Directory not found: {target}\r\n"})
            await websocket.send_json({"type": "prompt", "cwd": session["cwd"]})
            return

        shell_cmd = _terminal_command(session.get("shell", "powershell"))
        if shell_cmd[0].lower().startswith("powershell") or shell_cmd[0].lower().startswith("pwsh"):
            shell_cmd = [*shell_cmd, "-Command", command]
        else:
            shell_cmd = [*shell_cmd, "/c", command]

        active_process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            cwd=session["cwd"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        session["process"] = active_process
        stdout_task = asyncio.create_task(pump_stream(active_process.stdout, "stdout"))
        stderr_task = asyncio.create_task(pump_stream(active_process.stderr, "stderr"))
        await active_process.wait()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        await websocket.send_json({"type": "exit", "code": active_process.returncode, "cwd": session["cwd"]})
        await websocket.send_json({"type": "prompt", "cwd": session["cwd"]})
        active_process = None
        session["process"] = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                event = {"type": "stdin", "data": raw}

            event_type = event.get("type")
            if event_type == "stdin":
                command_buffer += event.get("data", "")
                normalized = command_buffer.replace("\r\n", "\n").replace("\r", "\n")
                if "\n" in normalized:
                    lines = normalized.split("\n")
                    command_buffer = lines.pop()
                    for command in lines:
                        await run_terminal_command(command)
            elif event_type == "resize":
                continue
            elif event_type == "terminate":
                if active_process and active_process.returncode is None:
                    active_process.terminate()
                await websocket.send_json({"type": "prompt", "cwd": session["cwd"]})
    except WebSocketDisconnect:
        pass
    finally:
        if active_process and active_process.returncode is None:
            active_process.terminate()
        terminal_sessions.pop(session_id, None)

@app.post("/api/browser/open-system")
async def open_system_browser(req: BrowserOpenRequest):
    try:
        url = req.url.strip()
        if not re.match(r"^https?://", url):
            url = f"https://{url}"
        if sys.platform == "win32":
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        return {"status": "success", "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

active_chat_tasks = {}

def build_context_bundle_markdown(context_bundle: Optional[dict]) -> str:
    if not context_bundle:
        return ""
    parts = ["\n\n## 本地 GPU 已整理的上下文"]
    original = context_bundle.get("original_message") or ""
    gpu_draft = context_bundle.get("gpu_draft") or ""
    context_md = context_bundle.get("context_md") or ""
    source_run_id = context_bundle.get("source_run_id") or ""
    action = context_bundle.get("action") or ""
    if action:
        parts.append(f"- 触发动作：{action}")
    if source_run_id:
        parts.append(f"- 来源运行：{source_run_id}")
    if original:
        parts.append(f"\n### 用户原始需求\n{original}")
    if gpu_draft:
        parts.append(f"\n### 本地 GPU 初步整理\n{gpu_draft}")
    if context_md and context_md != gpu_draft:
        parts.append(f"\n### 压缩上下文 Markdown\n{context_md}")
    return "\n".join(parts)


def get_session_workflow_summary(session_id: str) -> dict:
    workflow_json = db.get_session_workflow(session_id)
    return summarize_workflow_payload(workflow_json) or {}


def workflow_needs_workspace(summary: dict, user_message: str = "") -> bool:
    if not summary:
        return False
    if summary.get("requires_workspace"):
        return True
    artifact_policy = summary.get("artifact_policy") or {}
    if artifact_policy.get("requires_workspace_when_code"):
        text = (user_message or "").lower()
        code_keywords = [
            "写", "生成", "开发", "系统", "项目", "代码", "flask", "fastapi", "django",
            "html", "css", "js", "ts", "typescript", "python", "sqlite", "vue", "react"
        ]
        return any(keyword in text for keyword in code_keywords)
    return False

async def stream_ollama_chat_to_queue(payload: dict, q: asyncio.Queue, routed_by: str, role: str, message_type: str = "message"):
    model = payload.get("model")
    messages = payload.get("messages") or []
    stream_payload = {**payload, "stream": True}
    partial = ""
    final_chunk = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:11434/api/chat", json=stream_payload, timeout=180) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama HTTP {resp.status}")
                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except Exception:
                        continue
                    final_chunk = chunk
                    content = (chunk.get("message") or {}).get("content") or ""
                    if content:
                        partial += content
                        await q.put({"type": message_type, "response": partial, "status": "streaming", "routed_by": routed_by})
                    if chunk.get("done"):
                        break
    except Exception:
        # Real fallback: one-shot Ollama call, explicitly not marked as streaming.
        async with aiohttp.ClientSession() as session:
            fallback_payload = {**payload, "stream": False}
            async with session.post("http://127.0.0.1:11434/api/chat", json=fallback_payload, timeout=180) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama fallback HTTP {resp.status}")
                final_chunk = await resp.json()
                partial = (final_chunk.get("message") or {}).get("content") or ""
                await q.put({"type": message_type, "response": partial, "status": "streaming", "routed_by": routed_by})

    usage = usage_from_ollama_response(final_chunk or {}, model=model, role=role, messages=messages, output_text=partial)
    return partial, usage

@app.post("/api/chat/stop/{session_id}")
async def stop_chat(session_id: str):
    task_info = active_chat_tasks.get(session_id)
    if task_info:
        task, q = task_info
        task.cancel()
        await q.put({"type": "message", "response": "\n\n[用户终止了生成]", "status": "done", "routed_by": "System"})
        return {"status": "success", "message": "已成功停止生成任务"}
    return {"status": "ignored", "message": "没有正在运行的任务"}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    
    # Remove the early exit so NPU/GPU routes can be evaluated
    async def generate():
        q = asyncio.Queue()
        
        async def log_cb(msg):
            await q.put({"type": "log", "log": msg})
            
        async def bg_task():
            partial_content = ""
            msg_id = None
            run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
            token_tracker = TokenAccumulator()
            workspace_prompt = f"\n当前用户工作区为：{req.workspace}\n" if req.workspace else ""
            
            async def emit_step(node, state="running", routed_by="System", description=None, token_usage=None):
                step = {
                    "type": "execution_step",
                    "node": node,
                    "state": state,
                    "routed_by": routed_by,
                    "description": description or node,
                    "token_usage": token_usage,
                }
                await q.put(step)
                await q.put({"type": "workflow", "node": node, "state": state, "routed_by": routed_by, "description": description, "token_usage": token_usage})

            async def emit_token_summary(summary, routed_by="System"):
                await q.put({
                    "type": "token_usage",
                    "token_usage": summary,
                    "status": "streaming",
                    "routed_by": routed_by,
                    "response": format_token_summary(summary),
                })

            def save_token_event(current_run_id, summary):
                db.save_run_event(
                    current_run_id,
                    "TOKEN_USAGE",
                    "TokenMeter",
                    "SUCCESS",
                    format_token_summary(summary),
                    json.dumps({"token_usage": summary}, ensure_ascii=False),
                    0
                )
            try:
                # Setup
                provider = req.provider
                if provider == "auto" or not provider:
                    provider = None
                
                # Check if this is a complex workflow that REQUIRES Cloud API
                # Reverted: The user wants the local model to be able to run deep workflows (via knowledge distillation) 
                # if they don't explicitly force the Cloud API.
                requires_cloud = req.force_api or req.is_escalation or req.is_approved
                
                if requires_cloud and (not provider or any(x in provider.lower() for x in ["ollama", "gemma", "llama", "qwen"])):
                    # In Force API mode, find the first cloud provider
                    cloud_providers = [k for k in llm.clients.keys() if k != "ollama"]
                    if cloud_providers:
                        provider = cloud_providers[0]
                    else:
                        await log_cb("> ⚠️ 警告：深度工作流强制需要云端大模型，但未检测到云端 API Key，将强行使用本地模型，可能导致智商降级。")
                        provider = list(llm.clients.keys())[0] if llm.clients else None
                elif not provider and llm.clients:
                    provider = list(llm.clients.keys())[0]
                    
                if provider:
                    llm.set_active_provider(provider)
                
                history = db.get_history(req.session_id)
                last_is_plan = len(history) > 0 and history[-1]["role"] == "agent" and history[-1]["type"] == "plan"
                
                if last_is_plan:
                    if req.is_approved:
                        await log_cb("> 用户已批准计划。开始分发任务...")
                        db.save_message(req.session_id, "user", "✅ 批准计划 (Approve & Execute)")
                        
                        # Apply workspace if specified
                        chosen_dir = req.workspace
                        dir_instruction = f"\n\n【用户工作区】: {chosen_dir}\n所有生成的代码文件必须保存到这个目录下。直接使用 write_file 工具写入到该目录。\n" if chosen_dir else ""
                        if chosen_dir:
                            await log_cb(f"> 📂 [Codex模式] 将应用绑定的工作区: {chosen_dir}")
                        else:
                            await log_cb("> 📂 [Codex模式] 请先选择项目文件保存目标文件夹...")
                            chosen_dir = await _popup_folder_selector()
                            if chosen_dir and not chosen_dir.startswith("Error"):
                                await log_cb(f"> ✅ 用户选定目标文件夹: {chosen_dir}")
                                dir_instruction = f"\n\n【用户已通过弹窗选定了文件保存目录】: {chosen_dir}\n所有生成的代码文件必须保存到这个目录下。直接使用 write_file 工具写入到该目录，无需再次调用 ask_user_for_directory。\n"
                            else:
                                await log_cb("> ⚠️ 用户取消了文件夹选择，工作流将在执行时再次询问")
                        
                        # Use AgentWorkflowEngine to execute the complex task with the approved plan
                        engine = AgentWorkflowEngine(provider=provider)
                        engine.session_id = req.session_id
                        
                        plan_content = history[-1]["content"]
                        plan_metadata = {}
                        try:
                            raw_metadata = history[-1].get("metadata_json") if isinstance(history[-1], dict) else None
                            plan_metadata = json.loads(raw_metadata) if raw_metadata else {}
                        except Exception:
                            plan_metadata = {}
                        plan_context_bundle = plan_metadata.get("context_bundle") or {}
                        pending_message = plan_context_bundle.get("original_message") or (history[-2]["content"] if len(history) > 1 else "执行当前计划")
                        
                        approved_message = f"用户原始需求: {pending_message}\n用户已批准以下执行计划，请严格按计划执行:\n{plan_content}{dir_instruction}"
                        
                        routed_by_display = "GPU" if provider and any(x in provider.lower() for x in ["gemma", "ollama", "llama", "qwen"]) else "Cloud API"
                        msg_id = db.save_message(req.session_id, "agent", "正在执行计划，请稍候...", "execution", routed_by=routed_by_display)
                        final_reply = await engine.execute_dag(approved_message, q, routed_by=routed_by_display, enabled_skills=req.enabled_skills, workflow_mode=req.workflow_mode)
                        token_summary = normalize_token_summary(engine.last_token_usage)
                        
                        db.update_message(msg_id, final_reply, metadata_json={"token_usage": token_summary, "run_id": engine.last_run_id})
                        await q.put({"type": "message", "response": final_reply, "status": "done", "routed_by": routed_by_display})
                        return
                    elif not req.is_escalation:
                        # User is sending a revision
                        await log_cb(f"> 用户对计划提出了修改意见: {req.message}\n> 正在打回重做...")
                        plan_content_old = history[-1]["content"]
                        plan_prompt = f"{workspace_prompt}原先的计划：\n{plan_content_old}\n\n用户提出了新的修改意见：{req.message}\n请根据用户的意见修订计划，并输出完整的最新的 Markdown 计划书。"
                        
                        msgs = [{"role": "system", "content": "你是Ai Multi Agent架构师，负责撰写项目执行计划。"}]
                        if history:
                            msgs.extend([{"role": "user" if h["role"] == "user" else "assistant", "content": h["content"]} for h in history[-5:]])
                        msgs.append({"role": "user", "content": plan_prompt})
                        
                        msg_id = db.save_message(req.session_id, "agent", "正在修订计划...", "plan", routed_by="Cloud API")
                        db.create_run_record(run_id, req.session_id, req.message or "修订架构计划")
                        await emit_step("修订架构计划", "running", "Cloud API", "调用 API 根据用户反馈修订计划。")
                        async def plan_stream_cb(text):
                            await q.put({"type": "plan", "plan_content": text, "status": "streaming", "routed_by": "Cloud API"})
                        plan_res = await llm.chat_completion(msgs, provider=provider, stream_callback=plan_stream_cb)
                        plan_content = plan_res.choices[0].message.content
                        call_usage = getattr(plan_res, "skyt_token_usage", None) or usage_from_openai_response(
                            plan_res,
                            provider=provider,
                            role="plan_revision",
                            messages=msgs,
                            output_text=plan_content,
                        )
                        token_tracker.add(call_usage)
                        token_summary = token_tracker.to_dict()
                        
                        db.update_message(msg_id, plan_content, metadata_json={"token_usage": token_summary, "run_id": run_id})
                        db.save_run_event(run_id, "LLM_PLAN", "Cloud API", "SUCCESS", "修订架构计划", json.dumps({
                            "input_payload": {"messages_count": len(msgs)},
                            "output_payload": {"preview": plan_content[:300]},
                            "token_usage": call_usage,
                            "model_info": {"provider": provider, "routed_by": "Cloud API"},
                        }, ensure_ascii=False), 0)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 9.0, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        await emit_step("修订架构计划", "done", "Cloud API", "计划修订完成，Token 已写入运行历史。", call_usage)
                        await emit_token_summary(token_summary, "Cloud API")
                        await q.put({"type": "plan", "plan_content": plan_content, "status": "done", "routed_by": "Cloud API"})
                        await log_cb("> 修订后的计划已生成，等待审查(Approve/Modify)...")
                        return

                await log_cb("> 接收指令，正在进行意图路由(Intent Routing)...")
                await emit_step("意图路由", "running", "System", "读取会话上下文并判断是否使用 NPU、本地 GPU 或云 API。")
                db.save_message(req.session_id, "user", req.message)
                
                t_route_start = time.time()
                history = db.get_history(req.session_id)

                if req.force_api:
                    route_result = {"intent": "COMPLEX_TASK", "routed_by": "Cloud API", "token_usage": empty_token_summary()}
                    await log_cb("> 强制开启 API 模式，直连云端...")
                    await emit_step("意图路由", "done", "Cloud API", "用户强制 API 模式，跳过本地缓冲层。", empty_token_summary())
                    context_action = (req.context_bundle or {}).get("action")
                    if context_action in ("direct_api", "deep_think"):
                        action_label = "启用深度思考" if context_action == "deep_think" else "生成 API 深度计划"
                        if not provider or any(x in str(provider).lower() for x in ["ollama", "gemma", "llama", "qwen"]):
                            message = f"未检测到可用的云端 API Key，无法执行“{action_label}”。请先在模型与 API Key 中配置云端模型。"
                            db.save_message(req.session_id, "agent", message, "error", routed_by="System")
                            await q.put({"type": "error", "response": message, "status": "done", "routed_by": "System"})
                            return
                        context_md = build_context_bundle_markdown(req.context_bundle)
                        api_prompt = (
                            f"用户原始需求：{req.message}\n"
                            f"{context_md}\n\n"
                            "请基于本地 GPU 已整理的上下文，生成一份可让用户确认后执行的 Markdown 深度计划。"
                            "不要忽略 GPU 初稿中的约束；如果草稿中已有代码，请审视结构、补足关键缺口并给出清晰的优化建议。"
                            "计划必须包含：需求理解、架构方案、执行步骤、拟修改或生成的文件、风险点、需要用户确认的问题。"
                            "本轮只输出可审查计划，不要自动写入文件或运行命令。"
                        )
                        msgs = [
                            {"role": "system", "content": "你是 Ai Multi Agent 云端 API 深度计划节点，负责基于本地 GPU 压缩上下文生成可审查、可批准执行的 Markdown 计划。"},
                            {"role": "user", "content": api_prompt}
                        ]
                        db.create_run_record(run_id, req.session_id, req.message or action_label)
                        msg_id = db.save_message(req.session_id, "agent", "正在生成 API 深度计划...", "plan", routed_by="Cloud API")
                        await emit_step(action_label, "running", "Cloud API", "使用本地 GPU 整理后的上下文作为 API 输入。")
                        async def api_stream_cb(text):
                            await q.put({"type": "plan", "plan_content": text, "status": "streaming", "routed_by": "Cloud API"})
                        api_res = await llm.chat_completion(msgs, provider=provider, stream_callback=api_stream_cb)
                        final_reply = api_res.choices[0].message.content or ""
                        call_usage = getattr(api_res, "skyt_token_usage", None) or usage_from_openai_response(
                            api_res,
                            provider=provider,
                            role="api_plan_with_gpu_context",
                            messages=msgs,
                            output_text=final_reply,
                        )
                        token_tracker.add(call_usage)
                        token_summary = token_tracker.to_dict()
                        db.update_message(msg_id, final_reply, metadata_json={"token_usage": token_summary, "run_id": run_id, "context_bundle": req.context_bundle})
                        db.save_run_event(run_id, "LLM_PLAN", "Cloud API", "SUCCESS", action_label, json.dumps({
                            "input_payload": {"context_bundle": req.context_bundle, "prompt": api_prompt[:1600]},
                            "output_payload": {"preview": final_reply[:600]},
                            "token_usage": call_usage,
                            "model_info": {"provider": provider, "routed_by": "Cloud API"},
                        }, ensure_ascii=False), 0)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 9.2, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        await emit_step(action_label, "done", "Cloud API", "API 深度计划已生成，并写入历史与深度回放。", call_usage)
                        await emit_token_summary(token_summary, "Cloud API")
                        await q.put({"type": "plan", "plan_content": final_reply, "status": "done", "routed_by": "Cloud API", "token_usage": token_summary, "context_bundle": req.context_bundle, "run_id": run_id})
                        return
                    if context_action == "workflow_template_demo":
                        workflow_summary = get_session_workflow_summary(req.session_id)
                        template_name = workflow_summary.get("template_name") or (req.context_bundle or {}).get("template_name") or "Workflow Template"
                        routed_by_display = "GPU" if provider and any(x in provider.lower() for x in ["gemma", "ollama", "llama", "qwen"]) else "Cloud API"
                        if workflow_needs_workspace(workflow_summary, req.message) and not req.workspace:
                            message = f"运行「{template_name}」前需要先绑定工作区。这个模板会生成或修改项目文件，Ai Multi Agent 必须先拿到明确目录边界。"
                            db.create_run_record(run_id, req.session_id, req.message or template_name)
                            db.save_run_event(run_id, "WORKFLOW_WORKSPACE_REQUIRED", "WorkflowEngine", "SKIPPED", message, json.dumps({
                                "input_payload": {"template_name": template_name, "workflow_summary": workflow_summary},
                                "output_payload": {"reason": "missing_workspace"},
                            }, ensure_ascii=False), 0)
                            db.save_message(req.session_id, "agent", message, "approval_required", routed_by="System", metadata_json={"run_id": run_id, "context_bundle": req.context_bundle})
                            await q.put({
                                "type": "approval_required",
                                "response": message,
                                "status": "done",
                                "routed_by": "System",
                                "risk": "missing_workspace",
                                "run_id": run_id,
                            })
                            return
                        engine = AgentWorkflowEngine(provider=provider)
                        engine.session_id = req.session_id
                        engine.workspace = req.workspace
                        demo_prompt = (
                            f"比赛演示工作流模板：{template_name}\n"
                            f"用户演示任务：{req.message}\n\n"
                            "请按当前会话绑定的 Workflow Template 节点顺序执行。"
                            "本轮重点展示多 Agent 节点协作、执行步骤、运行历史、深度回放和报告闭环。"
                            f"当前绑定工作区：{req.workspace or '未绑定'}\n"
                            "如果模板策略要求工程产物落盘，请输出带目标文件名的代码块或调用写文件工具；"
                            "如果产物是可运行 Web 服务，请在最终说明中给出 http://127.0.0.1 或 http://localhost 本地预览地址。"
                        )
                        msg_id = db.save_message(req.session_id, "agent", f"正在运行演示模板：{template_name}", "execution", routed_by=routed_by_display)
                        final_reply = await engine.execute_dag(demo_prompt, q, routed_by=routed_by_display, enabled_skills=req.enabled_skills, workflow_mode=req.workflow_mode)
                        token_summary = normalize_token_summary(engine.last_token_usage)
                        db.update_message(msg_id, final_reply, metadata_json={"token_usage": token_summary, "run_id": engine.last_run_id, "context_bundle": req.context_bundle})
                        for url in extract_local_urls(final_reply):
                            await q.put({"type": "browser_open", "url": url, "source": "workflow_template_demo", "run_id": engine.last_run_id})
                        await q.put({"type": "message", "response": final_reply, "status": "done", "routed_by": routed_by_display, "token_usage": token_summary})
                        return
                    autonomy_mode = req.autonomy_mode or "supervised_auto"
                    if autonomy_mode in ("supervised_auto", "full_auto"):
                        if not req.workspace:
                            message = "需要先绑定工作区，Ai Multi Agent 才能安全地自动读写文件、运行命令和启动服务。"
                            await q.put({
                                "type": "approval_required",
                                "response": message,
                                "status": "done",
                                "routed_by": "System",
                                "risk": "missing_workspace"
                            })
                            db.save_message(req.session_id, "agent", message, "approval_required", routed_by="System")
                            return

                        engine = AgentWorkflowEngine(provider=provider)
                        engine.session_id = req.session_id
                        engine.workspace = req.workspace
                        context_md = build_context_bundle_markdown(req.context_bundle)
                        execution_prompt = (
                            f"用户原始需求: {req.message}\n"
                            f"当前绑定工作区: {req.workspace}\n\n"
                            f"{context_md}\n\n"
                            "请以 Codex 式工程代理方式主动完成任务：先快速理解现有项目，再直接实施、运行必要验证并汇报结果。"
                            "允许在绑定工作区内读写文件、运行测试、安装项目依赖、启动本地服务。"
                            "遇到递归删除、格式化磁盘、git reset --hard、覆盖 .env/密钥文件、写入工作区外、全局安装、发布/提交、杀非项目进程等高风险动作时，必须停止并请求用户确认。"
                        )
                        msg_id = db.save_message(req.session_id, "agent", "正在以 API 模式主动执行，请稍候...", "execution", routed_by="Cloud API")
                        final_reply = await engine.execute_dag(execution_prompt, q, routed_by="Cloud API", enabled_skills=req.enabled_skills, workflow_mode=req.workflow_mode)
                        token_summary = normalize_token_summary(engine.last_token_usage)
                        db.update_message(msg_id, final_reply, metadata_json={"token_usage": token_summary, "run_id": engine.last_run_id})
                        await q.put({"type": "message", "response": final_reply, "status": "done", "routed_by": "Cloud API"})
                        return
                else:
                    route_result = await route_intent(req.message, provider=provider, is_escalation=req.is_escalation, history=history)
                    dur_route_ms = int((time.time() - t_route_start) * 1000)
                    intent = route_result.get("intent", "COMPLEX_TASK")
                    route_token_usage = normalize_token_summary(route_result.get("token_usage"))
                    token_tracker.extend(route_token_usage)
                    await emit_step("意图路由", "done", route_result.get("routed_by", "System"), "路由完成，已记录本地模型消耗（如有）。", route_token_usage)
                    
                    if intent == "NATIVE_ACTION":
                        action = route_result.get("action")
                        args = route_result.get("args", {})
                        
                        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
                        db.create_run_record(run_id, req.session_id, req.message)
                        await emit_step(f"[{action}]", "running", "NPU", "执行本地原生命令，不产生 API Token。")
                        
                        await log_cb(f"> 意图命中: NATIVE_ACTION -> {action} | 执行快思考流")
                        
                        t_action_start = time.time()
                        result = ""
                        message_type = "message"
                        final_routed_by = "NPU"
                        if action == "kill_port":
                            port = args.get("port")
                            if port is not None:
                                await log_cb(f"> [Native ACI] 正在检查和清理端口 {port}...")
                                result = check_and_kill_port(int(port))
                                await log_cb(f"> [Native ACI] 执行完毕")
                            else:
                                err = "NATIVE_ACTION (kill_port) 缺少 port 参数"
                                result = err
                                message_type = "error"
                        elif action == "check_resources":
                            await log_cb("> [Native ACI] 正在读取底层硬件指标...")

                            result = get_system_resources()
                            await log_cb("> [Native ACI] 读取完毕")
                        elif action == "check_weather":
                            if req.location:
                                await log_cb("> [Native ACI] 正在通过浏览器 HTML5 Geolocation 进行高精度物理定位...")
                            else:
                                await log_cb("> [Native ACI] 正在进行IP定位并获取实时天气...")

                            raw_weather = check_weather_local(req.location)
                            result = raw_weather.strip() if isinstance(raw_weather, str) else str(raw_weather or "").strip()
                            if not result:
                                result = "暂时没有拿到可用的天气数据，请稍后再试。"
                                await log_cb("> [WARN] 气象局返回为空，已使用兜底提示")
                            else:
                                await log_cb("> [Native ACI] 气象局数据获取成功，交由 GPU 缓冲层拟人化渲染...")
                            
                                # Give it to the GPU to make it sound natural, but never let
                                # an empty render overwrite the raw weather payload.
                                local_models = await get_prioritized_models(prefer_large=True)
                                if local_models:
                                    try:
                                        async with aiohttp.ClientSession() as session:
                                            sys_prompt = f"你是一个智能助理Ai Multi Agent。{LANGUAGE_OUTPUT_RULE}下面是来自中国气象局的实时数据，请你用一句温柔自然的口语把今天的天气报给用户听，不要遗漏数据，切忌机械死板。"
                                            payload = {
                                                "model": local_models[0],
                                                "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"原始气象数据：\n{result}"}],
                                                "stream": False,
                                                "options": {"temperature": 0.6, "num_predict": 150}
                                            }
                                            async with session.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=180) as resp:
                                                if resp.status == 200:
                                                    data = await resp.json()
                                                    rendered = ((data.get("message") or {}).get("content") or "").strip()
                                                    if rendered:
                                                        result = rendered
                                                        final_routed_by = "GPU"
                                                        token_tracker.add(usage_from_ollama_response(
                                                            data,
                                                            model=local_models[0],
                                                            role="weather_local_render",
                                                            messages=payload["messages"],
                                                            output_text=result,
                                                        ))
                                                        await log_cb("> [GPU 渲染] 天气语音拟人化渲染成功")
                                                    else:
                                                        await log_cb("> [WARN] GPU 渲染返回空内容，回退到原生数据")
                                                else:
                                                    await log_cb(f"> [WARN] GPU 渲染接口返回 {resp.status}，回退到原生数据")
                                    except Exception as e:
                                        await log_cb(f"> [WARN] GPU 渲染失败，回退到原生数据: {str(e)}")
                                else:
                                    await log_cb("> [WARN] 未发现可用本地 GPU 模型，直接返回原生天气数据")
                        else:
                            err_msg = f"未知的 Native Action: {action}"
                            result = err_msg
                            message_type = "error"
                            
                        dur_action_ms = int((time.time() - t_action_start) * 1000)
                        if not result or not str(result).strip():
                            result = "已完成本地动作，但没有拿到可展示结果。"
                        token_summary = token_tracker.to_dict()
                        db.save_run_event(run_id, "NPU_ACTION", action, "SUCCESS", f"执行 {action}", json.dumps({
                            "input_payload": {"args": args},
                            "output_payload": {"result": result},
                            "token_usage": token_summary,
                            "model_info": {"routed_by": final_routed_by},
                        }, ensure_ascii=False), dur_action_ms)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 10.0, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        await emit_step(f"[{action}]", "done", final_routed_by, "本地原生动作执行完毕，运行历史已写入。", token_summary)
                        await emit_token_summary(token_summary, final_routed_by)
                        db.save_message(req.session_id, "agent", result, message_type, routed_by=final_routed_by, metadata_json={"token_usage": token_summary, "run_id": run_id})
                        await q.put({"type": "message", "response": result, "status": "done", "routed_by": final_routed_by, "token_usage": token_summary})
                    
                    elif intent in ("GPU_CHAT_STREAM", "GPU_ASSIST"):
                        args = route_result.get("args") or {}
                        routed_by = route_result.get("routed_by", "GPU")
                        is_assist = intent == "GPU_ASSIST"
                        complex_engineering_request = is_complex_engineering_task(req.message or "")
                        if complex_engineering_request and not is_assist:
                            is_assist = True
                            routed_by = "GPU Assist"
                            if args.get("model"):
                                args["messages"] = build_ollama_messages(req.message, history, mode="assist")
                            args["complexity"] = "engineering"
                        message_type = "gpu_draft" if is_assist else "message"
                        action_label = "GPU 辅助整理" if is_assist else "GPU 实时生成回复"

                        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
                        db.create_run_record(run_id, req.session_id, req.message)
                        msg_id = db.save_message(req.session_id, "agent", "正在由本地 GPU 生成...", message_type, routed_by=routed_by)
                        await emit_step(action_label, "running", routed_by, "本地 GPU 正在逐步输出内容。")

                        payload = {
                            "model": args.get("model"),
                            "messages": args.get("messages") or [{"role": "user", "content": req.message}],
                            "options": {"temperature": 0.7, "num_predict": 4096}
                        }
                        reply, call_usage = await stream_ollama_chat_to_queue(
                            payload,
                            q,
                            routed_by=routed_by,
                            role="gpu_assist_context" if is_assist else "gpu_chat_stream",
                            message_type=message_type,
                        )
                        token_tracker.add(call_usage)
                        token_summary = token_tracker.to_dict()
                        code_blocks_count = len(_extract_code_blocks(reply)) if is_assist else 0
                        has_code_blocks = code_blocks_count > 0
                        context_bundle = {
                            "original_message": req.message,
                            "gpu_draft": reply,
                            "context_md": reply,
                            "source_run_id": run_id,
                            "action": "gpu_assist",
                            "has_code_blocks": has_code_blocks,
                            "code_blocks_count": code_blocks_count,
                        } if is_assist else None
                        if is_assist and has_code_blocks:
                            actions = [
                                {"key": "save_code_local", "label": "保存到本地"},
                                {"key": "deep_think_api", "label": "启用深度思考"},
                            ]
                        elif is_assist:
                            actions = [
                                {"key": "edit_requirement", "label": "更改需求"},
                                {"key": "confirm_api", "label": "确认"},
                            ]
                        else:
                            actions = []

                        db.save_run_event(run_id, "GPU_ASSIST" if is_assist else "GPU_CHAT", routed_by, "SUCCESS", action_label, json.dumps({
                            "input_payload": {"message": req.message, "messages_count": len(payload["messages"])},
                            "output_payload": {"reply": reply[:600]},
                            "token_usage": call_usage,
                            "model_info": {"provider": "ollama", "model": args.get("model"), "routed_by": routed_by},
                            "context_bundle": context_bundle,
                            "code_blocks_count": code_blocks_count,
                        }, ensure_ascii=False), dur_route_ms)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 8.8 if is_assist else 9.0, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        db.update_message(msg_id, reply, metadata_json={"token_usage": token_summary, "run_id": run_id, "context_bundle": context_bundle, "actions": actions})
                        await emit_step(action_label, "done", routed_by, "本地 GPU 输出完成，已写入历史与深度回放。", call_usage)
                        await emit_token_summary(token_summary, routed_by)
                        await q.put({
                            "type": message_type,
                            "response": reply,
                            "status": "done",
                            "routed_by": routed_by,
                            "token_usage": token_summary,
                            "actions": actions,
                            "context_bundle": context_bundle,
                            "run_id": run_id,
                        })

                    elif intent == "CHAT":
                        reply = route_result.get("reply", "你好！有什么我可以帮你的吗？")
                        routed_by = route_result.get("routed_by", "GPU")
                        
                        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
                        db.create_run_record(run_id, req.session_id, req.message)
                        await emit_step(f"[{routed_by}] 极速缓冲响应", "running", routed_by, "使用已选路由生成快速回复。", route_token_usage)
                        
                        await log_cb("> 意图命中: CHAT | 执行极速回复")
                        
                        # Save the event that actually happened during routing
                        token_summary = token_tracker.to_dict()
                        db.save_run_event(run_id, "LLM_INFERENCE", routed_by, "SUCCESS", "生成直连响应", json.dumps({
                            "input_payload": {"message": req.message},
                            "output_payload": {"reply": reply[:300] + "..." if len(reply)>300 else reply},
                            "token_usage": token_summary,
                            "model_info": {"routed_by": routed_by},
                        }, ensure_ascii=False), dur_route_ms)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 9.5, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        await emit_step(f"[{routed_by}] 极速缓冲响应", "done", routed_by, "快速回复完成，Token 已写入运行历史。", token_summary)
                        await emit_token_summary(token_summary, routed_by)
                        
                        # === Codex-Style: Auto-detect code blocks and save to user-selected folder ===
                        save_summary = await auto_save_code_blocks(reply, log_cb, provider=provider, token_tracker=token_tracker)
                        if save_summary:
                            reply += save_summary
                            token_summary = token_tracker.to_dict()
                            db.update_run_record(run_id, True, 9.5, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        
                        db.save_message(req.session_id, "agent", reply, "message", routed_by=routed_by, metadata_json={"token_usage": token_summary, "run_id": run_id})
                        await q.put({"type": "message", "response": reply, "status": "done", "routed_by": routed_by})
                        
                    elif intent == "CHAT_STREAM":
                        await log_cb("> 意图命中: CHAT_STREAM | 触发 NPU 生成式模型实时推理")
                        streamer = route_result.get("stream")
                        routed_by = route_result.get("routed_by", "NPU")
                        await q.put({"type": "workflow", "node": f"[{routed_by}] 实时生成回复", "state": "running", "routed_by": routed_by})
                        
                        msg_id = db.save_message(req.session_id, "agent", "正在思考...", "message", routed_by=routed_by)
                        last_save_time = time.time()
                        
                        # Read from the TextIteratorStreamer blocking generator asynchronously
                        for new_text in streamer:
                            if new_text:
                                partial_content += new_text
                                await q.put({"type": "message", "response": partial_content, "status": "streaming", "routed_by": routed_by})
                                if time.time() - last_save_time > 1.0:
                                    db.update_message(msg_id, partial_content)
                                    last_save_time = time.time()
                        
                        # === Codex-Style: Auto-detect code blocks and save to user-selected folder ===
                        save_summary = await auto_save_code_blocks(partial_content, log_cb, provider=provider)
                        if save_summary:
                            partial_content += save_summary
                                
                        db.update_message(msg_id, partial_content)
                        await q.put({"type": "workflow", "node": f"[{routed_by}] 实时生成回复", "state": "done", "routed_by": routed_by})
                        await q.put({"type": "message", "response": partial_content, "status": "done", "routed_by": routed_by})
                    
                    else:
                        await log_cb("> 意图命中: COMPLEX_TASK | 准备进入“先谋后动”计划模式...")
                        context_md = build_context_bundle_markdown(req.context_bundle)
                        autonomy_mode = "ask_each_step" if (req.context_bundle or {}).get("action") == "deep_think" else (req.autonomy_mode or "supervised_auto")
                        if autonomy_mode in ("supervised_auto", "full_auto"):
                            if not req.workspace:
                                message = "需要先绑定工作区，Ai Multi Agent 才能安全地自动读写文件、运行命令和启动服务。"
                                await q.put({
                                    "type": "approval_required",
                                    "response": message,
                                    "status": "done",
                                    "routed_by": "System",
                                    "risk": "missing_workspace"
                                })
                                db.save_message(req.session_id, "agent", message, "approval_required", routed_by="System")
                                return

                            await log_cb("> [Codex Mode] 已启用强自主可确认模式：将主动写文件、运行验证并在高风险动作前停止请求确认。")
                            engine = AgentWorkflowEngine(provider=provider)
                            engine.session_id = req.session_id
                            engine.workspace = req.workspace
                            routed_by_display = "GPU" if provider and any(x in provider.lower() for x in ["gemma", "ollama", "llama", "qwen"]) else "Cloud API"
                            execution_prompt = (
                                f"用户原始需求: {req.message}\n"
                                f"当前绑定工作区: {req.workspace}\n\n"
                                f"{context_md}\n\n"
                                "请以 Codex 式工程代理方式主动完成任务：先快速理解现有项目，再直接实施、运行必要验证并汇报结果。"
                                "允许在绑定工作区内读写文件、运行测试、安装项目依赖、启动本地服务。"
                                "遇到递归删除、格式化磁盘、git reset --hard、覆盖 .env/密钥文件、写入工作区外、全局安装、发布/提交、杀非项目进程等高风险动作时，必须停止并请求用户确认。"
                            )
                            msg_id = db.save_message(req.session_id, "agent", "正在以 Codex 模式主动执行，请稍候...", "execution", routed_by=routed_by_display)
                            final_reply = await engine.execute_dag(execution_prompt, q, routed_by=routed_by_display, enabled_skills=req.enabled_skills, workflow_mode=req.workflow_mode)
                            token_summary = normalize_token_summary(engine.last_token_usage)
                            db.update_message(msg_id, final_reply, metadata_json={"token_usage": token_summary, "run_id": engine.last_run_id})
                            await q.put({"type": "message", "response": final_reply, "status": "done", "routed_by": routed_by_display})
                            return
                        
                        engine = AgentWorkflowEngine(provider=provider)
                        engine.session_id = req.session_id
                        
                        # Generate Plan
                        await log_cb("> 正在生成深度架构计划(Plan)...")
                        plan_prompt = (
                            f"{workspace_prompt}用户提出了一个复杂需求：{req.message}\n"
                            f"{context_md}\n\n"
                            "请你作为架构师，基于本地 GPU 已整理的上下文继续深思。先不要直接写代码，"
                            "输出一份结构清晰的 Markdown 计划书，包含：需求理解、架构设计、执行步骤。"
                            "并附带一些需要用户确认的开放性问题。"
                        )
                        
                        msgs = [{"role": "system", "content": "你是Ai Multi Agent架构师，请输出专业的Markdown计划。\n【强制规则】：如果你要执行修改代码，由于已有了工作区，请根据工作区目录进行思考。"}]
                        if history:
                            msgs.extend([{"role": "user" if h["role"] == "user" else "assistant", "content": h["content"]} for h in history[-5:]])
                        msgs.append({"role": "user", "content": plan_prompt})
                        
                        routed_by_display = "GPU" if provider and any(x in provider.lower() for x in ["gemma", "ollama", "llama", "qwen"]) else "Cloud API"
                        msg_id = db.save_message(req.session_id, "agent", "正在生成架构计划...", "plan", routed_by=routed_by_display)
                        db.create_run_record(run_id, req.session_id, req.message)
                        await emit_step("生成架构计划", "running", routed_by_display, "调用模型生成可审查的执行计划。")
                        async def plan_stream_cb(text):
                            await q.put({"type": "plan", "plan_content": text, "status": "streaming", "routed_by": routed_by_display})

                        plan_res = await llm.chat_completion(msgs, provider=provider, stream_callback=plan_stream_cb)
                        plan_content = plan_res.choices[0].message.content
                        call_usage = getattr(plan_res, "skyt_token_usage", None) or usage_from_openai_response(
                            plan_res,
                            provider=provider,
                            role="plan_generation",
                            messages=msgs,
                            output_text=plan_content,
                        )
                        token_tracker.add(call_usage)
                        token_summary = token_tracker.to_dict()
                        
                        db.update_message(msg_id, plan_content, metadata_json={"token_usage": token_summary, "run_id": run_id})
                        db.save_run_event(run_id, "LLM_PLAN", routed_by_display, "SUCCESS", "生成架构计划", json.dumps({
                            "input_payload": {"messages_count": len(msgs), "requirement": req.message},
                            "output_payload": {"preview": plan_content[:300]},
                            "token_usage": call_usage,
                            "model_info": {"provider": provider, "routed_by": routed_by_display},
                        }, ensure_ascii=False), 0)
                        save_token_event(run_id, token_summary)
                        db.update_run_record(run_id, True, 8.8, token_summary["total_tokens"], token_summary["api_tokens"], token_summary["local_tokens"], token_summary["source"], token_summary)
                        
                        # Send plan to UI
                        await emit_step("生成架构计划", "done", routed_by_display, "计划生成完毕，Token 已写入运行历史。", call_usage)
                        await emit_token_summary(token_summary, routed_by_display)
                        await q.put({"type": "plan", "plan_content": plan_content, "status": "done", "routed_by": routed_by_display})
                        await log_cb("> 计划已生成，等待用户审查(Approve/Modify)...")
            
            except asyncio.CancelledError:
                # Handle task cancellation gracefully and save partial data
                if partial_content:
                    final_text = partial_content + "\n\n[由于您中止了生成，以上为部分已生成内容]"
                    if msg_id:
                        db.update_message(msg_id, final_text)
                    else:
                        db.save_message(req.session_id, "agent", final_text, "message", routed_by="System")
                raise
            except Exception as e:
                err_msg = f"系统执行错误: {str(e)}"
                db.save_message(req.session_id, "agent", err_msg, "error")
                await q.put({"type": "error", "response": err_msg, "status": "done"})

        task = asyncio.create_task(bg_task())
        active_chat_tasks[req.session_id] = (task, q)
        
        try:
            while True:
                data = await q.get()
                yield json.dumps(data) + "\n"
                if data.get("status") == "done":
                    break
        finally:
            active_chat_tasks.pop(req.session_id, None)
                
    return StreamingResponse(generate(), media_type="application/x-ndjson")

SYSTEM_TELEMETRY = {
    "cpu_usage": 0.0,
    "ram_usage": 0.0,
    "ram_total": 0.0,
    "ram_used": 0.0
}

@app.get("/api/telemetry")
async def get_telemetry():
    return SYSTEM_TELEMETRY

# --- New Analytics & Reporting Endpoints ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats_endpoint():
    try:
        return db.get_dashboard_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/distill/{run_id}")
def distill_run(run_id: str):
    """
    Trigger manual distillation for a run to save space.
    """
    try:
        saved_bytes = db.distill_run_data(run_id)
        return {"status": "success", "run_id": run_id, "space_saved_bytes": saved_bytes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/runs")
def get_runs_endpoint(limit: int = 50):
    try:
        return {"runs": db.get_run_records(limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/runs/{run_id}/events")
def get_run_events_endpoint(run_id: str):
    try:
        events = db.get_run_events(run_id)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/runs/{run_id}/generate-markdown")
async def generate_run_markdown_endpoint(run_id: str, req: MarkdownGenerateRequest):
    try:
        return await generate_run_markdown(run_id, kind=req.kind, workspace=req.workspace)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
def get_reports_endpoint(limit: int = 50):
    try:
        import time
        print("[DEBUG] get_reports_endpoint started")
        t0 = time.time()
        res = db.get_reports(limit=limit)
        print(f"[DEBUG] db.get_reports took {time.time() - t0:.3f}s")
        t1 = time.time()
        ret = {"reports": res}
        print(f"[DEBUG] dictionary creation took {time.time() - t1:.3f}s")
        return ret
    except Exception as e:
        print(f"[DEBUG] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ReportCreateRequest(BaseModel):
    title: str
    content: str

@app.post("/api/reports")
def create_report_endpoint(req: ReportCreateRequest):
    try:
        db.save_report(req.title, req.content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/runs/{run_id}/detail")
def get_run_detail_endpoint(run_id: str):
    try:
        detail = db.get_run_detail(run_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"run": detail}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/{report_id}")
def get_report_endpoint(report_id: int):
    try:
        report = db.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/skills/stats")
def get_skills_stats_endpoint():
    try:
        return {"stats": db.get_skill_usage_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/threads")
def debug_threads():
    import sys, traceback
    lines = []
    for th_id, frame in sys._current_frames().items():
        lines.append(f"Thread {th_id}:")
        for line in traceback.format_stack(frame):
            lines.append(line.strip())
        lines.append("")
    return {"threads": "\n".join(lines)}

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)
