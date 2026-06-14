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

def build_session_context(session_id: str, kind: str) -> tuple[dict, str]:
    session = db.get_run_session_detail(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    events = session.get("events") or []
    rows = []
    for event in events[:140]:
        detail = _safe_load_json(event.get("detail_json"))
        token_usage = detail.get("token_usage") if isinstance(detail, dict) else None
        input_payload = detail.get("input_payload") if isinstance(detail, dict) else None
        output_payload = detail.get("output_payload") if isinstance(detail, dict) else None
        rows.append(
            {
                "run_id": event.get("run_id"),
                "event_type": event.get("event_type"),
                "agent": event.get("agent"),
                "status": event.get("status"),
                "message": _clip(event.get("message"), 420),
                "duration_ms": event.get("duration_ms"),
                "token_usage": token_usage,
                "input_summary": _clip(input_payload, 400) if input_payload else "",
                "output_summary": _clip(output_payload, 550) if output_payload else "",
            }
        )

    context = {
        "session_id": session_id,
        "kind": kind,
        "title": session.get("title"),
        "first_requirement": session.get("first_requirement"),
        "latest_requirement": session.get("requirement"),
        "run_count": int(session.get("run_count") or 0),
        "success_count": int(session.get("success_count") or 0),
        "failed_count": int(session.get("failed_count") or 0),
        "quality_score": float(session.get("quality_score") or 0),
        "total_tokens": int(session.get("total_tokens") or 0),
        "api_tokens": int(session.get("api_tokens") or 0),
        "local_tokens": int(session.get("local_tokens") or 0),
        "events": rows,
    }
    context_text = json.dumps(context, ensure_ascii=False, indent=2, default=str)
    return session, _clip(context_text, 16000)


def fallback_markdown(run: dict, kind: str) -> str:
    label = KIND_LABELS.get(kind, kind)
    return (
        f"# 天韬（SkyT） {label}\n\n"
        f"- 运行 ID：`{run.get('run_id')}`\n"
        f"- 任务目标：{run.get('requirement') or '未记录'}\n"
        f"- 状态：{'成功' if run.get('success') else '失败或未完成'}\n"
        f"- 质量分：{run.get('quality_score')}\n"
        f"- Token：API {run.get('api_tokens') or 0} / 本地 {run.get('local_tokens') or 0} / 总计 {run.get('total_tokens') or 0}\n\n"
        "## 核心记录\n\n"
        "本报告由 天韬（SkyT） fallback 归档器生成。GPU Markdown 生成失败时，系统仍保留最小可读工作记录。\n"
    )

def fallback_session_markdown(session: dict, kind: str) -> str:
    label = KIND_LABELS.get(kind, kind)
    return (
        f"# 天韬（SkyT） 历史会话{label}\n\n"
        f"- 会话 ID：`{session.get('session_id')}`\n"
        f"- 会话标题：{session.get('title') or '未命名会话'}\n"
        f"- 运行次数：{session.get('run_count') or 0}\n"
        f"- 成功/失败：{session.get('success_count') or 0} / {session.get('failed_count') or 0}\n"
        f"- Token：API {session.get('api_tokens') or 0} / 本地 {session.get('local_tokens') or 0} / 总计 {session.get('total_tokens') or 0}\n\n"
        "## 核心记录\n\n"
        "本报告由 天韬（SkyT） fallback 会话归档器生成，覆盖整个历史会话而不是单次提问。\n"
    )


async def generate_run_markdown(run_id: str, kind: str = "important_work_log", workspace: Optional[str] = None) -> dict:
    if kind not in KIND_LABELS:
        kind = "important_work_log"

    run, context_text = build_run_context(run_id, kind)
    label = KIND_LABELS[kind]
    prompt = (
        f"请使用本地 GPU 辅助节点生成一份 天韬（SkyT） {label} Markdown。\n"
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
            {"role": "system", "content": "你是 天韬（SkyT） 本地 GPU Markdown 归档节点，负责低成本生成可维护的工程记录。除非用户明确要求其他语言，否则必须强制使用中文生成完整 Markdown。"},
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

    title = f"天韬（SkyT） {label}: {run_id}"
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


async def generate_session_markdown(session_id: str, kind: str = "important_work_log", workspace: Optional[str] = None) -> dict:
    if kind not in KIND_LABELS:
        kind = "important_work_log"

    session, context_text = build_session_context(session_id, kind)
    label = KIND_LABELS[kind]
    prompt = (
        f"请使用本地 GPU 辅助节点生成一份 天韬（SkyT） 历史会话级 {label} Markdown。\n"
        "【强制语言规则】：除非用户在原始需求中明确要求使用其他语言，否则整篇 Markdown 必须使用中文输出；标题、章节名、表格字段、总结、后续建议都必须是中文。\n"
        "要求：这是一个完整历史会话的工作记录，不要按单条问答割裂；必须包含会话目标演变、关键提问与回复、多个 run 的执行过程、失败或风险、Token 总消耗、最终产出和后续建议。\n\n"
        f"结构化会话上下文：\n```json\n{context_text}\n```"
    )

    markdown = ""
    token_usage = None
    model = None
    try:
        models = await get_prioritized_models(prefer_large=True)
        model = models[0] if models else "ollama"
        messages = [
            {"role": "system", "content": "你是 天韬（SkyT） 本地 GPU Markdown 会话归档节点，负责把完整历史会话整理成中文工程记录。"},
            {"role": "user", "content": prompt},
        ]
        response = await llm.chat_completion(messages, provider=model, is_background=True)
        markdown = response.choices[0].message.content or ""
        token_usage = getattr(response, "skyt_token_usage", None) or usage_from_openai_response(
            response,
            provider=model,
            role=f"markdown_archivist_session_{kind}",
            messages=messages,
            output_text=markdown,
            is_local=True,
        )
    except Exception as exc:
        markdown = fallback_session_markdown(session, kind) + f"\n\n> GPU 生成失败，已使用 fallback：{exc}\n"

    title = f"天韬（SkyT） 历史会话{label}: {session.get('title') or session_id}"
    report_id = db.save_report(title, markdown)
    saved_path = None

    if workspace:
        try:
            target_dir = Path(workspace) / ".skyt" / "important_work_logs"
            target_dir.mkdir(parents=True, exist_ok=True)
            safe_session_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session_id)
            target_path = target_dir / f"{safe_session_id}_{kind}.md"
            target_path.write_text(markdown, encoding="utf-8")
            saved_path = str(target_path)
        except Exception:
            saved_path = None

    return {
        "status": "success",
        "session_id": session_id,
        "kind": kind,
        "report_id": report_id,
        "saved_path": saved_path,
        "markdown_preview": markdown[:1200],
        "token_usage": token_usage,
    }
