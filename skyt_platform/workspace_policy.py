from __future__ import annotations

import os
from pathlib import Path


class WorkspaceViolation(ValueError):
    """Raised when an operation would leave the bound workspace."""


def canonical_root(value: str | os.PathLike[str]) -> Path:
    path = Path(value).expanduser()
    if not path.exists():
        raise WorkspaceViolation(f"工作区不存在：{path}")
    if not path.is_dir():
        raise WorkspaceViolation(f"工作区不是目录：{path}")
    return path.resolve()


def resolve_inside(root: str | os.PathLike[str], candidate: str | os.PathLike[str], *, allow_missing: bool = True) -> Path:
    root_path = canonical_root(root)
    raw = Path(candidate).expanduser()
    target = raw if raw.is_absolute() else root_path / raw
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise WorkspaceViolation(f"路径超出工作区：{candidate}") from exc
    if not allow_missing and not resolved.exists():
        raise WorkspaceViolation(f"路径不存在：{candidate}")
    return resolved


def ensure_directory(root: str | os.PathLike[str], candidate: str | os.PathLike[str] | None = None) -> Path:
    target = canonical_root(root) if candidate in (None, "") else resolve_inside(root, candidate)
    target.mkdir(parents=True, exist_ok=True)
    return target
