from __future__ import annotations

import json


def _is_game_requirement(requirement: str) -> bool:
    text = (requirement or "").lower()
    keywords = ("贪吃蛇", "snake", "小游戏", "游戏", "game")
    return any(keyword in text for keyword in keywords)


def _infer_domain(requirement: str) -> dict:
    text = (requirement or "").lower()
    if any(key in text for key in ("图书", "书籍", "借阅", "library", "book")):
        return {
            "title": "图书管理系统",
            "entity": "book",
            "entity_plural": "books",
            "entity_cn": "图书",
            "fields": [
                ("title", "书名", "text", "必填"),
                ("author", "作者", "text", "必填"),
                ("category", "分类", "text", "可选"),
                ("isbn", "ISBN", "text", "可选"),
                ("stock", "库存", "number", "默认 1"),
                ("note", "备注", "text", "可选"),
            ],
        }
    if any(key in text for key in ("人员", "员工", "职工", "employee", "staff", "personnel")):
        return {
            "title": "人员管理系统",
            "entity": "employee",
            "entity_plural": "employees",
            "entity_cn": "人员",
            "fields": [
                ("name", "姓名", "text", "必填"),
                ("department", "部门", "text", "可选"),
                ("phone", "电话", "text", "可选"),
                ("role", "岗位", "text", "可选"),
                ("status", "状态", "text", "在职"),
                ("note", "备注", "text", "可选"),
            ],
        }
    return {
        "title": "信息管理系统",
        "entity": "item",
        "entity_plural": "items",
        "entity_cn": "记录",
        "fields": [
            ("name", "名称", "text", "必填"),
            ("category", "分类", "text", "可选"),
            ("owner", "负责人", "text", "可选"),
            ("status", "状态", "text", "可选"),
            ("note", "备注", "text", "可选"),
        ],
    }


def _slug_from_title(title: str) -> str:
    mapping = {
        "图书管理系统": "library_system",
        "人员管理系统": "personnel_system",
        "信息管理系统": "management_system",
    }
    return mapping.get(title, "flask_project")


def generate_flask_crud_blocks(requirement: str) -> list[dict]:
    """Generate a compact Flask project when an LLM node fails to produce files."""
    if _is_game_requirement(requirement):
        return generate_snake_game_blocks(requirement)

    domain = _infer_domain(requirement)
    title = domain["title"]
    entity = domain["entity"]
    plural = domain["entity_plural"]
    entity_cn = domain["entity_cn"]
    slug = _slug_from_title(title)
    fields = domain["fields"]
    field_names = [name for name, *_ in fields]

    columns_sql = ",\n            ".join(
        f"{name} {'INTEGER' if input_type == 'number' else 'TEXT'} {'NOT NULL' if rule == '必填' else ''}".strip()
        for name, _label, input_type, rule in fields
    )
    insert_cols = ", ".join(field_names)
    placeholders = ", ".join("?" for _ in fields)
    update_assignments = ", ".join(f"{name}=?" for name in field_names)
    required_checks = "\n    ".join(
        f"if not payload.get('{name}'):\n        return jsonify({{'error': '{label}不能为空'}}), 400"
        for name, label, _input_type, rule in fields
        if rule == "必填"
    ) or "pass"
    tuple_values = ", ".join(f"_clean(payload.get('{name}'))" for name in field_names)
    row_seed_values = ", ".join(repr(value) for value in _seed_values(domain))
    form_inputs = "\n          ".join(
        f'<label>{label}<input name="{name}" type="{input_type}" placeholder="{rule}" /></label>'
        for name, label, input_type, rule in fields
    )
    table_headers = "".join(f"<th>{label}</th>" for _name, label, _type, _rule in fields)
    js_fields = json.dumps(field_names, ensure_ascii=False)
    ts_type_fields = "\n  ".join(
        f"{name}: {'number' if input_type == 'number' else 'string'};"
        for name, _label, input_type, _rule in fields
    )

    app_py = f'''from flask import Flask, jsonify, render_template, request
import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "{slug}.db"

app = Flask(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _clean(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return value


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS {plural} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_sql},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        count = conn.execute("SELECT COUNT(*) AS total FROM {plural}").fetchone()["total"]
        if count == 0:
            conn.execute(
                "INSERT INTO {plural} ({insert_cols}) VALUES ({placeholders})",
                ({row_seed_values},)
            )
        conn.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/{plural}")
def list_items():
    keyword = _clean(request.args.get("q"))
    fields = {field_names!r}
    with get_conn() as conn:
        if keyword:
            where = " OR ".join([f"{{field}} LIKE ?" for field in fields])
            rows = conn.execute(
                f"SELECT * FROM {plural} WHERE {{where}} ORDER BY id DESC",
                tuple(f"%{{keyword}}%" for _ in fields)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM {plural} ORDER BY id DESC").fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/{plural}")
def create_item():
    payload = request.get_json(silent=True) or {{}}
    {required_checks}
    values = ({tuple_values},)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO {plural} ({insert_cols}) VALUES ({placeholders})",
            values
        )
        conn.commit()
    return jsonify({{"id": cur.lastrowid, "message": "{entity_cn}已创建"}}), 201


@app.put("/api/{plural}/<int:item_id>")
def update_item(item_id):
    payload = request.get_json(silent=True) or {{}}
    {required_checks}
    values = ({tuple_values}, item_id)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE {plural} SET {update_assignments} WHERE id=?",
            values
        )
        conn.commit()
    if cur.rowcount == 0:
        return jsonify({{"error": "{entity_cn}不存在"}}), 404
    return jsonify({{"message": "{entity_cn}已更新"}})


@app.delete("/api/{plural}/<int:item_id>")
def delete_item(item_id):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM {plural} WHERE id=?", (item_id,))
        conn.commit()
    if cur.rowcount == 0:
        return jsonify({{"error": "{entity_cn}不存在"}}), 404
    return jsonify({{"message": "{entity_cn}已删除"}})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
'''

    index_html = f'''<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div>
          <p>Flask / SQLite / JavaScript / TypeScript</p>
          <h1>{title}</h1>
          <span>支持新增、编辑、删除、搜索和状态管理，适合作为课程或比赛演示工程。</span>
        </div>
      </section>

      <section class="panel">
        <form id="item-form">
          <input type="hidden" name="id" />
          {form_inputs}
          <div class="actions">
            <button type="submit">保存{entity_cn}</button>
            <button type="button" id="reset-btn">清空</button>
          </div>
        </form>
      </section>

      <section class="panel">
        <div class="toolbar">
          <input id="search" placeholder="搜索{entity_cn}..." />
          <button id="search-btn">搜索</button>
          <button id="reload-btn">刷新</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th>{table_headers}<th>操作</th></tr>
            </thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
      </section>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
'''

    app_js = f'''const API = "/api/{plural}";
const fields = {js_fields};
const form = document.querySelector("#item-form");
const rows = document.querySelector("#rows");
const search = document.querySelector("#search");
const resetBtn = document.querySelector("#reset-btn");

async function requestJson(url, options = {{}}) {{
  const response = await fetch(url, {{
    headers: {{ "Content-Type": "application/json" }},
    ...options,
  }});
  const data = await response.json().catch(() => ({{}}));
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}}

function formData() {{
  const data = Object.fromEntries(new FormData(form).entries());
  fields.forEach((field) => {{
    if (field === "stock" && data[field] !== undefined) data[field] = Number(data[field] || 0);
  }});
  return data;
}}

function fillForm(item) {{
  form.elements.id.value = item.id;
  fields.forEach((field) => {{
    if (form.elements[field]) form.elements[field].value = item[field] || "";
  }});
  window.scrollTo({{ top: 0, behavior: "smooth" }});
}}

function resetForm() {{
  form.reset();
  form.elements.id.value = "";
}}

async function loadItems() {{
  const q = search.value.trim();
  const items = await requestJson(q ? `${{API}}?q=${{encodeURIComponent(q)}}` : API);
  rows.innerHTML = items.map((item) => `
    <tr>
      <td>${{item.id}}</td>
      ${{fields.map((field) => `<td>${{item[field] || ""}}</td>`).join("")}}
      <td class="row-actions">
        <button data-edit="${{item.id}}">编辑</button>
        <button data-delete="${{item.id}}">删除</button>
      </td>
    </tr>
  `).join("");
  rows.querySelectorAll("[data-edit]").forEach((btn) => {{
    btn.addEventListener("click", () => fillForm(items.find((item) => String(item.id) === btn.dataset.edit)));
  }});
  rows.querySelectorAll("[data-delete]").forEach((btn) => {{
    btn.addEventListener("click", async () => {{
      if (!confirm("确认删除这条{entity_cn}？")) return;
      await requestJson(`${{API}}/${{btn.dataset.delete}}`, {{ method: "DELETE" }});
      await loadItems();
    }});
  }});
}}

form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  const data = formData();
  const id = data.id;
  delete data.id;
  await requestJson(id ? `${{API}}/${{id}}` : API, {{
    method: id ? "PUT" : "POST",
    body: JSON.stringify(data),
  }});
  resetForm();
  await loadItems();
}});

document.querySelector("#search-btn").addEventListener("click", loadItems);
document.querySelector("#reload-btn").addEventListener("click", () => {{
  search.value = "";
  loadItems();
}});
resetBtn.addEventListener("click", resetForm);
loadItems().catch((error) => alert(error.message));
'''

    app_ts = f'''type {entity.title()} = {{
  id: number;
  {ts_type_fields}
  created_at?: string;
}};

type ApiMessage = {{
  message?: string;
  error?: string;
}};

const apiEndpoint: string = "/api/{plural}";
const editableFields: string[] = {js_fields};
'''

    style_css = _shared_dark_css()

    readme = f'''# {title}

这是 Ai Multi Agent 工程工作流兜底生成的 Flask + SQLite 演示项目。

## 功能

- {entity_cn}新增、编辑、删除、搜索
- SQLite 本地持久化
- HTML/CSS/JavaScript 前端交互
- TypeScript 类型源文件，便于后续接入构建工具

## 启动

```powershell
python -m pip install -r requirements.txt
python app.py
```

访问：http://127.0.0.1:5000
'''

    return [
        {"filename": "app.py", "lang": "python", "code": app_py},
        {"filename": "requirements.txt", "lang": "text", "code": "Flask>=3.0,<4.0\n"},
        {"filename": "templates/index.html", "lang": "html", "code": index_html},
        {"filename": "static/app.js", "lang": "javascript", "code": app_js},
        {"filename": "static/app.ts", "lang": "typescript", "code": app_ts},
        {"filename": "static/style.css", "lang": "css", "code": style_css},
        {"filename": "README.md", "lang": "markdown", "code": readme},
    ]


def generate_snake_game_blocks(requirement: str) -> list[dict]:
    app_py = '''from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
'''

    index_html = '''<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>贪吃蛇小游戏</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <main class="game-shell">
      <section class="hero">
        <p>Flask / Canvas / JavaScript / TypeScript</p>
        <h1>贪吃蛇小游戏</h1>
        <span>方向键或 WASD 控制移动，吃到食物加分，撞墙或撞到身体后可以一键重开。</span>
      </section>

      <section class="game-panel">
        <div class="hud">
          <strong>分数：<span id="score">0</span></strong>
          <strong>最高分：<span id="best-score">0</span></strong>
          <button id="restart-btn">重新开始</button>
        </div>
        <canvas id="game" width="520" height="520" aria-label="贪吃蛇游戏画布"></canvas>
        <p id="status">按方向键或 WASD 开始游戏。</p>
      </section>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
'''

    app_js = '''const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const scoreEl = document.querySelector("#score");
const bestScoreEl = document.querySelector("#best-score");
const statusEl = document.querySelector("#status");
const restartBtn = document.querySelector("#restart-btn");

const gridSize = 20;
const tileCount = canvas.width / gridSize;
let snake;
let food;
let direction;
let nextDirection;
let score;
let bestScore = Number(localStorage.getItem("snake_best_score") || 0);
let running;
let gameTimer;

bestScoreEl.textContent = String(bestScore);

function randomCell() {
  return {
    x: Math.floor(Math.random() * tileCount),
    y: Math.floor(Math.random() * tileCount),
  };
}

function spawnFood() {
  let candidate = randomCell();
  while (snake.some((part) => part.x === candidate.x && part.y === candidate.y)) {
    candidate = randomCell();
  }
  food = candidate;
}

function resetGame() {
  snake = [
    { x: 8, y: 10 },
    { x: 7, y: 10 },
    { x: 6, y: 10 },
  ];
  direction = { x: 1, y: 0 };
  nextDirection = { x: 1, y: 0 };
  score = 0;
  running = true;
  scoreEl.textContent = "0";
  statusEl.textContent = "游戏进行中，吃到蓝色能量块可以加分。";
  spawnFood();
  draw();
  clearInterval(gameTimer);
  gameTimer = setInterval(tick, 110);
}

function drawCell(cell, color, inset = 2) {
  ctx.fillStyle = color;
  ctx.fillRect(
    cell.x * gridSize + inset,
    cell.y * gridSize + inset,
    gridSize - inset * 2,
    gridSize - inset * 2
  );
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#07111f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i <= tileCount; i += 1) {
    ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
    ctx.beginPath();
    ctx.moveTo(i * gridSize, 0);
    ctx.lineTo(i * gridSize, canvas.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i * gridSize);
    ctx.lineTo(canvas.width, i * gridSize);
    ctx.stroke();
  }

  drawCell(food, "#60a5fa", 3);
  snake.forEach((part, index) => drawCell(part, index === 0 ? "#22c55e" : "#86efac"));
}

function endGame() {
  running = false;
  clearInterval(gameTimer);
  bestScore = Math.max(bestScore, score);
  localStorage.setItem("snake_best_score", String(bestScore));
  bestScoreEl.textContent = String(bestScore);
  statusEl.textContent = `游戏结束，最终得分 ${score}。点击重新开始继续挑战。`;
  draw();
}

function tick() {
  if (!running) return;
  direction = nextDirection;
  const head = {
    x: snake[0].x + direction.x,
    y: snake[0].y + direction.y,
  };

  const hitWall = head.x < 0 || head.y < 0 || head.x >= tileCount || head.y >= tileCount;
  const hitSelf = snake.some((part) => part.x === head.x && part.y === head.y);
  if (hitWall || hitSelf) {
    endGame();
    return;
  }

  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score += 10;
    scoreEl.textContent = String(score);
    spawnFood();
  } else {
    snake.pop();
  }

  draw();
}

function setDirection(x, y) {
  if (direction.x + x === 0 && direction.y + y === 0) return;
  nextDirection = { x, y };
}

document.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (key === "arrowup" || key === "w") setDirection(0, -1);
  if (key === "arrowdown" || key === "s") setDirection(0, 1);
  if (key === "arrowleft" || key === "a") setDirection(-1, 0);
  if (key === "arrowright" || key === "d") setDirection(1, 0);
});

restartBtn.addEventListener("click", resetGame);
resetGame();
'''

    app_ts = '''type Cell = {
  x: number;
  y: number;
};

type Direction = Cell;

type SnakeGameState = {
  snake: Cell[];
  food: Cell;
  direction: Direction;
  score: number;
  running: boolean;
};
'''

    style_css = '''* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  background:
    radial-gradient(circle at 20% 20%, rgba(96, 165, 250, 0.24), transparent 28%),
    linear-gradient(135deg, #07111f, #111827 52%, #0f172a);
  color: #e5e7eb;
}

.game-shell {
  width: min(980px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 44px;
}

.hero,
.game-panel {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.82);
  border-radius: 14px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
}

.hero {
  padding: 26px;
  margin-bottom: 18px;
}

.hero p {
  margin: 0 0 8px;
  color: #93c5fd;
}

.hero h1 {
  margin: 0 0 10px;
  font-size: clamp(30px, 5vw, 50px);
}

.hero span,
#status {
  color: #cbd5e1;
}

.game-panel {
  padding: 18px;
}

.hud {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

button {
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: #60a5fa;
  color: #07111f;
  font-weight: 800;
  cursor: pointer;
}

canvas {
  display: block;
  width: min(100%, 520px);
  aspect-ratio: 1;
  height: auto;
  border: 1px solid rgba(147, 197, 253, 0.42);
  border-radius: 12px;
  margin: 0 auto;
  background: #07111f;
}
'''

    readme = '''# 贪吃蛇小游戏

这是 Ai Multi Agent 工程工作流兜底生成的 Flask + HTML Canvas 贪吃蛇项目。

## 功能

- 方向键或 WASD 控制蛇移动
- 吃到食物加分
- 撞墙或撞到身体后失败
- 支持重新开始和本地最高分记录
- 包含 JavaScript 运行文件和 TypeScript 类型说明文件

## 启动

```powershell
python -m pip install -r requirements.txt
python app.py
```

访问：http://127.0.0.1:5000
'''

    return [
        {"filename": "app.py", "lang": "python", "code": app_py},
        {"filename": "requirements.txt", "lang": "text", "code": "Flask>=3.0,<4.0\n"},
        {"filename": "templates/index.html", "lang": "html", "code": index_html},
        {"filename": "static/app.js", "lang": "javascript", "code": app_js},
        {"filename": "static/app.ts", "lang": "typescript", "code": app_ts},
        {"filename": "static/style.css", "lang": "css", "code": style_css},
        {"filename": "README.md", "lang": "markdown", "code": readme},
    ]


def _shared_dark_css() -> str:
    return '''* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  background: #0f172a;
  color: #e5e7eb;
}

.shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 48px;
}

.hero,
.panel {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.78);
  border-radius: 14px;
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.28);
}

.hero {
  padding: 28px;
  margin-bottom: 18px;
}

.hero p {
  margin: 0 0 8px;
  color: #93c5fd;
}

.hero h1 {
  margin: 0 0 10px;
  font-size: clamp(28px, 4vw, 44px);
}

.hero span {
  color: #cbd5e1;
}

.panel {
  padding: 18px;
  margin-bottom: 18px;
}

form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

label {
  display: grid;
  gap: 6px;
  color: #cbd5e1;
}

input {
  width: 100%;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 11px 12px;
  background: #111827;
  color: #f8fafc;
}

.actions,
.toolbar {
  display: flex;
  gap: 10px;
  align-items: end;
  flex-wrap: wrap;
}

button {
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: #60a5fa;
  color: #07111f;
  font-weight: 700;
  cursor: pointer;
}

button:hover {
  filter: brightness(1.08);
}

.table-wrap {
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
}

th,
td {
  border-bottom: 1px solid #334155;
  padding: 12px;
  text-align: left;
  white-space: nowrap;
}

th {
  color: #93c5fd;
  background: rgba(96, 165, 250, 0.08);
}

.row-actions {
  display: flex;
  gap: 8px;
}
'''


def _seed_values(domain: dict) -> list[object]:
    values = []
    for name, _label, input_type, _rule in domain["fields"]:
        if input_type == "number":
            values.append(5)
        elif name == "title":
            values.append("示例图书")
        elif name == "name":
            values.append(f"示例{domain['entity_cn']}")
        elif name == "author":
            values.append("Ai Multi Agent")
        elif name == "category":
            values.append("默认分类")
        elif name == "isbn":
            values.append("9780000000000")
        elif name == "status":
            values.append("正常")
        elif name == "department":
            values.append("综合部")
        elif name == "phone":
            values.append("13800000000")
        elif name == "role":
            values.append("员工")
        else:
            values.append("")
    return values
