from pathlib import Path

from agent.tools.fs_tools import read_file, run_command, write_file


def test_file_tools_stay_inside_workspace(tmp_path: Path):
    assert "successfully written" in write_file("src/hello.txt", "hello", str(tmp_path))
    assert read_file("src/hello.txt", str(tmp_path)) == "hello"
    assert "APPROVAL_REQUIRED" in write_file("../escape.txt", "nope", str(tmp_path))


def test_command_tool_uses_workspace_and_approval_boundary(tmp_path: Path):
    result = run_command("python -c \"print('workspace-ok')\"", workspace=str(tmp_path))
    assert "workspace-ok" in result
    assert "APPROVAL_REQUIRED" in run_command("git reset --hard", workspace=str(tmp_path))
