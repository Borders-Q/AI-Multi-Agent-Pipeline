from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from skyt_platform.workflow_spec import build_default_workflow_spec, validate_workflow_spec


ROOT = Path(__file__).resolve().parent


async def main() -> int:
    cases = json.loads((ROOT / "tasks.json").read_text(encoding="utf-8"))
    reports = []
    for case in cases:
        spec = build_default_workflow_spec(case["goal"], title=case["title"], policy={"max_model_calls": 1})
        issues = validate_workflow_spec(spec)
        errors = [item for item in issues if item.get("severity") == "error"]
        reports.append({
            "id": case["id"],
            "category": case["category"],
            "compiled": not errors,
            "source": "offline-heuristic",
            "node_count": len(spec.get("nodes") or []),
            "validation_errors": errors,
        })
    summary = {
        "offline": True,
        "case_count": len(reports),
        "compiled_count": sum(1 for report in reports if report["compiled"]),
        "success_rate": (sum(1 for report in reports if report["compiled"]) / len(reports)) if reports else 0,
        "reports": reports,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["compiled_count"] == summary["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
