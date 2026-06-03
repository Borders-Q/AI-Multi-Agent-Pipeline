import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any


OFFICIAL_TEMPLATE_SLUGS = {
    "tmpl_competition_engineering_pipeline": "ai-engineering-pipeline",
    "tmpl_competition_docs_pipeline": "project-docs-pipeline",
    "tmpl_competition_bugfix_pipeline": "bugfix-replay-pipeline",
    "tmpl_competition_demo_enhance_pipeline": "competition-demo-enhance",
    "tmpl_competition_gpu_api_pipeline": "gpu-api-collaboration",
}


def _load_workflow(workflow_json: Any) -> dict:
    if isinstance(workflow_json, str):
        return json.loads(workflow_json) if workflow_json.strip() else {}
    if isinstance(workflow_json, dict):
        return workflow_json
    return {}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [value]


def _slugify(title: str, template_id: str = "") -> str:
    if template_id in OFFICIAL_TEMPLATE_SLUGS:
        return OFFICIAL_TEMPLATE_SLUGS[template_id]

    source = title or template_id or "workflow-skill"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", source).strip("-").lower()
    if len(slug) >= 3:
        return slug[:64].strip("-")

    digest = hashlib.sha1(source.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"workflow-skill-{digest}"


def _yaml_scalar(value: str) -> str:
    safe = _text(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{safe}"'


def _node_label(node: dict) -> str:
    data = node.get("data") or {}
    return _text(data.get("label") or data.get("name") or node.get("id"), "未命名节点")


def _node_agent(node: dict) -> str:
    data = node.get("data") or {}
    return _text(data.get("agentId") or data.get("agent_id") or data.get("nodeType"), "agent")


def _node_stage(node: dict) -> str:
    data = node.get("data") or {}
    return _text(data.get("stage"), "custom")


def _node_description(node: dict) -> str:
    data = node.get("data") or {}
    return _text(data.get("description") or data.get("role") or data.get("instruction"), "按节点职责完成当前阶段任务。")


def _node_io(node: dict, key: str) -> str:
    data = node.get("data") or {}
    fields = data.get(key) or []
    if isinstance(fields, str):
        fields = [item.strip() for item in re.split(r"[\n,]", fields) if item.strip()]
    if not fields:
        return "未显式配置"
    return "、".join(str(item) for item in fields)


def _ordered_nodes(workflow: dict) -> list:
    nodes = workflow.get("nodes") or []
    edges = workflow.get("edges") or []
    if not nodes or not edges:
        return nodes

    by_id = {node.get("id"): node for node in nodes}
    incoming = {edge.get("target") for edge in edges}
    starts = [node for node in nodes if node.get("id") not in incoming]
    ordered = []
    seen = set()

    def visit(node: dict):
        node_id = node.get("id")
        if not node_id or node_id in seen:
            return
        seen.add(node_id)
        ordered.append(node)
        for edge in edges:
            if edge.get("source") == node_id and edge.get("target") in by_id:
                visit(by_id[edge.get("target")])

    for start in starts or nodes:
        visit(start)
    for node in nodes:
        if node.get("id") not in seen:
            ordered.append(node)
    return ordered


def build_skill_package(title: str, description: str, workflow_json: Any, template_id: str = "") -> dict:
    workflow = _load_workflow(workflow_json)
    meta = workflow.get("meta") or {}
    final_title = _text(title or meta.get("template_name") or meta.get("title"), "Ai Multi Agent 工作流 Skill")
    final_description = _text(
        description or meta.get("template_description") or meta.get("description") or meta.get("demo_scene"),
        "用于在 Trae 中复用 Ai Multi Agent 工作流模板的项目级 Skill。",
    )
    skill_name = _slugify(final_title, template_id or _text(meta.get("template_id")))
    nodes = _ordered_nodes(workflow)
    edges = workflow.get("edges") or []

    recommended_prompt = _text(meta.get("recommended_user_prompt"), "按当前 Skill 的流程完成用户提出的开发任务。")
    expected_outputs = _as_list(meta.get("expected_outputs"))
    replay_highlights = _as_list(meta.get("replay_highlights"))
    report_highlights = _as_list(meta.get("report_highlights"))
    requires_workspace = bool(meta.get("requires_workspace", False))
    whether_gpu_needed = bool(meta.get("whether_gpu_needed", False))
    whether_api_needed = bool(meta.get("whether_api_needed", False))

    node_lines = []
    for idx, node in enumerate(nodes, start=1):
        node_lines.extend([
            f"### {idx}. {_node_label(node)}",
            f"- Agent Key：`{_node_agent(node)}`",
            f"- 阶段：`{_node_stage(node)}`",
            f"- 职责：{_node_description(node)}",
            f"- 输入：{_node_io(node, 'inputFields')}",
            f"- 输出：{_node_io(node, 'outputFields')}",
            "",
        ])

    execution_steps = [
        "1. 先复述用户需求，并识别是否需要工作区、是否会生成或修改文件。",
        "2. 按“节点分工”顺序执行，不要跳过需求理解、方案规划、实现、验证和总结环节。",
        "3. 如果需要落盘代码，先确认工作区；生成的代码块必须标明目标文件名。",
        "4. 执行过程中只展示用户可理解的步骤摘要，不展示模型隐藏推理链。",
        "5. 最终输出要包含已完成内容、文件清单、验证建议、运行方式和可进入回放/报告的摘要。",
    ]

    skill_md = "\n".join([
        "---",
        f"name: {_yaml_scalar(skill_name)}",
        f"description: {_yaml_scalar(final_description)}",
        "---",
        "",
        f"# {final_title}",
        "",
        "这是由 Ai Multi Agent Workflow Template 一键导出的 Trae 项目级 Skill。它用于把比赛演示中的多 Agent 工作流固化为 Trae 可复用的执行流程。",
        "",
        "## 适用场景",
        _text(meta.get("demo_scene"), final_description),
        "",
        "## 推荐触发方式",
        f"- 在 Trae 中提出类似需求：`{recommended_prompt}`",
        "- 当任务需要按固定多 Agent 流程完成时，优先使用本 Skill。",
        "",
        "## 工作流策略",
        f"- 需要工作区：{'是' if requires_workspace else '否'}",
        f"- 需要本地 GPU：{'是' if whether_gpu_needed else '可选'}",
        f"- 需要云端 API：{'是' if whether_api_needed else '可选'}",
        f"- 节点数量：{len(nodes)}",
        f"- 连线数量：{len(edges)}",
        "",
        "## 节点分工",
        *(node_lines or ["暂无节点。", ""]),
        "## 执行步骤",
        *execution_steps,
        "",
        "## 预期产出",
        *([f"- {item}" for item in expected_outputs] or ["- 可运行或可审查的任务结果。", "- 清晰的验证方式和交付摘要。"]),
        "",
        "## Replay 展示重点",
        *([f"- {item}" for item in replay_highlights] or ["- 展示任务从输入、节点协作到最终输出的过程。"]),
        "",
        "## Report 展示重点",
        *([f"- {item}" for item in report_highlights] or ["- 汇总任务结果、文件产物、风险和后续建议。"]),
        "",
        "## 安全边界",
        "- 生成或修复工程代码前必须确认目标工作区。",
        "- 不要静默执行递归删除、覆盖密钥文件、全局安装、发布、提交或清理非项目进程。",
        "- 不要把内部推理链当作展示内容；只展示用户可理解的执行状态、方案和结果。",
        "- 如果信息不足，先提出最少量关键确认问题，再继续执行。",
        "",
        "## 附带参考",
        "- `workflow.json` 保存了原始 Ai Multi Agent 工作流结构，可用于回看节点和连线。",
        "",
    ])

    workflow_text = json.dumps(workflow, ensure_ascii=False, indent=2)
    return {
        "skill_name": skill_name,
        "skill_dir": skill_name,
        "skill_md": skill_md,
        "workflow_json": workflow_text,
    }


def build_skill_zip(package: dict) -> bytes:
    buffer = io.BytesIO()
    skill_dir = package["skill_dir"]
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{skill_dir}/SKILL.md", package["skill_md"])
        zf.writestr(f"{skill_dir}/workflow.json", package["workflow_json"])
    return buffer.getvalue()


def save_skill_to_workspace(package: dict, workspace: str) -> dict:
    if not workspace:
        raise ValueError("workspace is required")

    workspace_path = Path(workspace).expanduser().resolve()
    target_dir = workspace_path / ".trae" / "skills" / package["skill_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)

    skill_path = target_dir / "SKILL.md"
    workflow_path = target_dir / "workflow.json"
    skill_path.write_text(package["skill_md"], encoding="utf-8")
    workflow_path.write_text(package["workflow_json"], encoding="utf-8")

    return {
        "skill_name": package["skill_name"],
        "target_dir": os.fspath(target_dir),
        "files": [os.fspath(skill_path), os.fspath(workflow_path)],
    }
