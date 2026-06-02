import os
import json
import pymysql
import pymysql.cursors
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import threading
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
OFFICIAL_WORKFLOW_SEED_VERSION = 3

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

def _workflow_edge(edge_id, source, target, label=""):
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": "smoothstep",
        "label": label,
        "markerEnd": {"type": "arrowclosed", "width": 18, "height": 18},
        "style": {"strokeWidth": 2},
    }

def _build_competition_workflow_template(template_id, title, description, demo_scene, recommended_prompt, nodes_def, meta):
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
    edges = [
        _workflow_edge(f"{template_id}_e{idx}", nodes[idx - 1]["id"], nodes[idx]["id"], f"{idx} -> {idx + 1}")
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
            "author": "Ai Multi Agent System",
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
                    "competition_demo_value": "最直观展示 Ai Multi Agent 能把复杂代码任务拆成可执行、可回放的多节点流程。",
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
            ),
        },
        {
            "template_id": "tmpl_competition_docs_pipeline",
            "title": "项目文档整理流水线",
            "description": "读取并压缩项目资料，生成维护文档和历史工作记录，展示 Ai Multi Agent 的项目记忆能力。",
            "stage": "Published",
            "tags": "Competition,Docs,Markdown,Memory",
            "author": "Ai Multi Agent System",
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
                    "competition_demo_value": "体现 Ai Multi Agent 能为长期项目维护和 vibe coding 保留可复用项目记忆。",
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
            "author": "Ai Multi Agent System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_bugfix_pipeline",
                "问题定位与修复流水线",
                "展示 Ai Multi Agent 如何从用户描述出发，逐步定位问题并给出最小修复方案。",
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
                    "competition_demo_value": "体现 Ai Multi Agent 不是乱改代码，而是可观察地定位、分析、修复和验证。",
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
            "author": "Ai Multi Agent System",
            "workflow_json": _build_competition_workflow_template(
                "tmpl_competition_demo_enhance_pipeline",
                "比赛演示增强流水线",
                "把比赛展示优化拆成目标、视觉层级、交互简化、路径和讲解词。",
                "用户希望优化页面视觉效果、展示路径或比赛讲解效果。",
                "请帮我优化 Ai Multi Agent 工作流页面的比赛展示路径，让评委快速看懂多 Agent 协作价值。",
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
            "author": "Ai Multi Agent System",
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
                    "competition_demo_value": "最能体现 Ai Multi Agent 的系统级优势：本地 GPU 辅助 API，而不是替代 API。",
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
            
            # Seed default agents if empty
            cursor.execute("SELECT COUNT(*) as count FROM agents")
            row = cursor.fetchone()
            if row['count'] == 0:
                default_agents = [
                    ('AiMultiAgentCore', 'Ai Multi Agent 深思', '深度反思与博弈，负责最复杂逻辑推演', '#b142ff', 'brain'),
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
                        ("AiMultiAgentCore", "Ai Multi Agent 深思", "深度反思与博弈，负责最复杂逻辑推演", legacy_agent_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE agents SET name=%s, description=%s WHERE agent_id=%s OR name LIKE %s",
                        ("Ai Multi Agent 深思", "深度反思与博弈，负责最复杂逻辑推演", "AiMultiAgentCore", f"%{legacy_name}%")
                    )
                
            # Seed default workflow template if empty
            cursor.execute("SELECT COUNT(*) as count FROM workflow_templates")
            row = cursor.fetchone()
            if row['count'] == 0:
                default_wf = '{"nodes":[{"id":"node_1","type":"default","position":{"x":100,"y":100},"data":{"label":"AiMultiAgentCore","name":"Ai Multi Agent 深思"},"style":{"border":"2px solid #b142ff"}}],"edges":[]}'
                cursor.execute(
                    "INSERT INTO workflow_templates (template_id, title, description, stage, tags, author, workflow_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    ("tmpl_default_1", "标准深思流", "默认的 Ai Multi Agent 深度思考工作流", "Published", "Official,Default", "Ai Multi Agent System", default_wf)
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
            official_authors = {"Ai Multi Agent System", legacy_author}
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
            cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))

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

def get_run_records(limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM run_records ORDER BY created_at DESC LIMIT %s", (limit,))
            return cursor.fetchall()

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

# --- Ai Multi Agent Data Distillation ---
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
    Ai Multi Agent·演进：以时间换空间。后台花少量处理时间，将长上下文、多 Agent
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
                    f"Ai Multi Agent数据蒸馏完成：以时间换空间，压缩 {round(space_saved/1024, 2)}KB 冗余中间日志。"
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
        "name": "Ai Multi Agent 深思节点",
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
            
            # Calculate total space saved by Ai Multi Agent distillation
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
