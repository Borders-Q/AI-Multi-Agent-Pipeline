import json
import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import db
from agent.skill_workflow_importer import import_trae_skill_to_template
from agent.trae_skill_exporter import AGENT_SKILLS_DIR, build_skill_package, build_skill_zip, save_skill_to_workspace


def main():
    template = db.competition_workflow_templates()[0]
    package = build_skill_package(
        template["title"],
        template["description"],
        template["workflow_json"],
        template["template_id"],
    )
    zip_bytes = build_skill_zip(package)

    expected_prefix = f"{AGENT_SKILLS_DIR}/{package['skill_dir']}/"
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())
        assert f"{expected_prefix}SKILL.md" in names
        assert f"{expected_prefix}workflow.json" in names

    imported = import_trae_skill_to_template(f"{package['skill_name']}.zip", zip_bytes)
    original_workflow = json.loads(package["workflow_json"])
    assert imported["workflow_json"]
    assert len(imported["workflow"]["nodes"]) == len(original_workflow["nodes"])
    assert len(imported["workflow"]["edges"]) == len(original_workflow["edges"])
    assert imported["warnings"] == []

    tmp_dir = Path(tempfile.mkdtemp(prefix="skyt_trec_skill_"))
    try:
        expected_skill_root = tmp_dir / ".agents" / "skills"
        expected_target_dir = expected_skill_root / package["skill_dir"]
        expected_skill_path = expected_target_dir / "SKILL.md"
        expected_workflow_path = expected_target_dir / "workflow.json"

        for selected_dir in (tmp_dir, tmp_dir / ".agents", tmp_dir / ".agents" / "skills"):
            saved = save_skill_to_workspace(package, str(selected_dir))
            assert Path(saved["skill_root"]).resolve() == expected_skill_root.resolve()
            assert Path(saved["target_dir"]).resolve() == expected_target_dir.resolve()
            assert Path(saved["skill_path"]).resolve() == expected_skill_path.resolve()
            assert expected_skill_path.exists()
            assert expected_workflow_path.exists()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("Skill export package is Trec/SOLO-compatible, installable, and can be imported back.")


if __name__ == "__main__":
    main()
