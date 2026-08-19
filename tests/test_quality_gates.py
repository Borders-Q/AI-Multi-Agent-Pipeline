import asyncio

from skyt_platform.quality_gates import run_quality_gates


def test_quality_gates_reject_empty_output_and_unresolved_workflow():
    result = asyncio.run(run_quality_gates(
        task="完成任务",
        spec={"quality_gates": [
            {"type": "output_present", "required": True},
            {"type": "workflow_success", "required": True},
        ]},
        context={"output": "", "workflow_success": False},
    ))
    assert not result["passed"]
    assert {item["type"] for item in result["failed_required"]} == {"output_present", "workflow_success"}


def test_unknown_gate_is_non_blocking_when_optional():
    result = asyncio.run(run_quality_gates(
        task="任务",
        spec={"quality_gates": [{"type": "future_checker", "required": False}]},
        context={"output": "ok"},
    ))
    assert result["passed"]
