import asyncio
from types import SimpleNamespace

from skyt_platform.workflow_runtime import WorkflowRuntime


def test_ready_nodes_support_parallel_roots_and_condition_join():
    runtime = WorkflowRuntime()
    spec = {
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "join"}],
        "edges": [
            {"source": "a", "target": "join", "condition": "success == true"},
            {"source": "b", "target": "join", "condition": "success == true"},
        ],
    }
    ready, skipped = runtime._ready_nodes(spec, {"a", "b", "join"}, {})
    assert set(ready) == {"a", "b"}
    assert skipped == []
    ready, skipped = runtime._ready_nodes(spec, {"join"}, {"a": {"success": True}, "b": {"success": True}})
    assert ready == ["join"]
    assert skipped == []


def test_loop_scheduler_is_bounded():
    runtime = WorkflowRuntime()
    spec = {"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"id": "loop", "source": "a", "target": "b", "type": "loop", "loop_policy": {"maxIterations": 2}}]}
    pending, completed, outputs, counts = {"b"}, {"b": {"success": True}}, {"b": {"success": True}}, {}
    assert runtime._schedule_loops(spec, "a", {"success": True}, pending, completed, outputs, counts) == ["b"]
    assert runtime._schedule_loops(spec, "a", {"success": True}, pending, completed, outputs, counts) == ["b"]
    assert runtime._schedule_loops(spec, "a", {"success": True}, pending, completed, outputs, counts) == []


def test_failed_node_gets_unexecuted_repair_node():
    runtime = WorkflowRuntime()
    spec = {"nodes": [{"id": "execute", "kind": "executor", "label": "执行"}, {"id": "deliver", "kind": "synthesizer", "label": "交付"}], "edges": [{"id": "ed", "source": "execute", "target": "deliver"}]}
    new_spec, repair_ids = runtime._add_repair_nodes(spec, ["execute"], {"execute": {"success": False}}, 1)
    assert repair_ids == ["execute__repair_1"]
    repair = next(node for node in new_spec["nodes"] if node["id"] == repair_ids[0])
    assert repair["repair_for"] == "execute"
    assert any(edge["source"] == repair_ids[0] and edge["target"] == "deliver" for edge in new_spec["edges"])


def test_execute_can_repair_a_failed_node_without_database(monkeypatch):
    import skyt_platform.workflow_runtime as module

    spec = {
        "title": "repair test",
        "policy": {"max_retries_per_node": 0, "max_replans": 1, "max_model_calls": 8, "max_parallelism": 2},
        "quality_gates": [{"type": "output_present", "required": True}, {"type": "evidence_recorded", "required": True}],
        "nodes": [{"id": "execute", "kind": "executor", "label": "执行", "instruction": "执行"}],
        "edges": [],
    }
    run = {"run_id": "RUN_TEST", "status": "queued", "workflow_spec": spec, "input": {"task": "修复"}, "model_calls": 0, "replan_count": 0, "plan_revision": 1}
    node_records = []
    calls = {"count": 0}

    def get_run(run_id):
        return run

    def update_run(run_id, **fields):
        run.update(fields)
        return run

    def create_node(*args, **kwargs):
        node_records.append({"node_id": args[1], "attempt": args[2], "status": "running"})
        return len(node_records)

    def finish_node(node_run_id, *, status, output=None, error=None, evidence=None, provider=None):
        node_records[node_run_id - 1].update(status=status, output=output or {}, evidence=evidence or {}, provider=provider)

    class FakeMessage:
        tool_calls = None
        def __init__(self, content):
            self.content = content

    class FakeResponse:
        def __init__(self, content):
            self.choices = [SimpleNamespace(message=FakeMessage(content))]
            self.skyt_token_usage = {"total_tokens": 1}

    async def chat(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse("" if calls["count"] == 1 else "fixed result")

    monkeypatch.setattr(module.db, "get_workflow_run", get_run)
    monkeypatch.setattr(module.db, "update_workflow_run", update_run)
    monkeypatch.setattr(module.db, "get_workflow_node_runs", lambda run_id: list(node_records))
    monkeypatch.setattr(module.db, "create_workflow_node_run", create_node)
    monkeypatch.setattr(module.db, "finish_workflow_node_run", finish_node)
    monkeypatch.setattr(module.db, "save_run_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(module.db, "save_workflow_evaluation", lambda *args, **kwargs: None)
    monkeypatch.setattr(module.db, "replace_workflow_spec", lambda run_id, new_spec, **kwargs: run.update(workflow_spec=new_spec, replan_count=kwargs["replan_count"], plan_revision=kwargs["plan_revision"], status=kwargs.get("status", "queued")) or run)
    monkeypatch.setattr(module.db, "get_task", lambda task_id: None)
    monkeypatch.setattr(module.llm, "clients", {"fake": object()})
    monkeypatch.setattr(module.llm, "chat_completion", chat)
    monkeypatch.setattr(module.tool_manager, "get_openai_tools", lambda: [])

    result = asyncio.run(WorkflowRuntime().execute("RUN_TEST"))
    assert result["result"]
    assert run["status"] == "succeeded"
    assert run["replan_count"] == 1
    assert any(record["node_id"].startswith("execute__repair") for record in node_records)
