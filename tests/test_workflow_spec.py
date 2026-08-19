import pytest

from skyt_platform.workflow_spec import (
    build_default_workflow_spec,
    normalize_workflow_spec,
    spec_to_legacy_workflow,
    validate_workflow_spec,
)


def test_legacy_workflow_is_normalized_and_roundtrips():
    legacy = {
        "nodes": [
            {"id": "a", "type": "customAgent", "data": {"label": "执行", "nodeType": "code_agent", "agentId": "code_agent"}},
            {"id": "b", "type": "customAgent", "data": {"label": "验证", "nodeType": "custom_agent", "agentId": "critic"}},
        ],
        "edges": [{"id": "e", "source": "a", "target": "b", "data": {"edgeType": "control"}}],
        "meta": {"template_name": "旧模板"},
    }

    spec = normalize_workflow_spec(legacy)
    assert spec["spec_version"] == 2
    assert spec["title"] == "旧模板"
    assert spec["nodes"][0]["kind"] == "executor"
    assert not [item for item in validate_workflow_spec(spec) if item["severity"] == "error"]
    assert len(spec_to_legacy_workflow(spec)["nodes"]) == 2


def test_cycle_requires_explicit_bounded_loop():
    spec = build_default_workflow_spec("测试循环")
    spec["edges"].extend([
        {"id": "x", "source": "s1", "target": "s2"},
        {"id": "y", "source": "s2", "target": "s1"},
    ])
    spec["nodes"].extend([
        {"id": "s1", "kind": "agent", "label": "一", "agent_id": "a"},
        {"id": "s2", "kind": "agent", "label": "二", "agent_id": "b"},
    ])
    issues = validate_workflow_spec(spec)
    assert any(item["code"] == "CYCLE_WITHOUT_LOOP" for item in issues)


def test_loop_edge_requires_positive_iteration_limit():
    spec = {
        "nodes": [
            {"id": "start", "kind": "agent", "label": "开始"},
            {"id": "a", "kind": "agent", "label": "入口"},
            {"id": "b", "kind": "agent", "label": "循环"},
        ],
        "edges": [
            {"id": "sa", "source": "start", "target": "a"},
            {"id": "ab", "source": "a", "target": "b"},
            {"id": "ba", "source": "b", "target": "a", "type": "loop"},
        ],
    }
    assert any(item["code"] == "LOOP_WITHOUT_LIMIT" for item in validate_workflow_spec(spec))
    spec["edges"][2]["loop_policy"] = {"maxIterations": 2}
    assert not any(item["severity"] == "error" for item in validate_workflow_spec(spec))
