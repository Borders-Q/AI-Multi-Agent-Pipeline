import csv
import io

def markdown_table_builder(csv_text: str):
    rows = list(csv.reader(io.StringIO(csv_text.strip())))
    rows = [[cell.strip() for cell in row] for row in rows if row]
    if not rows:
        return "没有可转换的数据。"
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

SCHEMA = {
    "name": "markdown_table_builder",
    "description": "把 CSV 风格文本转换为 Markdown 表格",
    "parameters": {
        "type": "object",
        "properties": {
            "csv_text": {"type": "string", "description": "逗号分隔文本，第一行为表头"}
        },
        "required": ["csv_text"]
    }
}
