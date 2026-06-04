import json
import zipfile
from io import BytesIO

import db
from agent.skill_workflow_importer import import_trae_skill_to_template
from agent.trae_skill_exporter import AGENT_SKILLS_DIR, build_skill_package, build_skill_zip


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

    print("Skill export package is Trec/SOLO-compatible and can be imported back.")


if __name__ == "__main__":
    main()
