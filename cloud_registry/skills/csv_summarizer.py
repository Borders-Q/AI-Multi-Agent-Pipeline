import csv
import io

def csv_summarizer(csv_text: str):
    rows = list(csv.reader(io.StringIO(csv_text.strip())))
    if not rows:
        return "CSV 为空。"
    width = max(len(row) for row in rows)
    empty_cells = sum(1 for row in rows for cell in row if not cell.strip())
    return "\n".join([
        "# CSV 摘要",
        "- 行数：" + str(len(rows)),
        "- 最大列数：" + str(width),
        "- 空单元格数：" + str(empty_cells),
        "- 表头：" + ("、".join(rows[0]) if rows else "无")
    ])

SCHEMA = {
    "name": "csv_summarizer",
    "description": "统计 CSV 行列和空值情况",
    "parameters": {
        "type": "object",
        "properties": {
            "csv_text": {"type": "string", "description": "CSV 文本"}
        },
        "required": ["csv_text"]
    }
}
