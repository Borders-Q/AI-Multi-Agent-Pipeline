from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any

import db
from agent.llm_client import llm
from agent.skills import tool_manager
from skyt_platform.checkpoints import create_checkpoint
from skyt_platform.model_router import ModelRouter
from skyt_platform.quality_gates import run_quality_gates
from skyt_platform.workflow_spec import normalize_workflow_spec


logger = logging.getLogger(__name__)


def _clip(value: Any, limit: int = 12000) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return f"{text[:3000]}\n...上下文已压缩...\n{text[-(limit - 3020):]}"


def _usage_total(usage: dict | None) -> int:
    usage = usage or {}
    return int(
        usage.get("total_tokens")
        or (int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0))
        or 0
    )


def _condition(condition: str, state: dict) -> bool:
    normalized = str(condition or "").strip()
    if not normalized or normalized.lower() in {"always", "default"}:
        return True
    if normalized.lower() == "else":
        return False
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(true|false|null|none|-?\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\")$", normalized, re.I)
    if not match:
        return False
    field, operator, raw = match.groups()
    left = state.get(field)
    value = raw[1:-1] if raw[:1] in {"'", '"'} else ({"true": True, "false": False, "null": None, "none": None}.get(raw.lower(), raw))
    if isinstance(value, str) and re.match(r"^-?\d+(?:\.\d+)?$", value):
        value = float(value) if "." in value else int(value)
    if operator == "==":
        return left == value
    if operator == "!=":
        return left != value
    try:
        left, value = float(left), float(value)
    except (TypeError, ValueError):
        return False
    return {">": left > value, "<": left < value, ">=": left >= value, "<=": left <= value}.get(operator, False)


class WorkflowRuntime:
    def __init__(self):
        self._run_locks: dict[str, asyncio.Lock] = {}

    async def handle_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = str(payload.get("run_id") or "")
        if not run_id:
            raise ValueError("workflow_run 任务缺少 run_id。")
        lock = self._run_locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            return await self.execute(run_id, task_id=str(payload.get("_task_id") or ""))

    async def _event(self, run_id: str, event_type: str, status: str, message: str, detail: dict | None = None):
        try:
            db.save_run_event(run_id, event_type, "WorkflowRuntime", status, message, json.dumps(detail or {}, ensure_ascii=False), 0)
        except Exception:
            logger.debug("workflow event could not be persisted", exc_info=True)

    async def _wait_state(self, run_id: str, task_id: str):
        while True:
            run = db.get_workflow_run(run_id) or {}
            task = db.get_task(task_id) if task_id else None
            run_status = run.get("status")
            task_status = (task or {}).get("status")
            if run_status == "cancelled" or task_status in {"cancel_requested", "cancelled"}:
                raise asyncio.CancelledError()
            if run_status != "paused":
                return run
            await self._event(run_id, "WORKFLOW_PAUSED", "SKIPPED", "工作流暂停中，等待恢复。")
            await asyncio.sleep(0.8)

    def _load_persisted_state(self, run_id: str, nodes: dict[str, dict]) -> tuple[dict[str, dict], dict[str, dict]]:
        """Recover successful node outputs so a worker restart is resumable."""
        completed: dict[str, dict] = {}
        outputs: dict[str, dict] = {}
        try:
            records = db.get_workflow_node_runs(run_id)
        except Exception:
            logger.warning("workflow node state could not be loaded for %s", run_id, exc_info=True)
            return completed, outputs
        latest: dict[str, dict] = {}
        for record in records or []:
            latest[str(record.get("node_id") or "")] = record
        for record in latest.values():
            node_id = str(record.get("node_id") or "")
            if node_id not in nodes or record.get("status") != "succeeded":
                continue
            output = record.get("output") or {}
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    output = {"success": True, "text": output}
            if not isinstance(output, dict):
                output = {"success": True, "text": str(output)}
            output.setdefault("success", True)
            completed[node_id] = output
            outputs[node_id] = output
        return completed, outputs

    def _attempt_start(self, run_id: str, node_id: str, max_attempts: int) -> int:
        try:
            records = [item for item in db.get_workflow_node_runs(run_id) if item.get("node_id") == node_id]
        except Exception:
            records = []
        failed = [int(item.get("attempt") or 0) for item in records if item.get("status") == "failed"]
        highest = max(failed, default=0)
        return max_attempts + 1 if highest >= max_attempts else highest + 1

    def _add_repair_nodes(self, spec: dict, failed_ids: list[str], completed: dict[str, dict], replan_count: int) -> tuple[dict, list[str]]:
        """Add bounded repair nodes while leaving already executed nodes intact."""
        existing = {node["id"] for node in spec.get("nodes") or []}
        added: list[str] = []
        original_nodes = {node["id"]: node for node in spec.get("nodes") or []}
        original_edges = list(spec.get("edges") or [])
        for failed_id in failed_ids:
            source = original_nodes.get(failed_id)
            if not source:
                continue
            repair_id = f"{failed_id}__repair_{replan_count}"
            if repair_id in existing:
                continue
            repair = {
                **source,
                "id": repair_id,
                "label": f"修复：{source.get('label') or failed_id}",
                "kind": "executor",
                "repair_for": failed_id,
                "instruction": f"修复节点 {source.get('label') or failed_id} 未通过质量门禁的问题。只处理未完成部分，输出可验证的修复结果。",
                "position": {"x": (source.get("position") or {}).get("x", 0) + 80, "y": (source.get("position") or {}).get("y", 100) + 180},
            }
            spec.setdefault("nodes", []).append(repair)
            spec.setdefault("edges", []).append({
                "id": f"{failed_id}__to__{repair_id}",
                "source": failed_id,
                "target": repair_id,
                "type": "control",
                "condition": "success == false",
                "label": "失败后修复",
                "from_output": "",
                "to_input": "",
                "loop_policy": {},
            })
            # Route the repair into downstream nodes that have not completed.
            for edge in original_edges:
                if edge.get("source") != failed_id or edge.get("type") == "loop":
                    continue
                target = str(edge.get("target") or "")
                if target not in original_nodes or target in completed:
                    continue
                spec["edges"].append({
                    **edge,
                    "id": f"{repair_id}__to__{target}",
                    "source": repair_id,
                    "condition": "success == true",
                })
            existing.add(repair_id)
            added.append(repair_id)
        return normalize_workflow_spec(spec), added

    def _schedule_loops(self, spec: dict, source_id: str, result: dict, pending: set[str], completed: dict[str, dict], outputs: dict[str, dict], loop_counts: dict[str, int]) -> list[str]:
        scheduled: list[str] = []
        if not result.get("success"):
            return scheduled
        for edge in spec.get("edges") or []:
            if edge.get("type") != "loop" or edge.get("source") != source_id:
                continue
            state = {"success": True, "status": "success", "quality_score": 10}
            if not _condition(edge.get("condition") or "", state):
                continue
            policy = edge.get("loop_policy") or {}
            maximum = int(policy.get("maxIterations") or policy.get("max_iterations") or 0)
            if maximum <= 0 or loop_counts.get(edge["id"], 0) >= maximum:
                continue
            target = str(edge.get("target") or "")
            if target not in completed and target not in pending:
                continue
            loop_counts[edge["id"]] = loop_counts.get(edge["id"], 0) + 1
            pending.add(target)
            completed.pop(target, None)
            outputs.pop(target, None)
            scheduled.append(target)
        return scheduled

    async def _call_model(self, node: dict, messages: list[dict], run: dict, tools: list[dict], counters: dict) -> tuple[str, str, dict, list[dict]]:
        router = ModelRouter(llm.clients)
        profile = node.get("model_profile") or "auto"
        preferred = run.get("provider")
        candidates = router.candidates(profile)
        if preferred:
            candidates = [preferred] + [item for item in candidates if item != preferred]
        if not candidates:
            raise RuntimeError("没有可用模型，请先配置 Ollama 或云端模型。")
        last_error = None
        for provider in candidates:
            if counters["model_calls"] >= counters["max_model_calls"]:
                raise RuntimeError("已达到本次工作流的模型调用预算。")
            try:
                counters["model_calls"] += 1
                response = await llm.chat_completion(messages, provider=provider, tools=tools or None, temperature=0.2)
                usage = getattr(response, "skyt_token_usage", None) or {}
                content = getattr(response.choices[0].message, "content", "") if getattr(response, "choices", None) else ""
                calls = []
                message = response.choices[0].message if getattr(response, "choices", None) else None
                if message is not None and getattr(message, "tool_calls", None):
                    message_dict = message.model_dump() if hasattr(message, "model_dump") else message
                    messages.append(message_dict)
                    for tool_call in message.tool_calls:
                        name = tool_call.function.name
                        try:
                            args = json.loads(tool_call.function.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        result = await tool_manager.execute_tool(name, args)
                        calls.append({"tool": name, "args": args, "result": str(result)[:4000]})
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": str(result)})
                    if counters["model_calls"] >= counters["max_model_calls"]:
                        return content or "", provider, usage, calls
                    counters["model_calls"] += 1
                    second = await llm.chat_completion(messages, provider=provider, tools=None, temperature=0.2)
                    usage2 = getattr(second, "skyt_token_usage", None) or {}
                    content = getattr(second.choices[0].message, "content", "") if getattr(second, "choices", None) else content
                    usage = {key: int(usage.get(key, 0) or 0) + int(usage2.get(key, 0) or 0) for key in set(usage) | set(usage2)}
                return str(content or ""), provider, usage, calls
            except Exception as exc:
                last_error = exc
                await self._event(run["run_id"], "MODEL_FALLBACK", "FAILED", f"模型 {provider} 调用失败，准备降级。", {"provider": provider, "error": type(exc).__name__})
        raise RuntimeError(f"所有候选模型均不可用：{type(last_error).__name__ if last_error else 'unknown'}")

    async def _execute_node(self, run: dict, node: dict, context: dict, counters: dict) -> dict:
        run_id = run["run_id"]
        node_id = node["id"]
        policy = run["workflow_spec"].get("policy") or {}
        max_attempts = max(1, int(policy.get("max_retries_per_node", 2)) + 1)
        if node["kind"] == "human_approval":
            db.update_workflow_run(run_id, status="waiting_approval", current_node_id=node_id)
            await self._event(run_id, "WORKFLOW_APPROVAL_REQUIRED", "WAITING", node["label"], {"node_id": node_id, "question": node.get("instruction")})
            while True:
                current = await self._wait_state(run_id, str(run.get("task_id") or ""))
                if current.get("approved"):
                    return {"success": True, "text": "人工审批已通过。", "evidence": [{"type": "approval", "node_id": node_id}]}
                if current.get("status") == "cancelled":
                    raise asyncio.CancelledError()
                await asyncio.sleep(0.8)

        tools = []
        allowed = set(node.get("tools") or [])
        if allowed:
            tools = [item for item in tool_manager.get_openai_tools() if (item.get("function") or {}).get("name") in allowed]
        prompt = (
            f"你正在执行 SkyT 工作流节点：{node['label']}。\n"
            f"节点类型：{node['kind']}\n角色：{node.get('role') or '按节点职责执行'}\n"
            f"节点指令：{node.get('instruction') or '完成该节点职责'}\n"
            f"输入字段：{', '.join(node.get('input_fields') or [])}\n"
            f"输出字段：{', '.join(node.get('output_fields') or [])}\n"
            "只完成本节点职责，不替代其他节点。输出必须说明做了什么、证据是什么、是否成功。\n"
            f"任务输入与上游上下文：\n{_clip(context)}"
        )
        if node.get("system_prompt"):
            prompt += f"\n额外系统约束：{node['system_prompt']}"
        messages = [{"role": "system", "content": "你是 SkyT 的严谨工作流节点。不要声称执行过未执行的操作。"}, {"role": "user", "content": prompt}]
        attempt_start = self._attempt_start(run_id, node_id, max_attempts)
        for attempt in range(attempt_start, max_attempts + 1):
            await self._wait_state(run_id, str(run.get("task_id") or ""))
            node_run_id = db.create_workflow_node_run(run_id, node_id, attempt, input_data=context, model_profile=node.get("model_profile"))
            started = time.monotonic()
            await self._event(run_id, "WORKFLOW_NODE_STARTED", "RUNNING", node["label"], {"node_id": node_id, "attempt": attempt, "model_profile": node.get("model_profile")})
            try:
                text, provider, usage, calls = await self._call_model(node, messages.copy(), run, tools, counters)
                evidence = [{"type": "node_output", "node_id": node_id, "provider": provider, "summary": text[:1000]}]
                evidence.extend({"type": "tool_call", **call} for call in calls)
                node_spec = {**run["workflow_spec"], "quality_gates": (node.get("verification") or {}).get("gates") or [{"type": "output_present", "required": True}]}
                gate = await run_quality_gates(task=run.get("input", {}).get("task", ""), spec=node_spec, context={"output": text, "evidence": evidence, "verified": True}, workspace=run.get("workspace"))
                result = {"success": gate["passed"], "text": text, "evidence": evidence, "quality": gate, "provider": provider, "usage": usage, "tool_calls": calls, "duration_ms": int((time.monotonic() - started) * 1000)}
                db.finish_workflow_node_run(node_run_id, status="succeeded" if gate["passed"] else "failed", output=result, evidence=gate, provider=provider)
                await self._event(run_id, "WORKFLOW_NODE_FINISHED", "SUCCESS" if gate["passed"] else "FAILED", node["label"], {"node_id": node_id, "attempt": attempt, "quality": gate, "provider": provider, "tool_calls": calls})
                if gate["passed"]:
                    return result
                if attempt < max_attempts:
                    messages.append({"role": "user", "content": f"上一次输出未通过质量门禁，请修复后重试。失败门禁：{json.dumps(gate['failed_required'], ensure_ascii=False)}"})
            except asyncio.CancelledError:
                db.finish_workflow_node_run(node_run_id, status="cancelled", error="用户取消")
                raise
            except Exception as exc:
                db.finish_workflow_node_run(node_run_id, status="failed", error=str(exc))
                await self._event(run_id, "WORKFLOW_NODE_FAILED", "FAILED", node["label"], {"node_id": node_id, "attempt": attempt, "error": str(exc)})
                if attempt >= max_attempts:
                    return {"success": False, "text": "", "error": str(exc), "evidence": []}
        return {"success": False, "text": "节点重试预算耗尽。", "evidence": []}

    def _ready_nodes(self, spec: dict, pending: set[str], completed: dict[str, dict]) -> tuple[list[str], list[str]]:
        edges = spec.get("edges") or []
        incoming = {node["id"]: [] for node in spec.get("nodes") or []}
        loop_incoming = {node_id: [] for node_id in incoming}
        for edge in edges:
            if edge.get("type") == "loop" and edge.get("target") in loop_incoming:
                loop_incoming[edge["target"]].append(edge)
        for edge in edges:
            if edge.get("type") != "loop" and edge.get("target") in incoming:
                incoming[edge["target"]].append(edge)
        ready, skipped = [], []
        for node_id in pending:
            inbound = incoming.get(node_id, [])
            if not inbound:
                if loop_incoming.get(node_id):
                    # A loop target needs a normal entry edge for its first
                    # iteration; loop edges only schedule later iterations.
                    continue
                ready.append(node_id)
                continue
            if not all(edge.get("source") in completed for edge in inbound):
                continue
            selected = False
            has_else = False
            for edge in inbound:
                source = completed.get(edge.get("source")) or {}
                state = {"success": bool(source.get("success")), "status": "success" if source.get("success") else "failed", "quality_score": 10 if source.get("success") else 0}
                condition = edge.get("condition") or ""
                if condition.strip().lower() == "else":
                    has_else = True
                    continue
                if source.get("success") is False and not condition:
                    continue
                if _condition(condition, state):
                    selected = True
                    break
            if not selected and has_else:
                selected = True
            if selected:
                ready.append(node_id)
            else:
                skipped.append(node_id)
        return ready, skipped

    async def execute(self, run_id: str, *, task_id: str = "") -> dict:
        run = db.get_workflow_run(run_id)
        if not run:
            raise ValueError(f"工作流运行不存在：{run_id}")
        if run.get("status") == "succeeded" and run.get("result"):
            return run["result"]
        if run.get("status") == "cancelled":
            raise asyncio.CancelledError()
        if task_id and not run.get("task_id"):
            db.update_workflow_run(run_id, task_id=task_id)
            run["task_id"] = task_id
        spec = normalize_workflow_spec(run.get("workflow_spec") or {})
        run["workflow_spec"] = spec
        db.update_workflow_run(run_id, status="running")
        nodes = {node["id"]: node for node in spec.get("nodes") or []}
        completed, outputs = self._load_persisted_state(run_id, nodes)
        pending = set(nodes) - set(completed)
        counters = {"model_calls": int(run.get("model_calls") or 0), "max_model_calls": int((spec.get("policy") or {}).get("max_model_calls", 40))}
        resolved_failures = {
            node.get("repair_for") for node_id, node in nodes.items()
            if node.get("repair_for") and node_id in completed
        }
        evidence: list[dict] = [item for result in outputs.values() for item in result.get("evidence") or []]
        loop_counts: dict[str, int] = {}
        try:
            checkpoint = create_checkpoint(run.get("workspace"), run_id, "workflow-start")
            if checkpoint.get("path"):
                db.save_workflow_checkpoint(run_id, checkpoint)
            while pending:
                await self._wait_state(run_id, str(run.get("task_id") or task_id))
                ready, skipped = self._ready_nodes(spec, pending, completed)
                for node_id in skipped:
                    pending.remove(node_id)
                    completed[node_id] = {"success": False, "skipped": True, "text": "条件未满足，节点跳过。"}
                    await self._event(run_id, "WORKFLOW_NODE_SKIPPED", "SKIPPED", nodes[node_id]["label"], {"node_id": node_id})
                if not ready:
                    if pending:
                        raise RuntimeError(f"工作流无法继续，待执行节点存在未满足依赖：{sorted(pending)}")
                    break
                limit = max(1, min(int((spec.get("policy") or {}).get("max_parallelism", 4)), 16))
                for start in range(0, len(ready), limit):
                    batch = ready[start:start + limit]
                    await self._event(run_id, "WORKFLOW_PARALLEL_BATCH", "RUNNING", f"并行执行 {len(batch)} 个节点。", {"nodes": batch})
                    results = await asyncio.gather(*[self._execute_node(run, nodes[node_id], {"task": run.get("input", {}).get("task", ""), "upstream": {key: outputs.get(key) for key in outputs}}, counters) for node_id in batch], return_exceptions=True)
                    for node_id, result in zip(batch, results):
                        pending.discard(node_id)
                        if isinstance(result, BaseException):
                            if isinstance(result, asyncio.CancelledError):
                                raise result
                            result = {"success": False, "error": str(result), "evidence": []}
                        outputs[node_id] = result
                        completed[node_id] = result
                        evidence.extend(result.get("evidence") or [])
                        repair_for = nodes.get(node_id, {}).get("repair_for")
                        if repair_for and result.get("success"):
                            resolved_failures.add(repair_for)
                        db.update_workflow_run(run_id, current_node_id=node_id, model_calls=counters["model_calls"], total_tokens=sum(_usage_total(item.get("usage")) for item in outputs.values()))
                        self._schedule_loops(spec, node_id, result, pending, completed, outputs, loop_counts)
                    failed_batch = [
                        node_id for node_id in batch
                        if not outputs.get(node_id, {}).get("success") and not outputs.get(node_id, {}).get("skipped")
                    ]
                    max_replans = int((spec.get("policy") or {}).get("max_replans", 3))
                    current_replans = int(run.get("replan_count") or 0)
                    if failed_batch and current_replans < max_replans:
                        next_replan = current_replans + 1
                        spec, repair_ids = self._add_repair_nodes(spec, failed_batch, completed, next_replan)
                        if repair_ids:
                            run["workflow_spec"] = spec
                            run["replan_count"] = next_replan
                            run["plan_revision"] = int(run.get("plan_revision") or 1) + 1
                            nodes = {node["id"]: node for node in spec.get("nodes") or []}
                            pending.update(repair_ids)
                            db.replace_workflow_spec(run_id, spec, replan_count=next_replan, plan_revision=run["plan_revision"], status="running")
                            await self._event(run_id, "WORKFLOW_REPLANNED", "RUNNING", "节点质量失败，已为未完成分支生成受限修复计划。", {"failed_nodes": failed_batch, "repair_nodes": repair_ids, "replan_count": next_replan})
                    checkpoint = create_checkpoint(run.get("workspace"), run_id, f"after-{batch[-1]}")
                    if checkpoint.get("path"):
                        db.save_workflow_checkpoint(run_id, checkpoint)
            final_outputs = [result for result in outputs.values() if not result.get("skipped")]
            failed_nodes = [
                node_id for node_id, result in outputs.items()
                if not result.get("skipped") and not result.get("success", False) and node_id not in resolved_failures
            ]
            if failed_nodes:
                raise RuntimeError(f"节点未通过质量门禁：{', '.join(failed_nodes)}")
            final_text = "\n\n".join(str(result.get("text") or "") for result in final_outputs if result.get("text"))[-20000:]
            gate = await run_quality_gates(task=run.get("input", {}).get("task", ""), spec=spec, context={"output": final_text, "evidence": evidence, "verified": all(item.get("success", False) for item in final_outputs if item)}, workspace=run.get("workspace"))
            db.save_workflow_evaluation(run_id, "deterministic-gates", 10.0 if gate["passed"] else 0.0, gate["passed"], gate)
            if not gate["passed"]:
                raise RuntimeError(f"质量门禁未通过：{json.dumps(gate['failed_required'], ensure_ascii=False)}")
            result = {"result": final_text, "nodes": outputs, "evidence": evidence, "quality": gate, "model_calls": counters["model_calls"]}
            db.update_workflow_run(run_id, status="succeeded", result=result, model_calls=counters["model_calls"])
            await self._event(run_id, "WORKFLOW_FINISHED", "SUCCESS", "工作流完成并通过质量门禁。", {"quality": gate, "model_calls": counters["model_calls"]})
            return result
        except asyncio.CancelledError:
            db.update_workflow_run(run_id, status="cancelled", error="用户取消")
            await self._event(run_id, "WORKFLOW_CANCELLED", "CANCELLED", "工作流已取消。")
            raise
        except Exception as exc:
            db.update_workflow_run(run_id, status="failed", error=str(exc), model_calls=counters["model_calls"])
            await self._event(run_id, "WORKFLOW_FINISHED", "FAILED", "工作流未通过质量门禁或执行失败。", {"error": str(exc)})
            return {"success": False, "status": "failed", "non_retryable": True, "error": str(exc), "model_calls": counters["model_calls"]}


workflow_runtime = WorkflowRuntime()
