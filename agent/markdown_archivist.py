import os
import json
from pathlib import Path
from typing import Optional

import db
from agent.llm_client import llm
from agent.router import get_prioritized_models
from agent.token_usage import usage_from_openai_response


KIND_LABELS = {
    "task_summary": "本次任务总结",
    "replay_summary": "深度回放摘要",
    "important_work_log": "历史重要工作记录",
    "api_context": "API 前置上下文压缩",
}


def _safe_load_json(value):
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _clip(text, limit=900):
    text = "" if text is None else str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [clipped {len(text) - limit} chars]"


def build_run_context(run_id: str, kind: str) -> tuple[dict, str]:
    run = db.get_run_detail(run_id)
    if not run:
        raise ValueError(f"Run not found: {run_id}")

    events = run.get("events") or []
    rows = []
    for event in events[:80]:
        detail = _safe_load_json(event.get("detail_json"))
        token_usage = detail.get("token_usage") if isinstance(detail, dict) else None
        input_payload = detail.get("input_payload") if isinstance(detail, dict) else None
        output_payload = detail.get("output_payload") if isinstance(detail, dict) else None
        distillation = detail.get("distillation") if isinstance(detail, dict) else None
        rows.append(
            {
                "event_type": event.get("event_type"),
                "agent": event.get("agent"),
                "status": event.get("status"),
                "message": event.get("message"),
                "duration_ms": event.get("duration_ms"),
                "token_usage": token_usage,
                "input_summary": _clip(input_payload, 500) if input_payload else "",
                "output_summary": _clip(output_payload, 700) if output_payload else "",
                "distillation": distillation,
            }
        )

    context = {
        "run_id": run_id,
        "kind": kind,
        "requirement": run.get("requirement"),
        "success": bool(run.get("success")),
        "quality_score": float(run.get("quality_score") or 0),
        "total_tokens": int(run.get("total_tokens") or 0),
        "api_tokens": int(run.get("api_tokens") or 0),
        "local_tokens": int(run.get("local_tokens") or 0),
        "token_source": run.get("token_source") or "none",
        "events": rows,
    }

    context_text = json.dumps(context, ensure_ascii=False, indent=2)
    return run, _clip(context_text, 12000)


def fallback_markdown(run: dict, kind: str) -> str:
    label = KIND_LABELS.get(kind, kind)
    return (
        f"# Ai Multi Agent {label}\n\n"
        f"- 运行 ID：`{run.get('run_id')}`\n"
        f"- 任务目标：{run.get('requirement') or '未记录'}\n"
        f"- 状态：{'成功' if run.get('success') else '失败或未完成'}\n"
        f"- 质量分：{run.get('quality_score')}\n"
        f"- Token：API {run.get('api_tokens') or 0} / 本地 {run.get('local_tokens') or 0} / 总计 {run.get('total_tokens') or 0}\n\n"
        "## 核心记录\n\n"
        "本报告由 Ai Multi Agent fallback 归档器生成。GPU Markdown 生成失败时，系统仍保留最小可读工作记录。\n"
    )


async def generate_run_markdown(run_id: str, kind: str = "important_work_log", workspace: Optional[str] = None) -> dict:
    if kind not in KIND_LABELS:
        kind = "important_work_log"

    run, context_text = build_run_context(run_id, kind)
    label = KIND_LABELS[kind]
    prompt = (
        f"请使用本地 GPU 辅助节点生成一份 Ai Multi Agent {label} Markdown。\n"
        "【强制语言规则】：除非用户在原始需求中明确要求使用其他语言，否则整篇 Markdown 必须使用中文输出；标题、章节名、表格字段、总结、后续建议都必须是中文，不要夹杂英文小标题。\n"
        "要求：不要写流水账；必须包含任务时间/运行ID、任务目标、核心步骤、关键文件或产物、错误与修复、Token 消耗、后续建议。\n"
        "如果事件已经被蒸馏，请基于 distillation 摘要说明，不要要求原始日志。\n\n"
        f"结构化运行上下文：\n```json\n{context_text}\n```"
    )

    markdown = ""
    token_usage = None
    model = None
    try:
        models = await get_prioritized_models(prefer_large=True)
        model = models[0] if models else "ollama"
        messages = [
            {"role": "system", "content": "你是 Ai Multi Agent 本地 GPU Markdown 归档节点，负责低成本生成可维护的工程记录。除非用户明确要求其他语言，否则必须强制使用中文生成完整 Markdown。"},
            {"role": "user", "content": prompt},
        ]
        response = await llm.chat_completion(messages, provider=model, is_background=True)
        markdown = response.choices[0].message.content or ""
        token_usage = getattr(response, "skyt_token_usage", None) or usage_from_openai_response(
            response,
            provider=model,
            role=f"markdown_archivist_{kind}",
            messages=messages,
            output_text=markdown,
            is_local=True,
        )
    except Exception as exc:
        markdown = fallback_markdown(run, kind) + f"\n\n> GPU 生成失败，已使用 fallback：{exc}\n"

    title = f"Ai Multi Agent {label}: {run_id}"
    report_id = db.save_report(title, markdown)
    saved_path = None

    if workspace:
        try:
            target_dir = Path(workspace) / ".skyt" / "important_work_logs"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{run_id}_{kind}.md"
            target_path.write_text(markdown, encoding="utf-8")
            saved_path = str(target_path)
        except Exception:
            saved_path = None

    db.save_run_event(
        run_id,
        "MARKDOWN_ARCHIVE",
        "GPUMarkdown",
        "SUCCESS",
        f"生成 {label}",
        json.dumps(
            {
                "input_payload": {"kind": kind, "workspace": workspace},
                "output_payload": {"report_id": report_id, "saved_path": saved_path, "preview": markdown[:700]},
                "token_usage": token_usage,
                "model_info": {"provider": "ollama", "model": model, "routed_by": "GPU"},
            },
            ensure_ascii=False,
        ),
        0,
    )

    return {
        "status": "success",
        "run_id": run_id,
        "kind": kind,
        "report_id": report_id,
        "saved_path": saved_path,
        "markdown_preview": markdown[:1200],
        "token_usage": token_usage,
    }
