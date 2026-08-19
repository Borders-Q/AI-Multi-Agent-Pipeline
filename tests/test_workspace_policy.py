from pathlib import Path

import pytest

from skyt_platform.workspace_policy import WorkspaceViolation, canonical_root, resolve_inside


def test_resolve_inside_accepts_relative_path(tmp_path: Path):
    root = canonical_root(tmp_path)
    assert resolve_inside(root, "src/main.py") == root / "src" / "main.py"


def test_resolve_inside_rejects_traversal(tmp_path: Path):
    with pytest.raises(WorkspaceViolation):
        resolve_inside(tmp_path, "../outside.txt")


def test_resolve_inside_rejects_absolute_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(WorkspaceViolation):
        resolve_inside(tmp_path, outside)
