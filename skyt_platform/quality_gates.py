from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from skyt_platform.workspace_policy import WorkspaceViolation, resolve_inside


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


async def _compile_workspace(workspace: str) -> dict:
    root = Path(workspace).resolve()
    if not root.is_dir():
        return {"passed": False, "message": "工作区不存在。"}
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "compileall", "-q", str(root),
        cwd=str(root), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return {"passed": False, "message": "Python 编译检查超时。"}
    return {
        "passed": process.returncode == 0,
        "message": "Python 编译检查通过。" if process.returncode == 0 else "Python 编译检查失败。",
        "stdout": stdout.decode(errors="replace")[-2000:],
        "stderr": stderr.decode(errors="replace")[-2000:],
    }


async def run_quality_gates(*, task: str, spec: dict, context: dict, workspace: str | None = None) -> dict:
    output = _text(context.get("output") or context.get("result") or context.get("last_output"))
    evidence = context.get("evidence") if isinstance(context.get("evidence"), list) else []
    gates = spec.get("quality_gates") or [{"type": "output_present", "required": True}]
    results: list[dict] = []
    for gate in gates:
        gate_type = str(gate.get("type") if isinstance(gate, dict) else gate)
        required = bool(gate.get("required", True)) if isinstance(gate, dict) else True
        result = {"type": gate_type, "required": required, "passed": True, "message": ""}
        if gate_type == "output_present":
            result["passed"] = bool(output.strip())
            result["message"] = "最终输出非空。" if result["passed"] else "最终输出为空。"
        elif gate_type == "evidence_recorded":
            result["passed"] = bool(evidence) or bool(context.get("verified"))
            result["message"] = "已记录验证证据。" if result["passed"] else "缺少验证证据。"
        elif gate_type == "workflow_success":
            result["passed"] = bool(context.get("workflow_success"))
            result["message"] = "所有未跳过节点均已通过。" if result["passed"] else "仍有节点未通过质量门禁。"
        elif gate_type in {"python_compile", "code_compile", "tests"}:
            result = {**result, **(await _compile_workspace(workspace) if workspace else {"passed": False, "message": "代码门禁需要绑定工作区。"})}
        elif gate_type in {"source_check", "research_evidence"}:
            urls = re.findall(r"https?://[^\s)\]>]+", output)
            result["passed"] = bool(urls) or bool(evidence)
            result["message"] = "已发现来源或证据。" if result["passed"] else "研究结果缺少可追溯来源。"
        elif gate_type == "artifact_exists":
            paths = gate.get("paths") if isinstance(gate, dict) else []
            if isinstance(paths, str):
                paths = [paths]
            try:
                result["passed"] = bool(workspace and paths and all(resolve_inside(workspace, str(path), allow_missing=False).is_file() for path in paths))
                result["message"] = "目标产物存在。" if result["passed"] else "目标产物不存在。"
            except WorkspaceViolation:
                result["passed"] = False
                result["message"] = "目标产物路径超出工作区。"
        elif gate_type == "task_specific":
            result["passed"] = bool(output.strip()) and not any(word in output.lower() for word in ("traceback", "exception", "执行失败", "错误"))
            result["message"] = "任务结果未发现明显失败信号。" if result["passed"] else "任务结果包含失败信号。"
        else:
            result["message"] = "未知门禁按非阻断检查记录。"
            result["passed"] = not required
        results.append(result)
    failed_required = [item for item in results if item.get("required") and not item.get("passed")]
    return {"passed": not failed_required, "results": results, "failed_required": failed_required}
