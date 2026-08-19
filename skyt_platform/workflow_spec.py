from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any


WORKFLOW_SPEC_VERSION = 2
NODE_KINDS = {
    "planner",
    "researcher",
    "executor",
    "tool",
    "verifier",
    "critic",
    "synthesizer",
    "human_approval",
    "agent",
    "condition",
    "join_and",
    "join_or",
}
MODEL_PROFILES = {"fast", "strong", "critic", "fallback", "auto"}
DEFAULT_POLICY = {
    "max_parallelism": 4,
    "max_retries_per_node": 2,
    "max_replans": 3,
    "max_model_calls": 40,
    "timeout_seconds": 1800,
    "approval_mode": "risk_based",
}
DEFAULT_GATES = [
    {"type": "output_present", "required": True},
    {"type": "evidence_recorded", "required": True},
]


def _parse(value: Any) -> dict:
    if isinstance(value, dict):
        return deepcopy(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"工作流 JSON 无法解析：{exc}") from exc
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("工作流必须是 JSON 对象。")


def _list(value: Any, default: list[str] | None = None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[\n,]", value) if item.strip()]
    return list(default or [])


def _node_kind(data: dict) -> str:
    raw = str(data.get("kind") or data.get("nodeType") or data.get("node_type") or data.get("agentId") or "agent")
    aliases = {
        "code_agent": "executor",
        "tool_skill": "tool",
        "custom_agent": "agent",
        "loop_controller": "agent",
        "branch": "condition",
    }
    return aliases.get(raw, raw if raw in NODE_KINDS else "agent")


def _normalize_node(raw: dict, index: int) -> dict:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    node_id = str(raw.get("id") or data.get("id") or f"node_{index}")
    kind = _node_kind(data)
    agent_id = str(data.get("agentId") or data.get("agent_id") or data.get("agentKey") or kind)
    tools = _list(data.get("tools") or data.get("allowedTools"))
    tool_config = data.get("toolSkillConfig") if isinstance(data.get("toolSkillConfig"), dict) else {}
    if kind == "tool" and tool_config.get("name") and tool_config["name"] not in tools:
        tools.append(str(tool_config["name"]))
    position = raw.get("position") if isinstance(raw.get("position"), dict) else data.get("position", {})
    return {
        "id": node_id,
        "kind": kind,
        "label": str(data.get("label") or data.get("name") or node_id),
        "role": str(data.get("role") or (data.get("customAgentMeta") or {}).get("role") or ""),
        "stage": str(data.get("stage") or "execution"),
        "agent_id": agent_id,
        "description": str(data.get("description") or ""),
        "instruction": str(data.get("instruction") or ""),
        "system_prompt": str(data.get("systemPrompt") or data.get("system_prompt") or ""),
        "model_profile": str(data.get("modelProfile") or data.get("model_profile") or "auto").lower(),
        "tools": tools,
        "input_fields": _list(data.get("inputFields") or data.get("input_fields"), ["task"]),
        "output_fields": _list(data.get("outputFields") or data.get("output_fields"), ["result"]),
        "input_schema": data.get("inputSchema") or data.get("input_schema") or {"type": "object"},
        "output_schema": data.get("outputSchema") or data.get("output_schema") or {"type": "object"},
        "verification": data.get("verification") or {"gates": []},
        "policy": data.get("policy") or {},
        "condition": str(data.get("condition") or ""),
        "repair_for": str(data.get("repair_for") or data.get("repairFor") or ""),
        "position": {"x": position.get("x", index * 280), "y": position.get("y", 100)},
        "legacy_data": deepcopy(data),
    }


def _normalize_edge(raw: dict, index: int) -> dict:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    loop_policy = data.get("loopPolicy") or data.get("loop_policy") or {}
    return {
        "id": str(raw.get("id") or f"edge_{index}"),
        "source": str(raw.get("source") or raw.get("from") or ""),
        "target": str(raw.get("target") or raw.get("to") or ""),
        "type": str(data.get("edgeType") or data.get("edge_type") or raw.get("edgeType") or raw.get("type") or "control"),
        "condition": str(data.get("condition") or raw.get("condition") or ""),
        "label": str(data.get("label") or raw.get("label") or ""),
        "from_output": str(data.get("fromOutputField") or data.get("from_output") or ""),
        "to_input": str(data.get("toInputField") or data.get("to_input") or ""),
        "loop_policy": loop_policy if isinstance(loop_policy, dict) else {},
    }


def normalize_workflow_spec(value: Any, *, title: str = "") -> dict:
    raw = _parse(value)
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    nodes = [_normalize_node(node, index) for index, node in enumerate(raw.get("nodes") or [], 1)]
    edges = [_normalize_edge(edge, index) for index, edge in enumerate(raw.get("edges") or [], 1)]
    policy = {**DEFAULT_POLICY, **(raw.get("policy") or meta.get("policy") or {})}
    gates = raw.get("quality_gates") or raw.get("qualityGates") or meta.get("quality_gates") or DEFAULT_GATES
    normalized = {
        "spec_version": WORKFLOW_SPEC_VERSION,
        "workflow_id": str(raw.get("workflow_id") or meta.get("template_id") or meta.get("id") or ""),
        "title": str(raw.get("title") or meta.get("template_name") or meta.get("title") or title or "未命名工作流"),
        "description": str(raw.get("description") or meta.get("template_description") or meta.get("description") or ""),
        "input_contract": raw.get("input_contract") or raw.get("inputContract") or {"type": "object", "required": ["task"]},
        "output_contract": raw.get("output_contract") or raw.get("outputContract") or {"type": "object", "required": ["result"]},
        "success_criteria": _list(raw.get("success_criteria") or raw.get("successCriteria") or meta.get("success_criteria"), ["产出非空结果", "记录验证证据"]),
        "policy": policy,
        "quality_gates": gates if isinstance(gates, list) else DEFAULT_GATES,
        "nodes": nodes,
        "edges": edges,
        "meta": {**meta, "compiled": bool(raw.get("compiled") or meta.get("compiled")), "source_version": raw.get("spec_version", 1)},
    }
    return normalized


def _condition_is_valid(value: str) -> bool:
    if not value or value.strip().lower() in {"always", "default", "else"}:
        return True
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*(==|!=|>=|<=|>|<)\s*(true|false|null|none|-?\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\")$", value.strip(), re.I))


def _positive_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def validate_workflow_spec(value: Any) -> list[dict]:
    spec = normalize_workflow_spec(value)
    issues: list[dict] = []
    nodes = spec["nodes"]
    node_ids = [node["id"] for node in nodes]
    node_set = set(node_ids)
    if not nodes:
        issues.append({"severity": "error", "code": "EMPTY_WORKFLOW", "message": "工作流至少需要一个节点。"})
    if len(node_set) != len(node_ids):
        issues.append({"severity": "error", "code": "DUPLICATE_NODE", "message": "节点 ID 必须唯一。"})
    for node in nodes:
        if node["kind"] not in NODE_KINDS:
            issues.append({"severity": "error", "code": "UNKNOWN_NODE_KIND", "node_id": node["id"], "message": f"不支持的节点类型：{node['kind']}"})
        if node["model_profile"] not in MODEL_PROFILES:
            issues.append({"severity": "warning", "code": "UNKNOWN_MODEL_PROFILE", "node_id": node["id"], "message": f"模型档位 {node['model_profile']} 将按 auto 处理。"})
        if not node["label"].strip():
            issues.append({"severity": "error", "code": "EMPTY_NODE_LABEL", "node_id": node["id"], "message": "节点名称不能为空。"})
        for schema_name in ("input_schema", "output_schema"):
            if not isinstance(node.get(schema_name), dict):
                issues.append({"severity": "error", "code": "INVALID_NODE_SCHEMA", "node_id": node["id"], "message": f"节点 {node['id']} 的 {schema_name} 必须是 JSON Schema 对象。"})
    for contract_name in ("input_contract", "output_contract"):
        if not isinstance(spec.get(contract_name), dict):
            issues.append({"severity": "error", "code": "INVALID_CONTRACT", "message": f"{contract_name} 必须是 JSON Schema 对象。"})
    adjacency = defaultdict(list)
    indegree = {node_id: 0 for node_id in node_set}
    incoming = {node_id: [] for node_id in node_set}
    loop_incoming = {node_id: [] for node_id in node_set}
    for edge in spec["edges"]:
        if edge["source"] not in node_set or edge["target"] not in node_set:
            issues.append({"severity": "error", "code": "INVALID_EDGE", "message": f"连线 {edge['id']} 引用了不存在的节点。"})
        if edge["source"] == edge["target"]:
            issues.append({"severity": "error", "code": "SELF_EDGE", "message": f"连线 {edge['id']} 不能连接节点自身。"})
        if not _condition_is_valid(edge["condition"]):
            issues.append({"severity": "error", "code": "INVALID_CONDITION", "message": f"连线 {edge['id']} 的条件表达式不安全。"})
        if edge["type"] == "loop" and _positive_int((edge["loop_policy"] or {}).get("maxIterations") or (edge["loop_policy"] or {}).get("max_iterations")) <= 0:
            issues.append({"severity": "error", "code": "LOOP_WITHOUT_LIMIT", "message": f"循环连线 {edge['id']} 必须设置 maxIterations。"})
        if edge["type"] != "loop" and edge["source"] in node_set and edge["target"] in node_set:
            adjacency[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1
            if edge["target"] in incoming:
                incoming[edge["target"]].append(edge)
        elif edge["target"] in loop_incoming:
            loop_incoming[edge["target"]].append(edge)
    queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if node_set and visited != len(node_set):
        issues.append({"severity": "error", "code": "CYCLE_WITHOUT_LOOP", "message": "工作流存在未声明为 loop 的循环。"})
    for node_id, loop_edges in loop_incoming.items():
        if loop_edges and not incoming.get(node_id):
            issues.append({"severity": "error", "code": "LOOP_TARGET_WITHOUT_ENTRY", "node_id": node_id, "message": "循环目标必须有一条普通入口边，不能只依赖 loop 边启动。"})
    policy = spec["policy"]
    for key in ("max_parallelism", "max_retries_per_node", "max_replans", "max_model_calls", "timeout_seconds"):
        if _positive_int(policy.get(key)) <= 0:
            issues.append({"severity": "error", "code": "INVALID_POLICY", "message": f"策略 {key} 必须大于 0。"})
    if not isinstance(spec["quality_gates"], list) or not spec["quality_gates"]:
        issues.append({"severity": "warning", "code": "NO_QUALITY_GATE", "message": "工作流没有配置质量门禁，将使用默认输出检查。"})
    return issues


def build_default_workflow_spec(prompt: str, *, title: str = "自动编译工作流", policy: dict | None = None) -> dict:
    prompt = str(prompt or "").strip()
    nodes = [
        {"id": "planner", "kind": "planner", "label": "任务规划 Agent", "role": "拆解目标、约束和验收标准", "stage": "analysis", "model_profile": "strong", "instruction": "把目标拆成可执行步骤，并明确每一步的输入、输出和成功标准。", "tools": []},
        {"id": "researcher", "kind": "researcher", "label": "资料与上下文 Agent", "role": "补齐事实、依赖和环境信息", "stage": "research", "model_profile": "strong", "instruction": "识别缺失信息；需要实时事实时收集来源和证据。", "tools": ["web_search"]},
        {"id": "executor", "kind": "executor", "label": "执行 Agent", "role": "完成主要产出或工程修改", "stage": "execution", "model_profile": "strong", "instruction": "根据规划和上下文完成主要任务，必要时使用受限工具。", "tools": ["read_file", "write_file", "run_command"]},
        {"id": "verifier", "kind": "verifier", "label": "验证与修复 Agent", "role": "检查结果、运行测试并提出修复", "stage": "testing", "model_profile": "critic", "instruction": "用证据检查产出；发现问题时给出可执行修复意见。", "tools": ["read_file", "run_command"]},
        {"id": "synthesizer", "kind": "synthesizer", "label": "交付总结 Agent", "role": "整理最终结果、证据和后续动作", "stage": "delivery", "model_profile": "strong", "instruction": "只基于已验证事实输出最终交付内容和文件清单。", "tools": []},
    ]
    edges = [
        {"id": "planner-research", "source": "planner", "target": "researcher", "type": "control"},
        {"id": "planner-execute", "source": "planner", "target": "executor", "type": "control"},
        {"id": "research-verify", "source": "researcher", "target": "verifier", "type": "control"},
        {"id": "execute-verify", "source": "executor", "target": "verifier", "type": "control"},
        {"id": "verify-deliver", "source": "verifier", "target": "synthesizer", "type": "branch", "condition": "success == true"},
    ]
    return normalize_workflow_spec({
        "spec_version": WORKFLOW_SPEC_VERSION,
        "title": title,
        "description": f"由自然语言编译：{prompt[:240]}",
        "input_contract": {"type": "object", "required": ["task"], "properties": {"task": {"type": "string"}}},
        "output_contract": {"type": "object", "required": ["result", "evidence"]},
        "success_criteria": ["完成用户目标", "验证关键产出", "记录可追溯证据"],
        "policy": {**DEFAULT_POLICY, **(policy or {})},
        "quality_gates": DEFAULT_GATES + [{"type": "task_specific", "required": True}],
        "nodes": nodes,
        "edges": edges,
        "meta": {"compiled": True, "compiler": "heuristic-v2", "source_prompt": prompt},
    })


def spec_to_legacy_workflow(spec: dict) -> dict:
    """Keep existing ReactFlow/Skill consumers working while runtime uses v2."""
    normalized = normalize_workflow_spec(spec)
    nodes = []
    for node in normalized["nodes"]:
        data = deepcopy(node.get("legacy_data") or {})
        data.update({
            "label": node["label"], "agentId": node["agent_id"], "nodeType": node["kind"],
            "role": node["role"], "stage": node["stage"], "description": node["description"],
            "instruction": node["instruction"], "systemPrompt": node["system_prompt"],
            "modelProfile": node["model_profile"], "inputFields": node["input_fields"], "outputFields": node["output_fields"],
            "inputSchema": node["input_schema"], "outputSchema": node["output_schema"], "verification": node["verification"],
        })
        if node.get("repair_for"):
            data["repair_for"] = node["repair_for"]
        nodes.append({"id": node["id"], "type": "customAgent", "position": node["position"], "data": data})
    edges = []
    for edge in normalized["edges"]:
        edges.append({"id": edge["id"], "source": edge["source"], "target": edge["target"], "type": "smoothstep", "label": edge["label"], "data": {"edgeType": edge["type"], "condition": edge["condition"], "label": edge["label"], "fromOutputField": edge["from_output"], "toInputField": edge["to_input"], "loopPolicy": edge["loop_policy"]}})
    return {"nodes": nodes, "edges": edges, "meta": {**normalized["meta"], "template_name": normalized["title"], "template_description": normalized["description"], "workflow_spec_version": WORKFLOW_SPEC_VERSION, "policy": normalized["policy"], "quality_gates": normalized["quality_gates"], "success_criteria": normalized["success_criteria"]}}
