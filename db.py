import os
import json
import pymysql
import pymysql.cursors
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import threading
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "skyt_db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is not set in .env")

fernet = Fernet(ENCRYPTION_KEY.encode('utf-8'))

_local = threading.local()
OFFICIAL_WORKFLOW_SEED_VERSION = 4

@contextmanager
def get_connection(use_db=True):
    """Get a MySQL connection with thread-local pooling to avoid constant reconnects."""
    db_name = DB_NAME if use_db else None
    
    # If not using db (e.g., initial DB creation), don't cache
    if not use_db:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        try:
            yield conn
        finally:
            conn.close()
        return

    # Check if this thread already has an active connection
    if not hasattr(_local, "conn") or not _local.conn.open:
        _local.conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    else:
        try:
            _local.conn.ping(reconnect=True)
        except Exception:
            _local.conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=db_name,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            
    yield _local.conn
    # Do NOT close the connection here to reuse it next time in the same thread


def check_health():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
            if not row or row.get("ok") != 1:
                raise RuntimeError("database health query failed")
    return True

def _add_column_if_missing(cursor, table: str, column_sql: str):
    """Run additive migrations safely; MySQL raises 1060 when the column exists."""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1060:
            raise

def _workflow_node(node_id, label, role, description, instruction, x, y, agent_id="custom_agent", stage="analysis", color="#4da3ff", icon="user", inputs=None, outputs=None):
    node_type = "agent"
    if agent_id == "code_agent":
        node_type = "code_agent"
    elif agent_id == "human_approval":
        node_type = "human_approval"
    elif agent_id == "custom_agent":
        node_type = "custom_agent"
    return {
        "id": node_id,
        "type": "customAgent",
        "position": {"x": x, "y": y},
        "data": {
            "label": label,
            "agentId": agent_id,
            "nodeType": node_type,
            "color": color,
            "icon": icon,
            "stage": stage,
            "enabled": True,
            "description": description,
            "role": role,
            "instruction": instruction,
            "systemPrompt": "",
            "inputFields": inputs or ["input"],
            "outputFields": outputs or ["output"],
            "customAgentMeta": {
                "role": role,
                "version": "1.0",
                "promptRef": "",
            } if node_type == "custom_agent" else None,
            "codeAgentConfig": {
                "operation": "write_file",
                "targetPath": "output/workflow_demo.txt",
                "content": "",
                "auditLogPath": "output/workflow_audit.jsonl",
                "dryRun": True,
            } if node_type == "code_agent" else None,
        },
    }

def _workflow_edge(edge_id, source, target, label="", edge_type="control", condition="", loop_policy=None):
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": "smoothstep",
        "label": label,
        "data": {
            "edgeType": edge_type,
            "condition": condition,
            "label": label,
            "loopPolicy": loop_policy
        },
        "markerEnd": {"type": "arrowclosed", "width": 18, "height": 18},
        "style": {"strokeWidth": 2},
    }

def _build_competition_workflow_template(template_id, title, description, demo_scene, recommended_prompt, nodes_def, meta, edges_def=None):
    nodes = []
    node_list = []
    for idx, item in enumerate(nodes_def, start=1):
        node_id = f"{template_id}_n{idx}"
        nodes.append(_workflow_node(
            node_id=node_id,
            label=item["name"],
            role=item["role"],
            description=item["description"],
            instruction=item["instruction"],
            x=80 + (idx - 1) * 300,
            y=120 + (idx % 2) * 36,
            agent_id=item.get("agent_id", "custom_agent"),
            stage=item.get("stage", "analysis"),
            color=item.get("color", "#4da3ff"),
            icon=item.get("icon", "user"),
            inputs=item.get("inputs"),
            outputs=item.get("outputs"),
        ))
        node_list.append({
            "name": item["name"],
            "role": item["role"],
            "responsibility": item["description"],
            "input": item.get("inputs", ["input"]),
            "output": item.get("outputs", ["output"]),
        })
    
    if edges_def is not None:
        edges = []
        edge_list = []
        for idx, edef in enumerate(edges_def, start=1):
            source_id = f"{template_id}_n{edef['source_idx']}"
            target_id = f"{template_id}_n{edef['target_idx']}"
            edges.append(_workflow_edge(
                f"{template_id}_e{idx}", 
                source_id, 
                target_id, 
                label=edef.get("label", ""),
                edge_type=edef.get("edge_type", "control"),
                condition=edef.get("condition", ""),
                loop_policy=edef.get("loop_policy")
            ))
            edge_list.append({
                "from": nodes_def[edef['source_idx'] - 1]["name"],
                "to": nodes_def[edef['target_idx'] - 1]["name"],
                "order": idx
            })
    else:
        edges = [
            _workflow_edge(f"{template_id}_e{idx}", nodes[idx - 1]["id"], nodes[idx]["id"], label=f"{idx} -> {idx + 1}")
            for idx in range(1, len(nodes))
        ]
        edge_list = [
            {"from": nodes_def[idx - 1]["name"], "to": nodes_def[idx]["name"], "order": idx}
            for idx in range(1, len(nodes_def))
        ]
    workflow_meta = {
        "template_id": template_id,
        "template_name": title,
        "template_description": description,
        "official_seed_version": meta.get("official_seed_version", OFFICIAL_WORKFLOW_SEED_VERSION),
        "demo_scene": demo_scene,
        "recommended_user_prompt": recommended_prompt,
        "node_list": node_list,
        "edge_list": edge_list,
        "suitable_for_live_demo": True,
        **meta,
    }
    return json.dumps({"nodes": nodes, "edges": edges, "meta": workflow_meta}, ensure_ascii=False)

def competition_workflow_templates():
    return [
        {
            "template_id": "tmpl_competition_engineering_pipeline",
            "title": "AI 工程生成流水线",
            "description": "把代码工程生成拆成需求理解、架构规划、代码生成、检查和报告，适合展示多 Agent 协作。",
            "stage": "Published",
            "tags": "Competition,Engineering,Code,Demo",
            "author": "天韬（SkyT） System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_engineering_pipeline",
                "AI 工程生成流水线",
                "把复杂代码任务拆成可观察的多节点工程生成流程。",
                "用户输入一个项目需求，例如 Python 贪吃蛇小游戏或 FastAPI 小工具。",
                "帮我生成一个 Python 贪吃蛇小游戏，要求有计分、失败重开和运行说明。",
                [
                    {"name": "需求理解 Agent", "role": "需求分析专家", "description": "提取真实需求、功能点和约束条件。", "instruction": "只做需求拆解，输出功能清单、约束和验收标准。", "agent_id": "ProductAgent", "stage": "analysis", "color": "#ffb347", "icon": "user", "inputs": ["user_requirement"], "outputs": ["feature_list", "constraints"]},
                    {"name": "架构规划 Agent", "role": "架构规划专家", "description": "生成项目结构、文件划分和技术方案。", "instruction": "基于需求输出项目目录、关键模块和技术取舍。", "agent_id": "AiMultiAgentCore", "stage": "analysis", "color": "#b142ff", "icon": "brain", "inputs": ["feature_list", "constraints"], "outputs": ["architecture_plan", "file_structure"]},
                    {"name": "代码生成 Agent", "role": "工程实现者", "description": "生成核心代码文件和关键逻辑。", "instruction": "必须输出完整、可保存的工程代码。每个 Markdown 代码块前必须明确写出目标文件名，例如 `app.py`、`templates/index.html`、`static/app.js`、`static/style.css`。不要只给蓝图或让用户继续选择方向。", "agent_id": "CoderAgent", "stage": "implementation", "color": "#00c781", "icon": "code", "inputs": ["architecture_plan"], "outputs": ["code_blocks", "file_changes"]},
                    {"name": "本地检查 Agent", "role": "质量门禁", "description": "检查代码结构、依赖、语法风险和可运行性。", "instruction": "基于已生成并保存的文件给出必要验证命令；如果是 Flask/前端项目，要给出启动命令和预期本地访问地址，例如 http://127.0.0.1:5000。", "agent_id": "TesterAgent", "stage": "testing", "color": "#ff6b6b", "icon": "shield", "inputs": ["code_blocks"], "outputs": ["test_notes", "risk_list"]},
                    {"name": "报告总结 Agent", "role": "交付说明作者", "description": "输出最终项目说明、运行方式和后续优化建议。", "instruction": "生成可放入报告中心的交付摘要，必须列出已保存文件清单、保存目录、运行检查结果和本地预览地址。", "agent_id": "custom_agent", "stage": "execution", "color": "#60a5fa", "icon": "sparkles", "inputs": ["test_notes", "file_changes"], "outputs": ["final_report"]},
                ],
                {
                    "expected_outputs": ["项目结构", "核心代码块", "运行说明", "检查建议", "最终报告"],
                    "replay_highlights": ["每个 Agent 的输入输出", "代码生成节点的代码块", "检查节点的风险列表", "Token 使用情况"],
                    "report_highlights": ["需求摘要", "文件结构", "运行方式", "后续优化建议"],
                    "competition_demo_value": "最直观展示 天韬（SkyT） 能把复杂代码任务拆成可执行、可回放的多节点流程。",
                    "estimated_complexity": "高",
                    "whether_api_needed": True,
                    "whether_gpu_needed": True,
                    "requires_workspace": True,
                    "artifact_policy": {
                        "mode": "required_workspace",
                        "save_code_blocks": True,
                        "run_checks": True,
                        "summary": "工程生成必须先绑定工作区，并把代码产物真实写入该目录。",
                    },
                    "preview_policy": {
                        "open_local_url": True,
                        "detect_from_output": True,
                        "summary": "最终回复或服务启动输出出现 localhost/127.0.0.1 地址时，自动推送到右侧浏览器。",
                    },
                    "token_cost_notes": "本地 GPU 可先整理需求，云 API 负责关键生成，适合展示 Token 分层。",
                    "risk_notes": "代码落盘和依赖安装应在绑定工作区后演示，高风险命令必须确认。",
                },
                edges_def=[
                    {"source_idx": 1, "target_idx": 2, "label": "", "edge_type": "control"},
                    {"source_idx": 2, "target_idx": 3, "label": "", "edge_type": "control"},
                    {"source_idx": 3, "target_idx": 4, "label": "", "edge_type": "control"},
                    {"source_idx": 4, "target_idx": 3, "label": "检查失败", "edge_type": "loop", "condition": "success == false", "loop_policy": {"maxIterations": 3}},
                    {"source_idx": 4, "target_idx": 5, "label": "检查通过", "edge_type": "branch", "condition": "else"},
                ]
            ),
        },
        {
            "template_id": "tmpl_competition_docs_pipeline",
            "title": "项目文档整理流水线",
            "description": "读取并压缩项目资料，生成维护文档和历史工作记录，展示 天韬（SkyT） 的项目记忆能力。",
            "stage": "Published",
            "tags": "Competition,Docs,Markdown,Memory",
            "author": "天韬（SkyT） System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_docs_pipeline",
                "项目文档整理流水线",
                "把项目文档整理、上下文压缩和 Markdown 归档串成一条演示流水线。",
                "用户希望整理项目文档、架构说明或后续优化 Markdown。",
                "请整理当前项目结构，生成一份后续维护和 vibe coding 使用的 Markdown 指南。",
                [
                    {"name": "文档扫描 Agent", "role": "资料索引员", "description": "识别 README、架构文档、优化文档等文件。", "instruction": "列出需要优先阅读的文档类型和路径线索。", "agent_id": "WebSearch", "stage": "research", "color": "#4facfe", "icon": "search", "inputs": ["workspace_docs"], "outputs": ["doc_index"]},
                    {"name": "架构理解 Agent", "role": "系统架构分析师", "description": "提取项目结构、前后端关系、数据流和核心模块。", "instruction": "把文档索引转成架构要点。", "agent_id": "AiMultiAgentCore", "stage": "analysis", "color": "#b142ff", "icon": "brain", "inputs": ["doc_index"], "outputs": ["architecture_summary"]},
                    {"name": "重点压缩 Agent", "role": "上下文压缩节点", "description": "把长文档压缩成可复用上下文。", "instruction": "保留核心事实，删除重复和无关描述。", "agent_id": "GPU", "stage": "generation", "color": "#0f9d58", "icon": "sparkles", "inputs": ["architecture_summary"], "outputs": ["compressed_context"]},
                    {"name": "Markdown 生成 Agent", "role": "文档生成者", "description": "生成项目优化文档、工作记录或开发指南。", "instruction": "输出结构化 Markdown，默认进入报告中心；如果当前已绑定工作区，可以额外建议归档到 `.skyt/important_work_logs/`，但不要强制要求工作区。", "agent_id": "custom_agent", "stage": "implementation", "color": "#60a5fa", "icon": "code", "inputs": ["compressed_context"], "outputs": ["markdown_doc"]},
                    {"name": "归档记录 Agent", "role": "长期记忆归档员", "description": "把重要结论写入历史工作记录。", "instruction": "总结哪些内容应进入报告中心和重要工作记录；不要读取或输出密钥、.env、隐私文件内容。", "agent_id": "custom_agent", "stage": "execution", "color": "#94a3b8", "icon": "shield", "inputs": ["markdown_doc"], "outputs": ["archive_summary"]},
                ],
                {
                    "expected_outputs": ["文档索引", "架构摘要", "压缩上下文", "Markdown 指南", "归档摘要"],
                    "replay_highlights": ["上下文压缩前后差异", "Markdown 生成节点", "归档结论"],
                    "report_highlights": ["项目结构", "核心模块", "后续维护建议"],
                    "competition_demo_value": "体现 天韬（SkyT） 能为长期项目维护和 vibe coding 保留可复用项目记忆。",
                    "estimated_complexity": "中",
                    "whether_api_needed": False,
                    "whether_gpu_needed": True,
                    "requires_workspace": False,
                    "artifact_policy": {
                        "mode": "report_default",
                        "optional_workspace_archive": True,
                        "summary": "默认生成报告中心文档；已绑定工作区时可额外归档 Markdown。",
                    },
                    "preview_policy": {"open_local_url": False, "summary": "文档整理模板不主动打开浏览器预览。"},
                    "token_cost_notes": "本地 GPU 先压缩上下文，减少 API 读取长文档的 Token 浪费。",
                    "risk_notes": "不要把密钥、.env 或隐私文件写入归档。",
                },
            ),
        },
        {
            "template_id": "tmpl_competition_bugfix_pipeline",
            "title": "问题定位与修复流水线",
            "description": "把 Bug 描述转成定位、分析、方案和验证步骤，适合展示可控修复过程。",
            "stage": "Published",
            "tags": "Competition,Bugfix,Replay,Quality",
            "author": "天韬（SkyT） System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_bugfix_pipeline",
                "问题定位与修复流水线",
                "展示 天韬（SkyT） 如何从用户描述出发，逐步定位问题并给出最小修复方案。",
                "用户描述一个 UI 问题、功能异常或后端报错。",
                "页面流式输出时我往上滚会被强制拉回底部，请帮我定位并给出修复方案。",
                [
                    {"name": "问题理解 Agent", "role": "问题定义专家", "description": "把用户描述转成明确的问题定义。", "instruction": "明确现象、影响范围、触发条件和成功标准。", "agent_id": "ProductAgent", "stage": "analysis", "color": "#ffb347", "icon": "user", "inputs": ["bug_report"], "outputs": ["problem_definition"]},
                    {"name": "相关文件定位 Agent", "role": "代码检索员", "description": "判断可能涉及哪些前端、后端或样式文件。", "instruction": "输出候选文件和定位依据。", "agent_id": "WebSearch", "stage": "research", "color": "#4facfe", "icon": "search", "inputs": ["problem_definition"], "outputs": ["candidate_files"]},
                    {"name": "原因分析 Agent", "role": "根因分析师", "description": "分析可能原因和关键状态流。", "instruction": "说明最可能根因，不做无关重构。", "agent_id": "AiMultiAgentCore", "stage": "analysis", "color": "#b142ff", "icon": "brain", "inputs": ["candidate_files"], "outputs": ["root_cause"]},
                    {"name": "修改方案 Agent", "role": "最小修复设计者", "description": "提出最小必要修改方案。", "instruction": "在绑定工作区内给出最小改动方案；如果需要生成补丁或代码块，每个代码块前必须写明目标文件名，不要大范围重构。", "agent_id": "CoderAgent", "stage": "implementation", "color": "#00c781", "icon": "code", "inputs": ["root_cause"], "outputs": ["fix_plan"]},
                    {"name": "验证建议 Agent", "role": "验收设计者", "description": "说明如何验证修复是否成功。", "instruction": "给出构建、手动测试和回归检查项；如产生可运行本地页面，请提供 localhost 或 127.0.0.1 预览地址。", "agent_id": "TesterAgent", "stage": "testing", "color": "#ff6b6b", "icon": "shield", "inputs": ["fix_plan"], "outputs": ["verification_plan"]},
                ],
                {
                    "expected_outputs": ["问题定义", "候选文件", "根因分析", "最小修复方案", "验证清单"],
                    "replay_highlights": ["文件定位依据", "根因分析节点", "验证建议节点"],
                    "report_highlights": ["Bug 现象", "根因", "修改范围", "测试结果"],
                    "competition_demo_value": "体现 天韬（SkyT） 不是乱改代码，而是可观察地定位、分析、修复和验证。",
                    "estimated_complexity": "中",
                    "whether_api_needed": True,
                    "whether_gpu_needed": True,
                    "requires_workspace": True,
                    "artifact_policy": {
                        "mode": "workspace_patch_or_plan",
                        "save_code_blocks": True,
                        "run_checks": True,
                        "summary": "修复类模板必须绑定工作区；否则只允许生成修复计划，不应写文件。",
                    },
                    "preview_policy": {
                        "open_local_url": True,
                        "detect_from_output": True,
                        "summary": "修复完成后如出现本地预览地址，自动推送右侧浏览器。",
                    },
                    "token_cost_notes": "GPU 可先整理 Bug 描述，API 负责关键分析和修复策略。",
                    "risk_notes": "实际写文件前应绑定工作区，并避免大范围重构。",
                },
            ),
        },
        {
            "template_id": "tmpl_competition_demo_enhance_pipeline",
            "title": "比赛演示增强流水线",
            "description": "围绕比赛展示目标优化 UI、演示路径和讲解文案，突出核心亮点。",
            "stage": "Published",
            "tags": "Competition,Demo,UI,Presentation",
            "author": "天韬（SkyT） System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_demo_enhance_pipeline",
                "比赛演示增强流水线",
                "把比赛展示优化拆成目标、视觉层级、交互简化、路径和讲解词。",
                "用户希望优化页面视觉效果、展示路径或比赛讲解效果。",
                "请帮我优化 天韬（SkyT） 工作流页面的比赛展示路径，让评委快速看懂多 Agent 协作价值。",
                [
                    {"name": "展示目标 Agent", "role": "比赛价值提炼者", "description": "判断这个功能在比赛中要突出什么价值。", "instruction": "输出一句核心展示目标和三个支撑点。", "agent_id": "ProductAgent", "stage": "analysis", "color": "#ffb347", "icon": "user", "inputs": ["demo_goal"], "outputs": ["core_value"]},
                    {"name": "UI 重点 Agent", "role": "视觉层级设计师", "description": "分析页面视觉层级和展示重点。", "instruction": "说明应该强调哪些区域，弱化哪些控件。", "agent_id": "custom_agent", "stage": "generation", "color": "#60a5fa", "icon": "sparkles", "inputs": ["core_value"], "outputs": ["ui_priority"]},
                    {"name": "交互简化 Agent", "role": "演示降噪专家", "description": "判断复杂功能应该弱化或隐藏。", "instruction": "列出现场不应展开讲的复杂设置。", "agent_id": "TesterAgent", "stage": "testing", "color": "#ff6b6b", "icon": "shield", "inputs": ["ui_priority"], "outputs": ["simplification_notes"]},
                    {"name": "演示路径 Agent", "role": "现场操作编排者", "description": "生成比赛现场操作顺序。", "instruction": "输出 3 到 5 分钟可执行演示步骤。", "agent_id": "AiMultiAgentCore", "stage": "analysis", "color": "#b142ff", "icon": "brain", "inputs": ["simplification_notes"], "outputs": ["demo_script_steps"]},
                    {"name": "讲解文案 Agent", "role": "讲解词作者", "description": "生成适合比赛展示的讲解词。", "instruction": "输出自然、简短、适合背诵的讲解稿。", "agent_id": "custom_agent", "stage": "execution", "color": "#94a3b8", "icon": "user", "inputs": ["demo_script_steps"], "outputs": ["speech_script"]},
                ],
                {
                    "expected_outputs": ["展示目标", "UI 强调项", "弱化项", "演示步骤", "讲解文案"],
                    "replay_highlights": ["展示目标如何转成演示路径", "讲解文案生成节点"],
                    "report_highlights": ["演示主线", "关键页面", "讲解词"],
                    "competition_demo_value": "直接服务比赛现场表达，避免把展示变成功能堆叠。",
                    "estimated_complexity": "低",
                    "whether_api_needed": False,
                    "whether_gpu_needed": True,
                    "requires_workspace": False,
                    "artifact_policy": {
                        "mode": "report_only",
                        "save_code_blocks": False,
                        "summary": "比赛演示增强默认输出方案、路径和讲解词，不强制落盘。",
                    },
                    "preview_policy": {"open_local_url": False, "summary": "演示增强模板不主动打开本地预览。"},
                    "token_cost_notes": "本地 GPU 足以生成初稿，必要时再交给 API 润色。",
                    "risk_notes": "不要在比赛现场展开 API Key、密钥和复杂配置细节。",
                },
            ),
        },
        {
            "template_id": "tmpl_competition_gpu_api_pipeline",
            "title": "本地 GPU 辅助 API 生成流水线",
            "description": "展示本地 GPU 先整理上下文，再由云端 API 高质量生成，并记录 Token 与回放。",
            "stage": "Published",
            "tags": "Competition,GPU,API,Token,Replay",
            "author": "天韬（SkyT） System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_gpu_api_pipeline",
                "本地 GPU 辅助 API 生成流水线",
                "展示本地 GPU 与云端 API 的协作分工和 Token 记录闭环。",
                "用户提出复杂生成任务，需要本地 GPU 先整理，再由 API 生成高质量结果。",
                "请为一个 Flask 人员管理系统整理需求并生成 API 调用前的高价值上下文，再给出最终实现方案。",
                [
                    {"name": "本地 GPU 初步理解 Agent", "role": "本地快速理解节点", "description": "快速理解用户需求。", "instruction": "低成本提取目标、约束和缺失信息。", "agent_id": "GPU", "stage": "generation", "color": "#0f9d58", "icon": "sparkles", "inputs": ["raw_requirement"], "outputs": ["gpu_understanding"]},
                    {"name": "本地 GPU 上下文压缩 Agent", "role": "上下文压缩节点", "description": "压缩历史会话、项目文档和无关内容。", "instruction": "只保留 API 需要的高价值上下文。", "agent_id": "GPU", "stage": "generation", "color": "#0f9d58", "icon": "sparkles", "inputs": ["gpu_understanding", "history"], "outputs": ["compressed_context"]},
                    {"name": "API 请求准备 Agent", "role": "API 输入整理者", "description": "整理高价值上下文，形成 API 输入。", "instruction": "输出 API 提示词结构和必须包含的信息。", "agent_id": "custom_agent", "stage": "analysis", "color": "#60a5fa", "icon": "code", "inputs": ["compressed_context"], "outputs": ["api_prompt"]},
                    {"name": "云端 API 高质量生成 Agent", "role": "高质量生成节点", "description": "生成最终方案、代码或文档。", "instruction": "基于 api_prompt 生成稳定、完整、中文的最终方案。如果产出代码，必须按带文件名的 Markdown 代码块输出，并遵守绑定工作区后落盘的规则。", "agent_id": "AiMultiAgentCore", "stage": "implementation", "color": "#b142ff", "icon": "brain", "inputs": ["api_prompt"], "outputs": ["final_result"]},
                    {"name": "Token 统计与回放 Agent", "role": "成本与回放记录员", "description": "记录本地 GPU Token、API Token、总 Token 和执行步骤。", "instruction": "输出 Token 消耗摘要和回放展示重点。", "agent_id": "custom_agent", "stage": "execution", "color": "#94a3b8", "icon": "shield", "inputs": ["final_result"], "outputs": ["token_replay_summary"]},
                ],
                {
                    "expected_outputs": ["GPU 需求理解", "压缩上下文", "API 输入", "最终方案", "Token 与回放摘要"],
                    "replay_highlights": ["GPU 与 API 分工", "Token Usage 事件", "压缩上下文如何进入 API"],
                    "report_highlights": ["协作策略", "Token 消耗", "最终交付物"],
                    "competition_demo_value": "最能体现 天韬（SkyT） 的系统级优势：本地 GPU 辅助 API，而不是替代 API。",
                    "estimated_complexity": "高",
                    "whether_api_needed": True,
                    "whether_gpu_needed": True,
                    "requires_workspace": False,
                    "artifact_policy": {
                        "mode": "conditional_code_workspace",
                        "requires_workspace_when_code": True,
                        "save_code_blocks": True,
                        "summary": "默认展示 GPU/API 协作；如果用户要求生成工程代码，则需要绑定工作区后保存。",
                    },
                    "preview_policy": {
                        "open_local_url": True,
                        "detect_from_output": True,
                        "summary": "协作链路产出本地服务地址时，自动推送右侧浏览器。",
                    },
                    "token_cost_notes": "本地 GPU 先筛选上下文，API 只处理高价值信息，适合展示节省 Token。",
                    "risk_notes": "必须清楚说明本地 GPU 是辅助层，不把复杂工程最终质量完全押给本地模型。",
                },
            ),
        },
    ]

def init_db():
    """Initialize the database and tables."""
    # 1. Create database if not exists
    with get_connection(use_db=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
    # 2. Create tables
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # api_keys table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    provider VARCHAR(50) PRIMARY KEY,
                    encrypted_key TEXT NOT NULL,
                    model_name VARCHAR(100) NOT NULL,
                    alias VARCHAR(100) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Auto-migrate: add alias column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE api_keys ADD COLUMN alias VARCHAR(100) DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                # Error 1060: Duplicate column name
                if e.args[0] != 1060:
                    raise
            
            # sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR(50) PRIMARY KEY,
                    title VARCHAR(255) DEFAULT '新对话',
                    workflow_json LONGTEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Auto-migrate: add workflow_json column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN workflow_json LONGTEXT DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060:
                    raise
            
            # messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content LONGTEXT NOT NULL,
                    type VARCHAR(20) DEFAULT 'message',
                    routed_by VARCHAR(20) DEFAULT NULL,
                    metadata_json LONGTEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session (session_id)
                )
            """)
            _add_column_if_missing(cursor, "messages", "metadata_json LONGTEXT DEFAULT NULL")
            
            # run_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_records (
                    run_id VARCHAR(50) PRIMARY KEY,
                    session_id VARCHAR(50),
                    requirement TEXT,
                    success BOOLEAN DEFAULT FALSE,
                    quality_score DECIMAL(3,1) DEFAULT 0.0,
                    total_tokens INT DEFAULT 0,
                    api_tokens INT DEFAULT 0,
                    local_tokens INT DEFAULT 0,
                    token_source VARCHAR(20) DEFAULT 'none',
                    token_breakdown_json LONGTEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            _add_column_if_missing(cursor, "run_records", "api_tokens INT DEFAULT 0")
            _add_column_if_missing(cursor, "run_records", "local_tokens INT DEFAULT 0")
            _add_column_if_missing(cursor, "run_records", "token_source VARCHAR(20) DEFAULT 'none'")
            _add_column_if_missing(cursor, "run_records", "token_breakdown_json LONGTEXT DEFAULT NULL")
            
            # run_events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(50) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    agent VARCHAR(50) DEFAULT NULL,
                    status VARCHAR(20) DEFAULT 'SUCCESS',
                    message TEXT,
                    detail_json LONGTEXT,
                    duration_ms INT DEFAULT 0,
                    created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_run_id (run_id)
                )
            """)

            # reports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # distilled_knowledge table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS distilled_knowledge (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(50) NOT NULL,
                    requirement TEXT,
                    distilled_content LONGTEXT,
                    space_saved_bytes INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # workflow_templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    template_id VARCHAR(100) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    stage VARCHAR(50) DEFAULT 'Draft',
                    tags VARCHAR(255),
                    author VARCHAR(100) DEFAULT 'System',
                    workflow_json LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)

            # agents table for the palette
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    agent_id VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    color VARCHAR(20) DEFAULT '#ffffff',
                    icon VARCHAR(50) DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Productization schema is additive and versioned independently of
            # the legacy seed tables above.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id VARCHAR(64) PRIMARY KEY,
                    session_id VARCHAR(64) DEFAULT NULL,
                    run_id VARCHAR(64) DEFAULT NULL,
                    task_type VARCHAR(100) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    attempt INT NOT NULL DEFAULT 0,
                    max_attempts INT NOT NULL DEFAULT 3,
                    payload_json LONGTEXT,
                    result_json LONGTEXT,
                    error_text TEXT,
                    worker_id VARCHAR(100) DEFAULT NULL,
                    lease_until DATETIME(3) DEFAULT NULL,
                    next_attempt_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    heartbeat_at DATETIME(3) DEFAULT NULL,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
                    INDEX idx_tasks_claim (status, next_attempt_at, lease_until),
                    INDEX idx_tasks_session (session_id, created_at),
                    INDEX idx_tasks_run (run_id, created_at)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_events (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    task_id VARCHAR(64) NOT NULL,
                    event_type VARCHAR(32) NOT NULL,
                    detail_json LONGTEXT,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_task_events (task_id, created_at, id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_versions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    template_id VARCHAR(100) NOT NULL,
                    version INT NOT NULL,
                    spec_json LONGTEXT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'draft',
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    UNIQUE KEY uq_workflow_version (template_id, version),
                    INDEX idx_workflow_versions_template (template_id, created_at)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id VARCHAR(64) PRIMARY KEY,
                    task_id VARCHAR(64) DEFAULT NULL,
                    session_id VARCHAR(64) DEFAULT NULL,
                    template_id VARCHAR(100) DEFAULT NULL,
                    workflow_version INT DEFAULT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    spec_json LONGTEXT NOT NULL,
                    input_json LONGTEXT,
                    workspace VARCHAR(2048) DEFAULT NULL,
                    current_node_id VARCHAR(100) DEFAULT NULL,
                    plan_revision INT NOT NULL DEFAULT 1,
                    replan_count INT NOT NULL DEFAULT 0,
                    max_replans INT NOT NULL DEFAULT 3,
                    max_parallelism INT NOT NULL DEFAULT 4,
                    model_calls INT NOT NULL DEFAULT 0,
                    total_tokens INT NOT NULL DEFAULT 0,
                    approved TINYINT(1) NOT NULL DEFAULT 0,
                    result_json LONGTEXT,
                    error_text TEXT,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    started_at DATETIME(3) DEFAULT NULL,
                    finished_at DATETIME(3) DEFAULT NULL,
                    updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
                    INDEX idx_workflow_runs_status (status, updated_at),
                    INDEX idx_workflow_runs_session (session_id, created_at),
                    INDEX idx_workflow_runs_template (template_id, created_at)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_node_runs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64) NOT NULL,
                    node_id VARCHAR(100) NOT NULL,
                    attempt INT NOT NULL DEFAULT 1,
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    input_json LONGTEXT,
                    output_json LONGTEXT,
                    error_text TEXT,
                    evidence_json LONGTEXT,
                    provider VARCHAR(80) DEFAULT NULL,
                    model_profile VARCHAR(32) DEFAULT NULL,
                    started_at DATETIME(3) DEFAULT NULL,
                    finished_at DATETIME(3) DEFAULT NULL,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_workflow_node_runs (run_id, node_id, attempt),
                    INDEX idx_workflow_node_status (run_id, status)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64) NOT NULL,
                    label VARCHAR(255) NOT NULL,
                    kind VARCHAR(32) NOT NULL,
                    path VARCHAR(2048) DEFAULT NULL,
                    metadata_json LONGTEXT,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_workflow_checkpoints (run_id, created_at)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_evaluations (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64) NOT NULL,
                    evaluator VARCHAR(100) NOT NULL,
                    score DECIMAL(5,2) DEFAULT NULL,
                    passed TINYINT(1) NOT NULL DEFAULT 0,
                    result_json LONGTEXT,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_workflow_evaluations (run_id, created_at)
                )
            """)
            cursor.execute("INSERT IGNORE INTO schema_migrations (version) VALUES (1), (2)")
            
            # Seed default agents if empty
            cursor.execute("SELECT COUNT(*) as count FROM agents")
            row = cursor.fetchone()
            if row['count'] == 0:
                default_agents = [
                    ('AiMultiAgentCore', '天韬（SkyT） 深思', '深度反思与博弈，负责最复杂逻辑推演', '#b142ff', 'brain'),
                    ('NPU', 'NPU高速节点', '极速缓冲响应，处理结构化快速任务', '#1a73e8', 'zap'),
                    ('GPU', 'GPU拟人渲染', '拟人化语音和文本渲染', '#0f9d58', 'sparkles'),
                    ('WebSearch', '搜索节点', '负责全网搜索资料并整合', '#4facfe', 'search'),
                    ('ProductAgent', '产品经理节点', '负责需求分析和任务拆解', '#ffb347', 'user'),
                    ('CoderAgent', '程序员节点', '负责编写底层代码逻辑', '#00ff9d', 'code'),
                    ('TesterAgent', '测试员节点', '负责自动化测试和校验', '#ff6b6b', 'shield')
                ]
                cursor.executemany(
                    "INSERT INTO agents (agent_id, name, description, color, icon) VALUES (%s, %s, %s, %s, %s)",
                    default_agents
                )
            else:
                legacy_agent_id = "Tian" + "TaoCore"
                legacy_name = chr(0x5929) + chr(0x97EC)
                cursor.execute("SELECT id FROM agents WHERE agent_id=%s", ("AiMultiAgentCore",))
                has_new_core = cursor.fetchone()
                cursor.execute("SELECT id FROM agents WHERE agent_id=%s", (legacy_agent_id,))
                has_legacy_core = cursor.fetchone()
                if has_legacy_core and not has_new_core:
                    cursor.execute(
                        "UPDATE agents SET agent_id=%s, name=%s, description=%s WHERE agent_id=%s",
                        ("AiMultiAgentCore", "天韬（SkyT） 深思", "深度反思与博弈，负责最复杂逻辑推演", legacy_agent_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE agents SET name=%s, description=%s WHERE agent_id=%s OR name LIKE %s",
                        ("天韬（SkyT） 深思", "深度反思与博弈，负责最复杂逻辑推演", "AiMultiAgentCore", f"%{legacy_name}%")
                    )
                
            # Seed default workflow template if empty
            cursor.execute("SELECT COUNT(*) as count FROM workflow_templates")
            row = cursor.fetchone()
            if row['count'] == 0:
                default_wf = '{"nodes":[{"id":"node_1","type":"default","position":{"x":100,"y":100},"data":{"label":"AiMultiAgentCore","name":"天韬（SkyT） 深思"},"style":{"border":"2px solid #b142ff"}}],"edges":[]}'
                cursor.execute(
                    "INSERT INTO workflow_templates (template_id, title, description, stage, tags, author, workflow_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    ("tmpl_default_1", "标准深思流", "默认的 天韬（SkyT） 深度思考工作流", "Published", "Official,Default", "天韬（SkyT） System", default_wf)
                )
            seed_competition_workflow_templates(cursor)

def seed_competition_workflow_templates(cursor=None):
    templates = competition_workflow_templates()
    if cursor is not None:
        for t in templates:
            cursor.execute("SELECT author, workflow_json FROM workflow_templates WHERE template_id=%s", (t["template_id"],))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute(
                    "INSERT INTO workflow_templates (template_id, title, description, stage, tags, author, workflow_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (t["template_id"], t["title"], t["description"], t["stage"], t["tags"], t["author"], t["workflow_json"])
                )
                continue

            legacy_author = "Sky" + "T System"
            official_authors = {"天韬（SkyT） System", legacy_author}
            should_update = existing.get("author") in official_authors
            try:
                current_meta = (json.loads(existing.get("workflow_json") or "{}").get("meta") or {})
                current_version = int(current_meta.get("official_seed_version") or 0)
                should_update = should_update and current_version < OFFICIAL_WORKFLOW_SEED_VERSION
            except Exception:
                should_update = should_update or existing.get("author") in official_authors

            if should_update:
                cursor.execute(
                    "UPDATE workflow_templates SET title=%s, description=%s, stage=%s, tags=%s, author=%s, workflow_json=%s WHERE template_id=%s",
                    (t["title"], t["description"], t["stage"], t["tags"], t["author"], t["workflow_json"], t["template_id"])
                )
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            seed_competition_workflow_templates(cur)

def encrypt_key(api_key: str) -> str:
    return fernet.encrypt(api_key.encode('utf-8')).decode('utf-8')

def decrypt_key(encrypted_key: str) -> str:
    return fernet.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')

def save_api_key(provider: str, api_key: str, model_name: str, alias: str = None):
    encrypted = fernet.encrypt(api_key.encode('utf-8')).decode('utf-8')
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # We use INSERT ... ON DUPLICATE KEY UPDATE to handle existing providers
            # Only update alias if a new one is provided
            if alias is not None:
                cursor.execute(
                    "INSERT INTO api_keys (provider, encrypted_key, model_name, alias) VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE encrypted_key=%s, model_name=%s, alias=%s",
                    (provider, encrypted, model_name, alias, encrypted, model_name, alias)
                )
            else:
                cursor.execute(
                    "INSERT INTO api_keys (provider, encrypted_key, model_name) VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE encrypted_key=%s, model_name=%s",
                    (provider, encrypted, model_name, encrypted, model_name)
                )

def update_api_key_alias(provider: str, alias: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE api_keys SET alias=%s WHERE provider=%s",
                (alias, provider)
            )

def get_all_api_keys():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT provider, encrypted_key, model_name, alias FROM api_keys")
            rows = cursor.fetchall()
            keys = []
            for r in rows:
                decrypted = fernet.decrypt(r['encrypted_key'].encode('utf-8')).decode('utf-8')
                keys.append({
                    "provider": r['provider'],
                    "api_key": decrypted,
                    "model_name": r['model_name'],
                    "alias": r.get('alias')
                })
            return keys

def delete_api_key(provider: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM api_keys WHERE provider = %s", (provider,))

def get_sessions():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT session_id, title, created_at FROM sessions ORDER BY created_at DESC")
            return cursor.fetchall()

def save_session_workflow(session_id: str, workflow_json: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Ensure session exists first
            cursor.execute("INSERT IGNORE INTO sessions (session_id) VALUES (%s)", (session_id,))
            cursor.execute("UPDATE sessions SET workflow_json = %s WHERE session_id = %s", (workflow_json, session_id))

def get_session_workflow(session_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT workflow_json FROM sessions WHERE session_id = %s", (session_id,))
            row = cursor.fetchone()
            return row['workflow_json'] if row else None

def _json_or_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)

def save_message(session_id: str, role: str, content: str, msg_type: str = 'message', routed_by: str = None, metadata_json=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Ensure session exists
            cursor.execute("INSERT IGNORE INTO sessions (session_id) VALUES (%s)", (session_id,))
            
            # If this is a user message, check if we need to set the title
            if role == "user" and msg_type == "message":
                cursor.execute("SELECT title FROM sessions WHERE session_id = %s", (session_id,))
                row = cursor.fetchone()
                if row and row['title'] == '新对话':
                    # Set the title to the first 20 characters of the content
                    new_title = content[:20].strip()
                    if len(content) > 20:
                        new_title += "..."
                    cursor.execute("UPDATE sessions SET title = %s WHERE session_id = %s", (new_title, session_id))
            
            # Insert message
            sql = "INSERT INTO messages (session_id, role, content, type, routed_by, metadata_json) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (session_id, role, content, msg_type, routed_by, _json_or_none(metadata_json)))
            return cursor.lastrowid

def update_message(msg_id: int, content: str, metadata_json=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if metadata_json is None:
                cursor.execute("UPDATE messages SET content=%s WHERE id=%s", (content, msg_id))
            else:
                cursor.execute(
                    "UPDATE messages SET content=%s, metadata_json=%s WHERE id=%s",
                    (content, _json_or_none(metadata_json), msg_id)
                )

def get_history(session_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT role, content, type, routed_by, metadata_json, created_at FROM messages WHERE session_id = %s ORDER BY id ASC", 
                (session_id,)
            )
            return cursor.fetchall()

def clear_history(session_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT run_id FROM run_records WHERE session_id = %s", (session_id,))
            run_ids = [row["run_id"] for row in cursor.fetchall()]
            if run_ids:
                placeholders = ",".join(["%s"] * len(run_ids))
                cursor.execute(f"DELETE FROM run_events WHERE run_id IN ({placeholders})", tuple(run_ids))
                cursor.execute(f"DELETE FROM run_records WHERE run_id IN ({placeholders})", tuple(run_ids))
            cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
            return {
                "deleted_runs": len(run_ids),
                "deleted_session_id": session_id,
            }

# --- Run History & Events Analytics ---

def create_run_record(run_id: str, session_id: str, requirement: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO run_records (run_id, session_id, requirement) VALUES (%s, %s, %s)",
                (run_id, session_id, requirement)
            )

def update_run_record(
    run_id: str,
    success: bool,
    quality_score: float = 0.0,
    total_tokens: int = 0,
    api_tokens: int = None,
    local_tokens: int = None,
    token_source: str = None,
    token_breakdown_json=None,
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if token_breakdown_json is not None and not isinstance(token_breakdown_json, str):
                token_breakdown_json = json.dumps(token_breakdown_json, ensure_ascii=False)
            api_tokens = int(api_tokens if api_tokens is not None else 0)
            local_tokens = int(local_tokens if local_tokens is not None else 0)
            token_source = token_source or ("real" if total_tokens else "none")
            cursor.execute(
                "UPDATE run_records SET success=%s, quality_score=%s, total_tokens=%s, api_tokens=%s, local_tokens=%s, token_source=%s, token_breakdown_json=%s WHERE run_id=%s",
                (success, quality_score, total_tokens, api_tokens, local_tokens, token_source, token_breakdown_json, run_id)
            )

def save_run_event(run_id: str, event_type: str, agent: str, status: str, message: str, detail_json: str = None, duration_ms: int = 0):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO run_events (run_id, event_type, agent, status, message, detail_json, duration_ms) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (run_id, event_type, agent, status, message, detail_json, duration_ms)
            )


def _task_json(value):
    return json.dumps(value, ensure_ascii=False, default=str) if value is not None else None


def create_task(task_id: str, task_type: str, payload: dict, *, session_id: str = None, run_id: str = None, max_attempts: int = 3):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks (task_id, session_id, run_id, task_type, status, max_attempts, payload_json) VALUES (%s, %s, %s, %s, 'queued', %s, %s)",
                (task_id, session_id, run_id, task_type, max_attempts, _task_json(payload or {})),
            )


def _decode_task(row):
    if not row:
        return row
    row = dict(row)
    payload_raw = row.pop("payload_json", None)
    result_raw = row.pop("result_json", None)
    try:
        row["payload"] = json.loads(payload_raw) if payload_raw else {}
    except (TypeError, json.JSONDecodeError):
        row["payload"] = {}
    try:
        row["result"] = json.loads(result_raw) if result_raw else None
    except (TypeError, json.JSONDecodeError):
        row["result"] = None
    return row


def get_task(task_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE task_id=%s", (task_id,))
            return _decode_task(cursor.fetchone())


def get_task_events(task_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM task_events WHERE task_id=%s ORDER BY created_at ASC, id ASC", (task_id,))
            rows = cursor.fetchall()
            for row in rows:
                raw = row.pop("detail_json", None)
                try:
                    row["detail"] = json.loads(raw) if raw else {}
                except (TypeError, json.JSONDecodeError):
                    row["detail"] = {"raw": raw}
            return rows


def save_task_event(task_id: str, event_type: str, detail: dict | None = None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO task_events (task_id, event_type, detail_json) VALUES (%s, %s, %s)",
                (task_id, event_type, _task_json(detail)),
            )


def recover_stale_tasks():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status='queued', worker_id=NULL, lease_until=NULL, next_attempt_at=NOW(3), updated_at=NOW(3) WHERE status='running' AND lease_until IS NOT NULL AND lease_until < NOW(3)"
            )


def claim_next_task(worker_id: str, lease_seconds: int = 300):
    lease_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=lease_seconds)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # MySQL 8 row locking prevents two workers from claiming the same task.
            conn.begin()
            try:
                cursor.execute(
                    "SELECT task_id FROM tasks WHERE status='queued' AND next_attempt_at <= NOW(3) ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED"
                )
                candidate = cursor.fetchone()
                if not candidate:
                    conn.commit()
                    return None
                cursor.execute(
                    "UPDATE tasks SET status='running', attempt=attempt+1, worker_id=%s, lease_until=%s, heartbeat_at=NOW(3), updated_at=NOW(3) WHERE task_id=%s AND status='queued'",
                    (worker_id, lease_until, candidate["task_id"]),
                )
                if cursor.rowcount != 1:
                    conn.rollback()
                    return None
                cursor.execute("SELECT * FROM tasks WHERE task_id=%s", (candidate["task_id"],))
                task = _decode_task(cursor.fetchone())
                conn.commit()
                return task
            except Exception:
                conn.rollback()
                raise


def heartbeat_task(task_id: str, worker_id: str, lease_seconds: int = 300):
    lease_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=lease_seconds)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET heartbeat_at=NOW(3), lease_until=%s, updated_at=NOW(3) WHERE task_id=%s AND worker_id=%s AND status='running'",
                (lease_until, task_id, worker_id),
            )


def complete_task(task_id: str, result: dict):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status=IF(status='cancel_requested', 'cancelled', 'succeeded'), result_json=%s, error_text=NULL, worker_id=NULL, lease_until=NULL, updated_at=NOW(3) WHERE task_id=%s AND status IN ('running', 'cancel_requested')",
                (_task_json(result), task_id),
            )
            return cursor.rowcount == 1


def fail_task(task_id: str, error: str, *, retry: bool):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT attempt, status FROM tasks WHERE task_id=%s", (task_id,))
            row = cursor.fetchone() or {}
            if row.get("status") == "cancel_requested":
                cursor.execute(
                    "UPDATE tasks SET status='cancelled', error_text=%s, worker_id=NULL, lease_until=NULL, updated_at=NOW(3) WHERE task_id=%s",
                    (error[:4000], task_id),
                )
            elif retry:
                delay = min(300, 2 ** max(0, int(row.get("attempt") or 1)))
                next_attempt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=delay)
                cursor.execute(
                    "UPDATE tasks SET status='queued', error_text=%s, worker_id=NULL, lease_until=NULL, next_attempt_at=%s, updated_at=NOW(3) WHERE task_id=%s",
                    (error[:4000], next_attempt, task_id),
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status='failed', error_text=%s, worker_id=NULL, lease_until=NULL, updated_at=NOW(3) WHERE task_id=%s",
                    (error[:4000], task_id),
                )


def request_task_cancel(task_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status=IF(status='queued', 'cancelled', 'cancel_requested'), updated_at=NOW(3) WHERE task_id=%s AND status IN ('queued', 'running')",
                (task_id,),
            )
            return cursor.rowcount == 1


def is_task_cancel_requested(task_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM tasks WHERE task_id=%s", (task_id,))
            row = cursor.fetchone()
            return bool(row and row.get("status") in {"cancel_requested", "cancelled"})


def mark_task_cancelled(task_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status='cancelled', worker_id=NULL, lease_until=NULL, updated_at=NOW(3) WHERE task_id=%s AND status IN ('queued', 'cancel_requested', 'running')",
                (task_id,),
            )
            return cursor.rowcount == 1


def list_tasks(limit: int = 50):
    limit = max(1, min(int(limit), 200))
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s", (limit,))
            return [_decode_task(row) for row in cursor.fetchall()]


def _decode_workflow_run(row):
    if not row:
        return row
    result = dict(row)
    for source, target, default in (
        ("spec_json", "workflow_spec", {}),
        ("input_json", "input", {}),
        ("result_json", "result", None),
    ):
        raw = result.pop(source, None)
        try:
            result[target] = json.loads(raw) if raw else default
        except (TypeError, json.JSONDecodeError):
            result[target] = default
    return result


def create_workflow_run(run_id: str, spec: dict, input_data: dict, *, session_id: str = "default", workspace: str | None = None, task_id: str | None = None) -> dict:
    policy = spec.get("policy") or {}
    meta = spec.get("meta") or {}
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO workflow_runs (run_id, task_id, session_id, template_id, workflow_version, status, spec_json, input_json, workspace, max_replans, max_parallelism) VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s, %s, %s, %s)",
                (run_id, task_id, session_id, spec.get("workflow_id") or meta.get("template_id"), spec.get("spec_version", 2), _task_json(spec), _task_json(input_data or {}), workspace, int(policy.get("max_replans", 3)), int(policy.get("max_parallelism", 4)))
            )
    return get_workflow_run(run_id)


def get_workflow_run(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_runs WHERE run_id=%s", (run_id,))
            return _decode_workflow_run(cursor.fetchone())


def list_workflow_runs(limit: int = 50, session_id: str | None = None):
    limit = max(1, min(int(limit), 200))
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if session_id:
                cursor.execute("SELECT * FROM workflow_runs WHERE session_id=%s ORDER BY created_at DESC LIMIT %s", (session_id, limit))
            else:
                cursor.execute("SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT %s", (limit,))
            return [_decode_workflow_run(row) for row in cursor.fetchall()]


def update_workflow_run(run_id: str, *, status: str | None = None, task_id: str | None = None, current_node_id: str | None = None, result: dict | None = None, error: str | None = None, approved: bool | None = None, replan_count: int | None = None, plan_revision: int | None = None, model_calls: int | None = None, total_tokens: int | None = None):
    fields = []
    values = []
    if status is not None:
        fields.append("status=%s")
        values.append(status)
        if status == "running":
            fields.append("started_at=COALESCE(started_at, CURRENT_TIMESTAMP(3))")
        if status in {"succeeded", "failed", "cancelled"}:
            fields.append("finished_at=CURRENT_TIMESTAMP(3)")
    for column, value in (("task_id", task_id), ("current_node_id", current_node_id), ("approved", approved), ("replan_count", replan_count), ("plan_revision", plan_revision), ("model_calls", model_calls), ("total_tokens", total_tokens)):
        if value is not None:
            fields.append(f"{column}=%s")
            values.append(value)
    if result is not None:
        fields.append("result_json=%s")
        values.append(_task_json(result))
    if error is not None:
        fields.append("error_text=%s")
        values.append(str(error)[:8000])
    if not fields:
        return get_workflow_run(run_id)
    values.append(run_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE workflow_runs SET {', '.join(fields)}, updated_at=CURRENT_TIMESTAMP(3) WHERE run_id=%s", tuple(values))
    return get_workflow_run(run_id)


def replace_workflow_spec(run_id: str, spec: dict, *, replan_count: int, plan_revision: int, status: str = "queued"):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE workflow_runs SET spec_json=%s, replan_count=%s, plan_revision=%s, status=%s, error_text=NULL, finished_at=NULL, updated_at=CURRENT_TIMESTAMP(3) WHERE run_id=%s", (_task_json(spec), replan_count, plan_revision, status, run_id))
    return get_workflow_run(run_id)


def create_workflow_node_run(run_id: str, node_id: str, attempt: int, *, status: str = "running", input_data: dict | None = None, provider: str | None = None, model_profile: str | None = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO workflow_node_runs (run_id, node_id, attempt, status, input_json, provider, model_profile, started_at) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(3))", (run_id, node_id, attempt, status, _task_json(input_data or {}), provider, model_profile))
            return cursor.lastrowid


def finish_workflow_node_run(node_run_id: int, *, status: str, output: dict | None = None, error: str | None = None, evidence: dict | None = None, provider: str | None = None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE workflow_node_runs SET status=%s, output_json=%s, error_text=%s, evidence_json=%s, provider=COALESCE(%s, provider), finished_at=CURRENT_TIMESTAMP(3) WHERE id=%s", (status, _task_json(output), error, _task_json(evidence), provider, node_run_id))


def get_workflow_node_runs(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_node_runs WHERE run_id=%s ORDER BY created_at ASC, id ASC", (run_id,))
            rows = cursor.fetchall()
            for row in rows:
                for source, target in (("input_json", "input"), ("output_json", "output"), ("evidence_json", "evidence")):
                    raw = row.pop(source, None)
                    try:
                        row[target] = json.loads(raw) if raw else {}
                    except (TypeError, json.JSONDecodeError):
                        row[target] = {}
            return rows


def save_workflow_checkpoint(run_id: str, checkpoint: dict):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO workflow_checkpoints (run_id, label, kind, path, metadata_json) VALUES (%s, %s, %s, %s, %s)", (run_id, checkpoint.get("label", "checkpoint"), checkpoint.get("kind", "snapshot"), checkpoint.get("path"), _task_json(checkpoint.get("metadata") or {})))


def get_workflow_checkpoints(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_checkpoints WHERE run_id=%s ORDER BY created_at ASC, id ASC", (run_id,))
            rows = cursor.fetchall()
            for row in rows:
                raw = row.pop("metadata_json", None)
                try:
                    row["metadata"] = json.loads(raw) if raw else {}
                except (TypeError, json.JSONDecodeError):
                    row["metadata"] = {}
            return rows


def save_workflow_evaluation(run_id: str, evaluator: str, score: float | None, passed: bool, result: dict):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO workflow_evaluations (run_id, evaluator, score, passed, result_json) VALUES (%s, %s, %s, %s, %s)", (run_id, evaluator, score, passed, _task_json(result)))


def get_workflow_evaluations(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_evaluations WHERE run_id=%s ORDER BY created_at ASC, id ASC", (run_id,))
            rows = cursor.fetchall()
            for row in rows:
                raw = row.pop("result_json", None)
                try:
                    row["result"] = json.loads(raw) if raw else {}
                except (TypeError, json.JSONDecodeError):
                    row["result"] = {}
            return rows


def save_workflow_version(template_id: str, version: int, spec: dict, status: str = "draft"):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO workflow_versions (template_id, version, spec_json, status) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE spec_json=%s, status=%s", (template_id, version, _task_json(spec), status, _task_json(spec), status))


def get_workflow_versions(template_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_versions WHERE template_id=%s ORDER BY version DESC", (template_id,))
            rows = cursor.fetchall()
            for row in rows:
                raw = row.pop("spec_json", None)
                try:
                    row["workflow_spec"] = json.loads(raw) if raw else {}
                except (TypeError, json.JSONDecodeError):
                    row["workflow_spec"] = {}
            return rows

def get_run_records(limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM run_records ORDER BY created_at DESC LIMIT %s", (limit,))
            return cursor.fetchall()

def get_run_session_records(limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.session_id,
                    COALESCE(NULLIF(s.title, ''), '新对话') AS title,
                    COUNT(*) AS run_count,
                    SUM(IF(r.success=1, 1, 0)) AS success_count,
                    SUM(IF(r.success=1, 0, 1)) AS failed_count,
                    IF(SUM(IF(r.success=1, 0, 1)) = 0, 1, 0) AS success,
                    AVG(r.quality_score) AS quality_score,
                    SUM(r.total_tokens) AS total_tokens,
                    SUM(r.api_tokens) AS api_tokens,
                    SUM(r.local_tokens) AS local_tokens,
                    IF(SUM(r.total_tokens) > 0, 'mixed', 'none') AS token_source,
                    MIN(r.created_at) AS first_run_at,
                    MAX(r.updated_at) AS last_run_at,
                    MAX(r.created_at) AS created_at,
                    SUBSTRING_INDEX(GROUP_CONCAT(r.run_id ORDER BY r.created_at DESC SEPARATOR '|||'), '|||', 1) AS latest_run_id,
                    SUBSTRING_INDEX(GROUP_CONCAT(COALESCE(r.requirement, '') ORDER BY r.created_at DESC SEPARATOR '|||'), '|||', 1) AS requirement,
                    SUBSTRING_INDEX(GROUP_CONCAT(COALESCE(r.requirement, '') ORDER BY r.created_at ASC SEPARATOR '|||'), '|||', 1) AS first_requirement
                FROM run_records r
                LEFT JOIN sessions s ON s.session_id = r.session_id
                WHERE r.session_id IS NOT NULL AND r.session_id != ''
                GROUP BY r.session_id, s.title
                ORDER BY last_run_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            for row in rows:
                row["run_id"] = row.get("session_id")
                row["record_type"] = "session"
                row["quality_score"] = float(row.get("quality_score") or 0)
                row["total_tokens"] = int(row.get("total_tokens") or 0)
                row["api_tokens"] = int(row.get("api_tokens") or 0)
                row["local_tokens"] = int(row.get("local_tokens") or 0)
                row["run_count"] = int(row.get("run_count") or 0)
                row["success_count"] = int(row.get("success_count") or 0)
                row["failed_count"] = int(row.get("failed_count") or 0)
                row["success"] = bool(row.get("success"))
            return rows

def get_run_session_detail(session_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.session_id,
                    COALESCE(NULLIF(s.title, ''), '新对话') AS title,
                    COUNT(*) AS run_count,
                    SUM(IF(r.success=1, 1, 0)) AS success_count,
                    SUM(IF(r.success=1, 0, 1)) AS failed_count,
                    IF(SUM(IF(r.success=1, 0, 1)) = 0, 1, 0) AS success,
                    AVG(r.quality_score) AS quality_score,
                    SUM(r.total_tokens) AS total_tokens,
                    SUM(r.api_tokens) AS api_tokens,
                    SUM(r.local_tokens) AS local_tokens,
                    IF(SUM(r.total_tokens) > 0, 'mixed', 'none') AS token_source,
                    MIN(r.created_at) AS first_run_at,
                    MAX(r.updated_at) AS last_run_at,
                    MAX(r.created_at) AS created_at,
                    SUBSTRING_INDEX(GROUP_CONCAT(r.run_id ORDER BY r.created_at DESC SEPARATOR '|||'), '|||', 1) AS latest_run_id,
                    SUBSTRING_INDEX(GROUP_CONCAT(COALESCE(r.requirement, '') ORDER BY r.created_at DESC SEPARATOR '|||'), '|||', 1) AS requirement,
                    SUBSTRING_INDEX(GROUP_CONCAT(COALESCE(r.requirement, '') ORDER BY r.created_at ASC SEPARATOR '|||'), '|||', 1) AS first_requirement
                FROM run_records r
                LEFT JOIN sessions s ON s.session_id = r.session_id
                WHERE r.session_id=%s
                GROUP BY r.session_id, s.title
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            row["run_id"] = row.get("session_id")
            row["record_type"] = "session"
            row["quality_score"] = float(row.get("quality_score") or 0)
            row["total_tokens"] = int(row.get("total_tokens") or 0)
            row["api_tokens"] = int(row.get("api_tokens") or 0)
            row["local_tokens"] = int(row.get("local_tokens") or 0)
            row["run_count"] = int(row.get("run_count") or 0)
            row["success_count"] = int(row.get("success_count") or 0)
            row["failed_count"] = int(row.get("failed_count") or 0)
            row["success"] = bool(row.get("success"))
            row["events"] = get_run_session_events(session_id)
            return row

def get_run_session_events(session_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM run_records WHERE session_id=%s ORDER BY created_at ASC, run_id ASC",
                (session_id,),
            )
            runs = cursor.fetchall()
            cursor.execute(
                "SELECT id, role, content, type, routed_by, metadata_json, created_at FROM messages WHERE session_id=%s ORDER BY created_at ASC, id ASC",
                (session_id,),
            )
            messages = cursor.fetchall()
            run_ids = [r["run_id"] for r in runs]
            events_by_run = {}
            if run_ids:
                placeholders = ",".join(["%s"] * len(run_ids))
                cursor.execute(
                    f"SELECT * FROM run_events WHERE run_id IN ({placeholders}) ORDER BY created_at ASC, id ASC",
                    tuple(run_ids),
                )
                for event in cursor.fetchall():
                    events_by_run.setdefault(event.get("run_id"), []).append(event)

    session_events = []
    order = 0

    def add_event(event):
        nonlocal order
        event["_order"] = order
        order += 1
        session_events.append(event)

    for msg in messages:
        role = msg.get("role")
        msg_type = msg.get("type") or "message"
        routed_by = msg.get("routed_by")
        is_user = role == "user"
        status = "ERROR" if msg_type == "error" else "SUCCESS"
        detail = {
            "input_payload" if is_user else "output_payload": {
                "role": role,
                "type": msg_type,
                "routed_by": routed_by,
                "content": msg.get("content"),
            }
        }
        metadata = _distill_json_load(msg.get("metadata_json"))
        if metadata:
            detail["metadata"] = metadata
        add_event({
            "id": f"MSG_{msg.get('id')}",
            "run_id": f"SESSION_{session_id}",
            "event_type": "USER_MESSAGE" if is_user else "AGENT_MESSAGE",
            "agent": "User" if is_user else (routed_by or "天韬（SkyT）"),
            "status": status,
            "message": msg.get("content") or "",
            "detail_json": json.dumps(detail, ensure_ascii=False),
            "duration_ms": 0,
            "created_at": msg.get("created_at"),
        })

    for run in runs:
        run_detail = {
            "input_payload": {
                "run_id": run.get("run_id"),
                "session_id": session_id,
                "requirement": run.get("requirement"),
            },
            "token_usage": {
                "api_tokens": int(run.get("api_tokens") or 0),
                "local_tokens": int(run.get("local_tokens") or 0),
                "total_tokens": int(run.get("total_tokens") or 0),
                "source": run.get("token_source") or "none",
            },
        }
        add_event({
            "id": f"{run.get('run_id')}_START",
            "run_id": run.get("run_id"),
            "event_type": "RUN_START",
            "agent": "RunSession",
            "status": "SUCCESS",
            "message": f"开始执行：{run.get('requirement') or run.get('run_id')}",
            "detail_json": json.dumps(run_detail, ensure_ascii=False),
            "duration_ms": 0,
            "created_at": run.get("created_at"),
        })
        for event in events_by_run.get(run.get("run_id"), []):
            event = dict(event)
            event["id"] = f"{event.get('run_id')}_{event.get('id')}"
            add_event(event)
        add_event({
            "id": f"{run.get('run_id')}_END",
            "run_id": run.get("run_id"),
            "event_type": "RUN_END",
            "agent": "RunSession",
            "status": "SUCCESS" if run.get("success") else "ERROR",
            "message": f"执行结束：{'成功' if run.get('success') else '失败或未完成'}，质量 {run.get('quality_score')}/10",
            "detail_json": json.dumps({
                "output_payload": {
                    "run_id": run.get("run_id"),
                    "success": bool(run.get("success")),
                    "quality_score": float(run.get("quality_score") or 0),
                },
                "token_usage": run_detail["token_usage"],
            }, ensure_ascii=False),
            "duration_ms": 0,
            "created_at": run.get("updated_at") or run.get("created_at"),
        })

    def event_sort_key(ev):
        value = ev.get("created_at")
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        return (str(value or ""), ev.get("_order") or 0)

    session_events.sort(key=event_sort_key)
    for event in session_events:
        event.pop("_order", None)
    return session_events

def get_run_events(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM run_events WHERE run_id=%s ORDER BY created_at ASC, id ASC", (run_id,))
            return cursor.fetchall()

# --- Reports ---
def save_report(title: str, content: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO reports (title, content) VALUES (%s, %s)", (title, content))
            return cursor.lastrowid

def get_reports(limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, created_at, content FROM reports ORDER BY created_at DESC LIMIT %s", (limit,))
            return cursor.fetchall()

def get_report_by_id(report_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, created_at, content FROM reports WHERE id=%s", (report_id,))
            return cursor.fetchone()

# --- 天韬（SkyT） Data Distillation ---
DISTILL_FULL_KEEP_TYPES = {"TOKEN_USAGE"}
DISTILL_IMPORTANT_TYPES = {
    "LLM_INFERENCE",
    "LLM_PLAN",
    "LLM_THINK",
    "LLM_REFLECTION",
    "WORKFLOW_NODE",
    "TOOL_CALL",
    "CODE_GEN",
    "NPU_ACTION",
}
DISTILL_REDUNDANT_TYPES = {"EXECUTION_STEP", "SYSTEM_LOG"}
DISTILL_PRESERVE_KEYS = {
    "token_usage",
    "model_info",
    "execution_step",
    "input_payload",
    "output_payload",
    "distillation",
}

def _distill_preview(value, limit: int = 700):
    if value is None:
        return None
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except Exception:
            value = str(value)
    value = value.replace("\\n", "\n").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n... [distilled, original_chars={len(value)}]"

def _distill_json_load(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def _summarize_event_detail(event):
    raw = event.get("detail_json") or ""
    detail = _distill_json_load(raw)
    original_bytes = len(raw.encode("utf-8"))
    compact = {
        "distillation": {
            "distilled": True,
            "strategy": "time_for_space",
            "summary": event.get("message") or event.get("event_type") or "运行事件已压缩",
            "original_bytes": original_bytes,
            "preserved_fields": [],
        }
    }

    if isinstance(detail, dict):
        for key in ("token_usage", "model_info", "execution_step"):
            if key in detail:
                compact[key] = detail[key]
                compact["distillation"]["preserved_fields"].append(key)

        input_payload = detail.get("input_payload")
        if input_payload is not None:
            compact["input_payload"] = {"summary": _distill_preview(input_payload, 500)}
            compact["distillation"]["preserved_fields"].append("input_payload.summary")

        output_payload = detail.get("output_payload")
        if output_payload is not None:
            compact["output_payload"] = {"summary": _distill_preview(output_payload, 900)}
            compact["distillation"]["preserved_fields"].append("output_payload.summary")

        for legacy_key in ("args", "arguments", "result", "reply", "preview", "code_preview", "error", "stdout", "stderr"):
            if legacy_key in detail:
                target = "input_payload" if legacy_key in ("args", "arguments") else "output_payload"
                compact.setdefault(target, {})[legacy_key] = _distill_preview(detail[legacy_key], 700)
                compact["distillation"]["preserved_fields"].append(f"{target}.{legacy_key}")
    else:
        compact["output_payload"] = {"summary": _distill_preview(raw, 900)}
        compact["distillation"]["preserved_fields"].append("output_payload.summary")

    return json.dumps(compact, ensure_ascii=False)

def _should_distill_event(event, raw_size: int) -> bool:
    if raw_size == 0:
        return False
    if event.get("event_type") in DISTILL_FULL_KEEP_TYPES:
        return False
    if event.get("status") in ("FAILED", "ERROR"):
        return raw_size > 6000
    if event.get("event_type") in DISTILL_REDUNDANT_TYPES:
        return raw_size > 600
    if event.get("event_type") in DISTILL_IMPORTANT_TYPES:
        return raw_size > 1800
    return raw_size > 1000

def distill_run_data(run_id: str, distilled_summary: str = None):
    """
    天韬（SkyT）·演进：以时间换空间。后台花少量处理时间，将长上下文、多 Agent
    产生的冗余中间日志压缩为可回放摘要，换取数据库长期轻量、可维护。
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, event_type, agent, status, message, detail_json, duration_ms FROM run_events WHERE run_id=%s", (run_id,))
            rows = cursor.fetchall()
            updates = []
            space_saved = 0
            preserved_types = set()
            distilled_types = set()

            for row in rows:
                detail_json = row.get("detail_json") or ""
                if not detail_json:
                    continue
                raw_size = len(detail_json.encode("utf-8"))
                if not _should_distill_event(row, raw_size):
                    preserved_types.add(row.get("event_type") or "UNKNOWN")
                    continue
                compact_detail = _summarize_event_detail(row)
                compact_size = len(compact_detail.encode("utf-8"))
                if compact_size >= raw_size:
                    preserved_types.add(row.get("event_type") or "UNKNOWN")
                    continue
                updates.append((compact_detail, row["id"]))
                space_saved += raw_size - compact_size
                distilled_types.add(row.get("event_type") or "UNKNOWN")
            
            if space_saved < 1024:
                return 0
                
            cursor.execute("SELECT requirement FROM run_records WHERE run_id=%s", (run_id,))
            req_row = cursor.fetchone()
            requirement = req_row['requirement'] if req_row else "Unknown"
            
            if not distilled_summary:
                distilled_summary = (
                    f"天韬（SkyT）数据蒸馏完成：以时间换空间，压缩 {round(space_saved/1024, 2)}KB 冗余中间日志。"
                    f" 保留核心事件类型：{', '.join(sorted(preserved_types)) or '无'}；"
                    f" 降维事件类型：{', '.join(sorted(distilled_types)) or '无'}。"
                    " 深度回放仍保留任务主线、Token、I/O 摘要、错误与关键产物。"
                )
            
            cursor.execute(
                "INSERT INTO distilled_knowledge (run_id, requirement, distilled_content, space_saved_bytes) VALUES (%s, %s, %s, %s)",
                (run_id, requirement, distilled_summary, space_saved)
            )
            
            # 不粗暴清空 detail_json：压缩写回轻量摘要，保留深度回放可读性。
            if updates:
                cursor.executemany("UPDATE run_events SET detail_json = %s WHERE id=%s", updates)
            return space_saved

# --- Advanced Analytics ---
def get_run_detail(run_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM run_records WHERE run_id=%s", (run_id,))
            run = cursor.fetchone()
            if not run:
                return None
            cursor.execute("SELECT * FROM run_events WHERE run_id=%s ORDER BY created_at ASC", (run_id,))
            events = cursor.fetchall()
            run["events"] = events
            return run

def get_skill_usage_stats():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent, event_type, COUNT(*) as count FROM run_events GROUP BY agent, event_type ORDER BY count DESC")
            return cursor.fetchall()

# --- Workflows and Agents ---
DEFAULT_AGENT_META = {
    "AiMultiAgentCore": {
        "name": "天韬（SkyT） 深思节点",
        "description": "负责复杂问题拆解、架构推理、反思校验与最终决策。",
        "color": "#b142ff",
        "icon": "brain",
    },
    "NPU": {
        "name": "NPU 高速节点",
        "description": "处理轻量结构化任务、意图命中、系统状态读取等快速动作。",
        "color": "#1a73e8",
        "icon": "zap",
    },
    "GPU": {
        "name": "GPU 本地生成节点",
        "description": "使用本地模型进行生成、改写、拟人化表达和快速草稿输出。",
        "color": "#0f9d58",
        "icon": "sparkles",
    },
    "WebSearch": {
        "name": "联网搜索节点",
        "description": "负责搜索资料、核验事实、整理引用信息。",
        "color": "#4facfe",
        "icon": "search",
    },
    "ProductAgent": {
        "name": "产品经理节点",
        "description": "负责需求分析、用户故事、范围控制和任务拆解。",
        "color": "#ffb347",
        "icon": "user",
    },
    "CoderAgent": {
        "name": "程序员节点",
        "description": "负责实现方案、代码编写、重构和工程落地。",
        "color": "#00c781",
        "icon": "code",
    },
    "TesterAgent": {
        "name": "测试员节点",
        "description": "负责测试计划、用例设计、运行验证和缺陷反馈。",
        "color": "#ff6b6b",
        "icon": "shield",
    },
}

DEFAULT_AGENT_META.update({
    "RequirementAgent": {
        "name": "需求理解 Agent",
        "description": "提取用户目标、约束、角色、验收标准和需要确认的问题。",
        "color": "#ffb347",
        "icon": "user",
        "stage": "analysis",
        "inputFields": ["requirement"],
        "outputFields": ["requirement_summary", "acceptance_criteria", "success"],
    },
    "ArchitectureAgent": {
        "name": "架构规划 Agent",
        "description": "把需求拆成模块、文件结构、数据流、接口和风险边界。",
        "color": "#38bdf8",
        "icon": "brain",
        "stage": "analysis",
        "inputFields": ["requirement_summary"],
        "outputFields": ["architecture_plan", "module_plan", "success"],
    },
    "ContextCompressorAgent": {
        "name": "上下文压缩 Agent",
        "description": "用本地 GPU 思路整理历史、文件、用户输入，减少 API 无效 Token。",
        "color": "#22c55e",
        "icon": "sparkles",
        "stage": "analysis",
        "inputFields": ["raw_context"],
        "outputFields": ["compressed_context", "success"],
    },
    "GPUDraftAgent": {
        "name": "本地 GPU 草稿 Agent",
        "description": "先生成低成本草稿、Markdown 归档或上下文摘要，再交给 API 深化。",
        "color": "#0f9d58",
        "icon": "sparkles",
        "stage": "generation",
        "inputFields": ["compressed_context"],
        "outputFields": ["gpu_draft", "has_code_blocks", "success"],
    },
    "APIDeepGenerateAgent": {
        "name": "API 深度生成 Agent",
        "description": "基于 GPU 草稿和高价值上下文生成高质量方案或可确认计划。",
        "color": "#8ab4f8",
        "icon": "brain",
        "stage": "generation",
        "inputFields": ["gpu_draft", "compressed_context"],
        "outputFields": ["api_plan", "success"],
    },
    "CodeGenerationAgent": {
        "name": "代码生成 Agent",
        "description": "生成带文件名的代码块、补丁或工程文件清单。",
        "color": "#00c781",
        "icon": "code",
        "stage": "implementation",
        "inputFields": ["architecture_plan"],
        "outputFields": ["code_blocks", "file_changes", "has_code_blocks", "success"],
    },
    "FileWriterAgent": {
        "name": "文件落盘 Agent",
        "description": "把代码产物写入绑定工作区，并记录保存文件清单。",
        "color": "#60a5fa",
        "icon": "code",
        "stage": "code_ops",
        "nodeType": "code_agent",
        "inputFields": ["code_blocks"],
        "outputFields": ["saved_files", "success"],
    },
    "DependencyInstallerAgent": {
        "name": "依赖安装 Agent",
        "description": "分析项目依赖并给出安装/启动前置步骤。",
        "color": "#f97316",
        "icon": "zap",
        "stage": "execution",
        "inputFields": ["saved_files"],
        "outputFields": ["install_result", "success"],
    },
    "TestValidationAgent": {
        "name": "测试验证 Agent",
        "description": "运行或设计构建检查、语法检查、手动验收和回归验证。",
        "color": "#ff6b6b",
        "icon": "shield",
        "stage": "testing",
        "inputFields": ["saved_files", "install_result"],
        "outputFields": ["test_result", "test_success", "success"],
    },
    "PreviewDeployAgent": {
        "name": "本地预览部署 Agent",
        "description": "扫描工作区、启动本地服务，并把 localhost 地址推送到右侧浏览器。",
        "color": "#4facfe",
        "icon": "zap",
        "stage": "execution",
        "inputFields": ["test_result"],
        "outputFields": ["preview_url", "success"],
    },
    "ReplayRecorderAgent": {
        "name": "Replay 记录 Agent",
        "description": "整理运行事件、I/O Payload、Token 和分支路径，服务深度回放展示。",
        "color": "#a78bfa",
        "icon": "merge",
        "stage": "analysis",
        "inputFields": ["workflow_events"],
        "outputFields": ["replay_summary", "success"],
    },
    "ReportSummaryAgent": {
        "name": "Report 总结 Agent",
        "description": "生成比赛展示用 Markdown 报告、交付摘要和后续优化建议。",
        "color": "#facc15",
        "icon": "sparkles",
        "stage": "analysis",
        "inputFields": ["final_context"],
        "outputFields": ["report_markdown", "success"],
    },
    "SafetyReviewAgent": {
        "name": "安全风险检查 Agent",
        "description": "检查危险命令、工作区边界、密钥文件和需要用户确认的动作。",
        "color": "#ef4444",
        "icon": "shield",
        "stage": "testing",
        "inputFields": ["planned_actions"],
        "outputFields": ["risk_notes", "approved", "success"],
    },
})

def _workflow_template_summary(row: dict) -> dict:
    result = dict(row)
    workflow_json = result.pop("workflow_json", None)
    try:
        data = json.loads(workflow_json) if workflow_json else {}
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        meta = data.get("meta") or {}
        result.update({
            "node_count": len(nodes),
            "edge_count": len(edges),
            "demo_scene": meta.get("demo_scene", ""),
            "recommended_user_prompt": meta.get("recommended_user_prompt", ""),
            "expected_outputs": meta.get("expected_outputs", []),
            "replay_highlights": meta.get("replay_highlights", []),
            "report_highlights": meta.get("report_highlights", []),
            "competition_demo_value": meta.get("competition_demo_value", ""),
            "suitable_for_live_demo": meta.get("suitable_for_live_demo", False),
            "estimated_complexity": meta.get("estimated_complexity", ""),
            "whether_api_needed": bool(meta.get("whether_api_needed", False)),
            "whether_gpu_needed": bool(meta.get("whether_gpu_needed", False)),
            "requires_workspace": bool(meta.get("requires_workspace", False)),
            "artifact_policy": meta.get("artifact_policy", {}),
            "preview_policy": meta.get("preview_policy", {}),
            "official_seed_version": meta.get("official_seed_version", 0),
            "token_cost_notes": meta.get("token_cost_notes", ""),
            "risk_notes": meta.get("risk_notes", ""),
            "node_list": meta.get("node_list", []),
            "edge_list": meta.get("edge_list", []),
        })
    except Exception:
        result.update({
            "node_count": 0,
            "edge_count": 0,
            "demo_scene": "",
            "recommended_user_prompt": "",
            "whether_api_needed": False,
            "whether_gpu_needed": False,
            "requires_workspace": False,
            "artifact_policy": {},
            "preview_policy": {},
            "official_seed_version": 0,
        })
    return result

def get_workflow_templates():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT template_id, title, description, stage, tags, author, workflow_json, created_at, updated_at FROM workflow_templates ORDER BY created_at DESC")
            return [_workflow_template_summary(row) for row in cursor.fetchall()]

def get_workflow_template(template_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM workflow_templates WHERE template_id=%s", (template_id,))
            row = cursor.fetchone()
            if not row:
                return row
            summary = _workflow_template_summary(row)
            row.update({k: v for k, v in summary.items() if k not in row})
            return row

def save_workflow_template(template_id: str, title: str, description: str, stage: str, tags: str, author: str, workflow_json: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO workflow_templates (template_id, title, description, stage, tags, author, workflow_json) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE title=%s, description=%s, stage=%s, tags=%s, author=%s, workflow_json=%s",
                (template_id, title, description, stage, tags, author, workflow_json, title, description, stage, tags, author, workflow_json)
            )

def get_agents():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id, name, description, color, icon FROM agents ORDER BY id ASC")
            rows = cursor.fetchall()
            normalized = []
            seen = set()
            for row in rows:
                agent_id = row.get("agent_id")
                seen.add(agent_id)
                meta = DEFAULT_AGENT_META.get(agent_id, {})
                normalized.append({
                    **row,
                    **meta,
                    "agent_id": agent_id,
                })

            for agent_id, meta in DEFAULT_AGENT_META.items():
                if agent_id not in seen:
                    normalized.append({"agent_id": agent_id, **meta})

            return normalized

# --- Dashboard Stats ---
def get_dashboard_stats():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total_runs, SUM(IF(success=1, 1, 0)) as success_runs, AVG(quality_score) as avg_quality FROM run_records")
            run_stats = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_reports FROM reports")
            report_stats = cursor.fetchone()
            
            # Count recent events by agent
            cursor.execute("SELECT agent, COUNT(*) as count FROM run_events GROUP BY agent ORDER BY count DESC LIMIT 10")
            events_by_agent = cursor.fetchall()
            
            # Calculate total space saved by 天韬（SkyT） distillation
            cursor.execute("SELECT SUM(space_saved_bytes) as total_saved FROM distilled_knowledge")
            saved_row = cursor.fetchone()
            total_saved_kb = round(float(saved_row['total_saved'] or 0) / 1024, 1)

            return {
                "totalRuns": run_stats['total_runs'] or 0,
                "successRuns": run_stats['success_runs'] or 0,
                "failedRuns": (run_stats['total_runs'] or 0) - (run_stats['success_runs'] or 0),
                "averageQualityScore": round(float(run_stats['avg_quality'] or 0), 1),
                "totalReports": report_stats['total_reports'] or 0,
                "eventsByAgent": events_by_agent,
                "spaceSavedKb": total_saved_kb
            }

# Initialize DB when this module is imported
try:
    init_db()
except Exception as e:
    print(f"Warning: Failed to initialize database: {e}")
