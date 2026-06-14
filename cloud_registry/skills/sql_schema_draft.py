def sql_schema_draft(entity_name: str, fields: str = ""):
    table = entity_name.strip().lower().replace(" ", "_") or "records"
    field_names = [f.strip() for f in fields.replace("\n", ",").split(",") if f.strip()]
    lines = ["CREATE TABLE IF NOT EXISTS " + table + " (", "  id INTEGER PRIMARY KEY AUTOINCREMENT,"]
    if field_names:
        for name in field_names:
            safe = name.lower().replace(" ", "_")
            lines.append("  " + safe + " TEXT,")
    else:
        lines.extend(["  name TEXT NOT NULL,", "  category TEXT,", "  status TEXT,", "  remark TEXT,"])
    lines.append("  created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    lines.append(");")
    return "\n".join(lines)

SCHEMA = {
    "name": "sql_schema_draft",
    "description": "生成 SQLite 建表草稿",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string", "description": "实体或表名"},
            "fields": {"type": "string", "description": "字段名，逗号或换行分隔", "default": ""}
        },
        "required": ["entity_name"]
    }
}
