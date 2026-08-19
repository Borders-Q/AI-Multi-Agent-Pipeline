from __future__ import annotations

import json
import re
from typing import Any

from agent.llm_client import llm
from skyt_platform.workflow_spec import (
    build_default_workflow_spec,
    normalize_workflow_spec,
    validate_workflow_spec,
)


def _json_from_text(text: str) -> dict | None:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S).strip()
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


async def compile_workflow(prompt: str, *, title: str = "", provider: str | None = None, policy: dict | None = None) -> dict:
    """Compile a goal into a reviewable graph, with a deterministic offline fallback."""
    fallback = build_default_workflow_spec(prompt, title=title or "自动编译工作流", policy=policy)
    assumptions = ["未执行任何工具；当前结果仅是待审查的工作流草案。"]
    questions: list[str] = []
    if not str(prompt or "").strip():
        questions.append("请补充任务目标、交付物和成功标准。")
        return {"workflow_spec": fallback, "assumptions": assumptions, "questions": questions, "source": "heuristic", "validation_issues": validate_workflow_spec(fallback)}

    if not llm.clients:
        assumptions.append("当前没有可用模型，使用内置通用规划骨架；确认后仍可在编辑器中调整。")
        return {"workflow_spec": fallback, "assumptions": assumptions, "questions": questions, "source": "heuristic", "validation_issues": validate_workflow_spec(fallback)}

    system = (
        "你是 SkyT Workflow Compiler。把用户目标编译成严格 JSON 工作流草案。"
        "只输出 JSON，不输出 Markdown。必须包含 spec_version=2、title、description、"
        "success_criteria、policy、quality_gates、nodes、edges、assumptions、questions。"
        "节点 kind 只能是 planner/researcher/executor/tool/verifier/critic/synthesizer/agent/human_approval。"
        "每个节点必须有 id、kind、label、role、instruction、model_profile、tools、input_fields、output_fields。"
        "图必须是有向无环图；循环只能通过 type=loop 且 loop_policy.maxIterations>0 表示。"
        "不要执行工具，不要虚构已完成的结果。"
    )
    user = json.dumps({"task": prompt, "title": title, "policy": policy or {}}, ensure_ascii=False)
    try:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        # Do not depend on response_format: several Ollama/OpenAI-compatible
        # endpoints reject it. The strict system prompt plus parser below keeps
        # the compiler portable across local and cloud providers.
        response = await llm.chat_completion(
            messages,
            provider=provider,
            tools=None,
            temperature=0.2,
        )
        content = getattr(response.choices[0].message, "content", "") if getattr(response, "choices", None) else ""
        candidate = _json_from_text(content)
        if candidate:
            spec = normalize_workflow_spec(candidate, title=title)
            spec["meta"].update({"compiled": True, "compiler": "llm-v2", "source_prompt": prompt})
            assumptions.extend(candidate.get("assumptions") or [])
            questions.extend(candidate.get("questions") or [])
            issues = validate_workflow_spec(spec)
            if not any(issue.get("severity") == "error" for issue in issues):
                return {"workflow_spec": spec, "assumptions": assumptions, "questions": questions, "source": "llm", "validation_issues": issues}
            assumptions.append("模型草案未通过结构校验，已回退到内置安全骨架。")
    except Exception as exc:
        assumptions.append(f"模型编译不可用，已回退到内置骨架：{type(exc).__name__}。")
    return {"workflow_spec": fallback, "assumptions": assumptions, "questions": questions, "source": "heuristic", "validation_issues": validate_workflow_spec(fallback)}
