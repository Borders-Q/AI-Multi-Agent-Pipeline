from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from skyt_platform.workspace_policy import WorkspaceViolation, resolve_inside


EXCLUDED = {".git", ".skyt", "__pycache__", ".pytest_cache", "node_modules"}


def _files(root: Path, base: Path):
    for item in root.rglob("*"):
        if any(part in EXCLUDED for part in item.relative_to(base).parts):
            continue
        if item.is_file() and not item.is_symlink():
            yield item


def create_checkpoint(workspace: str | None, run_id: str, label: str) -> dict:
    if not workspace:
        return {"kind": "none", "path": "", "label": label, "metadata": {"reason": "workspace_not_bound"}}
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("工作区不存在，无法创建检查点。")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    checkpoint = root / ".skyt" / "checkpoints" / run_id / stamp
    snapshot = checkpoint / "snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    manifest = []
    for source in _files(root, root):
        relative = source.relative_to(root)
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append(str(relative).replace("\\", "/"))
    git_commit = ""
    try:
        git_commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    metadata = {"run_id": run_id, "label": label, "git_commit": git_commit, "files": manifest}
    (checkpoint / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"kind": "git" if git_commit else "snapshot", "path": str(checkpoint), "label": label, "metadata": metadata}


def restore_checkpoint(checkpoint_path: str, workspace: str) -> dict:
    checkpoint = Path(checkpoint_path).resolve()
    root = Path(workspace).expanduser().resolve()
    metadata_path = checkpoint / "metadata.json"
    snapshot = checkpoint / "snapshot"
    if not metadata_path.is_file() or not snapshot.is_dir():
        raise ValueError("检查点不完整。")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    restored = 0
    expected = {str(item).replace("/", "\\") for item in metadata.get("files") or []}
    for relative in metadata.get("files") or []:
        source = snapshot / relative
        try:
            target = resolve_inside(root, relative)
        except WorkspaceViolation as exc:
            raise ValueError(f"检查点包含工作区外路径：{relative}") from exc
        if target.is_symlink():
            raise ValueError(f"拒绝覆盖符号链接：{relative}")
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored += 1

    removed = 0
    # A rollback must also remove files created after the checkpoint. Keep the
    # checkpoint store itself outside this pass via EXCLUDED.
    for current in list(_files(root, root)):
        relative = str(current.relative_to(root)).replace("/", "\\")
        if relative not in expected:
            current.unlink()
            removed += 1
    return {"restored": restored, "removed": removed, "checkpoint": str(checkpoint), "git_commit": metadata.get("git_commit", "")}
