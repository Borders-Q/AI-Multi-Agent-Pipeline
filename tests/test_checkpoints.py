from pathlib import Path

from skyt_platform.checkpoints import create_checkpoint, restore_checkpoint


def test_snapshot_restore_removes_files_created_after_checkpoint(tmp_path: Path):
    original = tmp_path / "src" / "main.py"
    original.parent.mkdir()
    original.write_text("before", encoding="utf-8")
    checkpoint = create_checkpoint(str(tmp_path), "RUN_TEST", "before-change")

    original.write_text("after", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new", encoding="utf-8")
    restored = restore_checkpoint(checkpoint["path"], str(tmp_path))

    assert original.read_text(encoding="utf-8") == "before"
    assert not (tmp_path / "new.txt").exists()
    assert restored["restored"] >= 1
    assert restored["removed"] >= 1
