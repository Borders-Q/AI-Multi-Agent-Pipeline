# 天韬（SkyT） Workflow Template 导出 Trec/SOLO Skill 说明

## 目标

本功能用于比赛演示：把 天韬（SkyT） 中的 Workflow Template 或当前 Workflow Editor 画布，一键转换成 Trec/SOLO 可识别的项目级 Skill 包。它的价值不是复制运行记录，而是把“多 Agent 工作流的执行方法”沉淀成 Trec/SOLO 可以读取的 `SKILL.md`。

## 生成结构

下载模式会生成一个 zip，内部结构如下：

```text
.agents/
  skills/
    <skill-name>/
      SKILL.md
      workflow.json
```

安装到 Trec/SOLO 项目模式会写入：

```text
<workspace>/.agents/skills/<skill-name>/SKILL.md
<workspace>/.agents/skills/<skill-name>/workflow.json
```

`SKILL.md` 是给 Trec/SOLO Agent 阅读和执行的流程说明，`workflow.json` 只作为 天韬（SkyT） 原始节点结构的参考文件。

## 前端入口

- `/workflows`：选择某个比赛演示模板后，右侧详情区点击“导出 Trec/SOLO Skill”。
- `/workflows/editor`：编辑当前画布后，顶部工具栏点击“导出 Skill”。

模板页支持两种方式：

- “下载 Skill 包”：浏览器直接下载 zip。
- “安装到 Trec/SOLO 项目”：选择 Trec/SOLO 当前打开的项目根目录，并写入该目录下的 `.agents/skills/`。
- 如果误选了项目内的 `.agents` 或 `.agents/skills` 目录，后端会自动归一化到项目根，避免生成嵌套目录。

编辑器入口当前默认下载当前画布生成的 zip，适合快速演示“画布 -> Skill 包”的闭环。

## 后端接口

### 导出已有模板

```http
POST /api/workflows/templates/{template_id}/export-trae-skill
Content-Type: application/json

{
  "mode": "download",
  "workspace": null
}
```

`mode=download` 返回 zip；`mode=workspace` 写入 `<workspace>/.agents/skills/`。`workspace` 应传 Trec/SOLO 项目根目录。

### 导出当前编辑器工作流

```http
POST /api/workflows/export-trae-skill
Content-Type: application/json

{
  "title": "AI 工程生成流水线",
  "description": "用于比赛演示的多 Agent 工程生成流程",
  "workflow_json": { "nodes": [], "edges": [], "meta": {} },
  "mode": "download"
}
```

### 导入 Trec/SOLO Skill 为工作流模板

```http
POST /api/workflows/import-trae-skill-template
Content-Type: application/json

{
  "file_name": "ai-engineering-pipeline.zip",
  "content_base64": "<base64>",
  "save": true
}
```

导入接口由 `agent/skill_workflow_importer.py` 负责解析，优先读取包内 `workflow.json` 恢复原画布；如果只有 `SKILL.md`，则按 Markdown 中的步骤生成兜底工作流模板。导入过程只解析文件内容，不执行 Skill 代码。

### 系统技能转工作流模板

```http
POST /api/workflows/skills/{skill_name}/to-template
Content-Type: application/json

{
  "save": true
}
```

该接口把 Skills Store 中的系统技能 schema 转成“需求整理 Agent -> Skill 调用 Agent -> 结果总结 Agent”的三段式模板，适合比赛演示“技能也能被编排为工作流”的能力。

## Skill 内容规范

生成器位于 `agent/trae_skill_exporter.py`。它会把工作流转换为中文 `SKILL.md`，主要包含：

- YAML frontmatter：`name`、`description`。
- 适用场景：说明什么时候应该触发该 Skill。
- 推荐触发方式：来自模板 `meta.recommended_user_prompt`。
- 工作流策略：说明是否需要工作区、GPU、API、预览和落盘。
- 节点分工：按画布节点顺序列出每个 Agent 的职责、输入和输出。
- 执行步骤：把节点顺序转成 Trec/SOLO 可跟随的操作流程。
- 预期产出：来自模板 `meta.expected_outputs`。
- Replay / Report 展示重点：服务比赛讲解。
- 安全边界：写文件前确认工作区，危险操作需要用户确认，不展示模型隐藏推理链。

## 比赛演示路径

推荐演示顺序：

1. 打开 `/workflows`，选择 5 个比赛模板之一。
2. 展示模板节点、GPU/API 标签、Replay 和 Report 展示重点。
3. 点击“导出 Trec/SOLO Skill”，下载 zip。
4. 解压后展示 `SKILL.md`，说明 天韬（SkyT） 可以把可视化工作流沉淀成外部 Agent 工具可读的 Skill。
5. 再点击“导入 Skill 为模板”，上传刚才的 zip，展示模板可恢复到 Workflow Editor。
6. 点击“安装到 Trec/SOLO 项目”，选择 Trec/SOLO 项目根目录，展示 `.agents/skills/<skill-name>/` 结构。
7. 打开 Skills Store，选择一个系统技能并点击“转为工作流模板”，展示系统工具也能进入模板编排。

## 维护边界

- 不要把 `.env`、数据库、运行日志、缓存、历史消息或用户隐私文件打进 Skill 包。
- 不要把 天韬（SkyT） 内部工具实现直接复制进 Trec/SOLO Skill；本轮只导出流程说明和 `workflow.json` 参考结构。
- 不要把 Skill 写成宣传文案；它应该是 Agent 可执行的流程约束。
- 不要在 `SKILL.md` 中暴露模型隐藏推理链，只描述可见执行步骤和安全规则。
- 如果后续 Trec/SOLO Skill 格式变化，优先修改 `agent/trae_skill_exporter.py`，再同步本文件。
- 导入 Trec/SOLO Skill 的解析规则在 `agent/skill_workflow_importer.py`，不要把上传文件里的代码执行权接入后端。

## 核心文件

- `agent/trae_skill_exporter.py`：Skill 内容、slug、zip、工作区写入逻辑。
- `agent/skill_workflow_importer.py`：Trec/SOLO Skill 导入、系统技能转模板逻辑。
- `server.py`：导出、导入和系统技能转模板 API。
- `frontend/src/views/Workflows.jsx`：模板页导出与导入入口。
- `frontend/src/views/SkillsStore.jsx`：系统技能卡片“转为工作流模板”入口。
- `frontend/src/components/WorkflowEditor/Toolbar.jsx`：编辑器当前画布导出入口。
- `docs/SKYT_TRAE_SKILL_EXPORT.md`：本维护说明。
