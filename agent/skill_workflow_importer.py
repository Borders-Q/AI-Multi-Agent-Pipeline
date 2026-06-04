import hashlib
import json
import re
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def slugify(value: str, fallback: str = "workflow") -> str:
    source = value or fallback
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", source).strip("-").lower()
    if len(slug) >= 3:
        return slug[:64].strip("-")
    digest = hashlib.sha1(source.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{fallback}-{digest}"


def _node(
    node_id: str,
    label: str,
    agent_id: str,
    node_type: str,
    x: int,
    y: int,
    *,
    role: str = "",
    description: str = "",
    instruction: str = "",
    stage: str = "custom",
    color: str = "#4da3ff",
    icon: str = "sparkles",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    extra_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = {
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
    }
    if extra_data:
        data.update(extra_data)
    return {
        "id": node_id,
        "type": "customAgent",
        "position": {"x": x, "y": y},
        "data": data,
    }


def _edge(edge_id: str, source: str, target: str, *, label: str = "", edge_type: str = "control", condition: str = "") -> dict[str, Any]:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": "smoothstep",
        "markerEnd": {"type": "arrowclosed", "width": 18, "height": 18},
        "style": {"strokeWidth": 2},
        "data": {
            "edgeType": edge_type,
            "condition": condition,
            "label": label,
            "fromOutputField": "",
            "toInputField": "",
            "loopPolicy": {"maxIterations": 0},
        },
    }


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_frontmatter(markdown: str) -> dict[str, str]:
    match = re.match(r"(?s)^\s*---\s*\n(?P<body>.*?)\n---", markdown or "")
    if not match:
        return {}
    meta: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip("'\"")
    return meta


def _extract_skill_steps(markdown: str) -> list[str]:
    steps: list[str] = []
    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{2,4}\s*(?:\d+[.、]\s*)?(.+)$", stripped)
        if heading and ("Agent" in heading.group(1) or "节点" in heading.group(1)):
            steps.append(heading.group(1).strip())
            continue
        numbered = re.match(r"^\d+[.、]\s*(.+)$", stripped)
        if numbered and len(numbered.group(1)) <= 80:
            steps.append(numbered.group(1).strip())
    cleaned: list[str] = []
    seen = set()
    for step in steps:
        step = re.sub(r"[`*_]+", "", step).strip()
        if step and step not in seen:
            cleaned.append(step)
            seen.add(step)
        if len(cleaned) >= 6:
            break
    return cleaned


def _workflow_from_markdown(markdown: str, title: str, description: str, source_name: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    steps = _extract_skill_steps(markdown)
    if not steps:
        steps = ["需求理解 Agent", "Skill 流程执行 Agent", "结果总结 Agent"]
        warnings.append("未在 SKILL.md 中识别到明确节点，已生成三段式兜底工作流。")

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        node_id = f"skill_step_{index + 1}"
        nodes.append(_node(
            node_id,
            step,
            "custom_agent",
            "custom_agent",
            160 + index * 300,
            120,
            role="Trec/SOLO Skill 流程节点",
            description=f"从 {source_name} 的 SKILL.md 解析得到的执行步骤。",
            instruction=f"严格按导入 Skill 的步骤完成：{step}",
            stage="custom",
            color="#94a3b8",
            icon="sparkles",
            inputs=["skill_context"],
            outputs=[f"step_{index + 1}_result"],
        ))
        if index > 0:
            edges.append(_edge(f"edge_{index}", f"skill_step_{index}", node_id))

    workflow = {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "template_name": title,
            "description": description,
            "demo_scene": "从 Trec/SOLO Skill 导入并恢复为 Ai Multi Agent 工作流模板。",
            "recommended_user_prompt": "按导入的 Skill 流程执行本次任务。",
            "expected_outputs": ["恢复后的工作流模板", "可编辑节点", "可运行回放记录"],
            "imported_from": "trae_skill_markdown",
            "source_file": source_name,
        },
    }
    return workflow, warnings


def _ensure_workflow_meta(workflow: dict[str, Any], title: str, description: str, source_name: str) -> dict[str, Any]:
    workflow = dict(workflow or {})
    workflow.setdefault("nodes", [])
    workflow.setdefault("edges", [])
    meta = dict(workflow.get("meta") or {})
    meta.setdefault("template_name", title)
    meta.setdefault("description", description)
    meta.setdefault("imported_from", "trae_skill_workflow_json")
    meta.setdefault("source_file", source_name)
    meta.setdefault("imported_at", datetime.now().isoformat(timespec="seconds"))
    workflow["meta"] = meta
    return workflow


def import_trae_skill_to_template(file_name: str, content: bytes, template_id: str = "", title_override: str = "") -> dict[str, Any]:
    warnings: list[str] = []
    source_name = file_name or "trae-skill"
    workflow_json_text = ""
    skill_md = ""

    if zipfile.is_zipfile(BytesIO(content)):
        with zipfile.ZipFile(BytesIO(content)) as zf:
            names = [name for name in zf.namelist() if not name.endswith("/")]
            workflow_name = next((name for name in names if name.lower().endswith("workflow.json")), "")
            skill_name = next((name for name in names if name.lower().endswith("skill.md")), "")
            if workflow_name:
                workflow_json_text = _decode_text(zf.read(workflow_name))
            if skill_name:
                skill_md = _decode_text(zf.read(skill_name))
            if not workflow_json_text and not skill_md:
                raise ValueError("Trec/SOLO Skill zip 中未找到 workflow.json 或 SKILL.md")
    else:
        raw_text = _decode_text(content)
        if source_name.lower().endswith(".json") or raw_text.lstrip().startswith("{"):
            workflow_json_text = raw_text
        else:
            skill_md = raw_text

    frontmatter = _parse_frontmatter(skill_md)
    raw_title = title_override or frontmatter.get("name") or ""
    raw_desc = frontmatter.get("description") or "从 Trec/SOLO Skill 导入的工作流模板"

    if workflow_json_text:
        try:
            workflow = json.loads(workflow_json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"workflow.json 不是有效 JSON: {exc}") from exc
        meta = workflow.get("meta") or {}
        title = raw_title or _text(meta.get("template_name") or meta.get("title"), "Imported Trec/SOLO Skill Workflow")
        description = raw_desc or _text(meta.get("description"), "从 Trec/SOLO Skill workflow.json 导入")
        workflow = _ensure_workflow_meta(workflow, title, description, source_name)
    else:
        title = raw_title or "Imported Trec/SOLO Skill Workflow"
        description = raw_desc
        workflow, md_warnings = _workflow_from_markdown(skill_md, title, description, source_name)
        warnings.extend(md_warnings)

    resolved_id = template_id or f"tmpl_imported_skill_{slugify(title, 'skill')}"
    workflow["meta"]["template_id"] = resolved_id
    workflow["meta"]["template_name"] = title
    workflow["meta"]["description"] = description
    workflow_text = json.dumps(workflow, ensure_ascii=False, indent=2)

    return {
        "template_id": resolved_id,
        "title": title,
        "description": description,
        "workflow_json": workflow_text,
        "workflow": workflow,
        "warnings": warnings,
    }


def tool_schema_to_workflow_template(tool: dict[str, Any], template_id: str = "") -> dict[str, Any]:
    function = tool.get("function") or tool
    skill_name = _text(function.get("name"), "custom_tool")
    description = _text(function.get("description"), f"调用系统技能 {skill_name}")
    params = function.get("parameters") or {"type": "object", "properties": {}}
    slug = slugify(skill_name, "skill")
    resolved_id = template_id or f"tmpl_skill_{slug}"

    nodes = [
        _node(
            "skill_requirement",
            "需求整理 Agent",
            "ProductAgent",
            "agent",
            120,
            140,
            role="需求整理者",
            description="把用户输入整理成工具可消费的参数线索。",
            instruction="提取用户意图、必要参数、约束和输出格式。",
            stage="analysis",
            color="#ffb347",
            icon="user",
            inputs=["requirement"],
            outputs=["tool_context"],
        ),
        _node(
            "skill_tool_call",
            f"{skill_name} 技能调用 Agent",
            f"skill:{skill_name}",
            "tool_skill",
            440,
            140,
            role="系统技能执行者",
            description=description,
            instruction=f"根据上游整理结果调用系统技能 `{skill_name}`，并把结构化结果交给下游总结。",
            stage="execution",
            color="#60a5fa",
            icon="wrench",
            inputs=["tool_context"],
            outputs=["tool_result", "success", "status"],
            extra_data={
                "toolSkillConfig": {
                    "name": skill_name,
                    "description": description,
                    "parameters": params,
                }
            },
        ),
        _node(
            "skill_summary",
            "结果总结 Agent",
            "AiMultiAgentCore",
            "agent",
            760,
            140,
            role="结果总结者",
            description="把系统技能输出整理成可读交付内容。",
            instruction="总结工具执行结果、异常、下一步建议，并保持中文输出。",
            stage="analysis",
            color="#b142ff",
            icon="brain",
            inputs=["tool_result"],
            outputs=["final_answer"],
        ),
    ]
    edges = [
        _edge("edge_skill_1", "skill_requirement", "skill_tool_call", label="整理后调用工具"),
        _edge("edge_skill_2", "skill_tool_call", "skill_summary", label="工具结果总结"),
    ]
    workflow = {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "template_id": resolved_id,
            "template_name": f"{skill_name} 技能工作流",
            "description": description,
            "demo_scene": f"把 Skills Store 中的 `{skill_name}` 转换为可编辑、可回放的工作流模板。",
            "recommended_user_prompt": f"使用 {skill_name} 技能完成一个演示任务。",
            "expected_outputs": ["工具调用结果", "结构化总结", "运行历史和深度回放记录"],
            "imported_from": "system_skill",
            "source_skill": skill_name,
            "node_list": [
                {"name": "需求整理 Agent", "responsibility": "整理用户输入"},
                {"name": f"{skill_name} 技能调用 Agent", "responsibility": "调用系统技能"},
                {"name": "结果总结 Agent", "responsibility": "总结结果"},
            ],
        },
    }
    return {
        "template_id": resolved_id,
        "title": f"{skill_name} 技能工作流",
        "description": description,
        "workflow_json": json.dumps(workflow, ensure_ascii=False, indent=2),
        "workflow": workflow,
        "warnings": [],
    }
