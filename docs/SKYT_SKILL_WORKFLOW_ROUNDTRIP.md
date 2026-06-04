# Skill 与工作流模板双向转换说明

本文档面向后续维护和比赛演示，说明 Ai Multi Agent 如何完成“工作流模板 -> Trec/SOLO Skill -> 工作流模板”的闭环，以及系统技能大厅中的 Skill 如何转换为可编辑、可运行、可回放的 Workflow Template。

## 目标

本功能不是把 Trec/SOLO 或 Skills Store 重新实现一遍，而是让比赛演示可以清楚展示：

- 工作流模板可以导出为 Trec/SOLO 项目级 Skill；
- 导出的 Skill 可以再次导入 Ai Multi Agent，恢复成工作流模板；
- 系统技能大厅中的工具能力可以一键转换成三段式工作流模板；
- 转换后的模板可以继续进入 Workflow Editor、运行历史、深度回放和报告中心。

## 核心文件

- `agent/trae_skill_exporter.py`：把 Workflow Template / 当前编辑器工作流导出成 Trec/SOLO Skill 包。
- `agent/skill_workflow_importer.py`：解析 Trec/SOLO Skill zip、`SKILL.md`、`workflow.json`，并生成标准 `workflow_json`。
- `server.py`：提供导入、导出、系统技能转模板 API。
- `frontend/src/views/Workflows.jsx`：Workflow Templates 页面中的“导入 Skill 为模板”入口。
- `frontend/src/views/SkillsStore.jsx`：技能大厅中每个系统技能的“转为工作流模板”入口。
- `frontend/src/components/WorkflowEditor/Toolbar.jsx`：编辑器当前工作流导出 Skill 的入口。

## API

### 导出模板为 Trec/SOLO Skill

`POST /api/workflows/templates/{template_id}/export-trae-skill`

用途：把已保存模板导出为 Trec/SOLO Skill。

请求体：

```json
{
  "mode": "download",
  "workspace": "E:/demo/workspace"
}
```

`mode=download` 返回 zip；`mode=workspace` 保存到 `<workspace>/.agents/skills/<skill-name>/`。`workspace` 应传 Trec/SOLO 当前项目根目录。

### 导出当前编辑器工作流为 Trec/SOLO Skill

`POST /api/workflows/export-trae-skill`

用途：导出还没有保存成模板的编辑器当前工作流。

请求体包含 `title`、`description`、`workflow_json`、`mode`、`workspace`。

### 导入 Trec/SOLO Skill 为模板

`POST /api/workflows/import-trae-skill-template`

请求体：

```json
{
  "file_name": "ai-engineering-pipeline.zip",
  "content_base64": "<base64>",
  "save": true,
  "template_id": "",
  "title_override": ""
}
```

解析优先级：

1. zip 中存在 `workflow.json`：直接恢复原始 ReactFlow 工作流结构。
2. zip 中只有 `SKILL.md`：解析标题、frontmatter 和步骤，生成兜底工作流。
3. 直接上传 `workflow.json`：按模板结构导入。
4. 直接上传 `SKILL.md`：按 Markdown 步骤生成兜底模板。

注意：导入过程只解析文本和 JSON，不执行上传包中的任何代码。

### 系统技能转工作流模板

`POST /api/workflows/skills/{skill_name}/to-template`

用途：把 Skills Store 中的 OpenAI tool schema 转成三段式工作流。

默认节点：

1. 需求整理 Agent：提取用户意图、参数和约束。
2. Skill 工具调用 Agent：只围绕目标系统技能调用工具。
3. 结果总结 Agent：把工具输出整理成中文交付内容。

## 导出的 Trec/SOLO Skill 结构

安装到 Trec/SOLO 项目模式会生成：

```text
<workspace>/
  .agents/
    skills/
      <skill-name>/
        SKILL.md
        workflow.json
```

`SKILL.md` 包含：

- YAML frontmatter：`name`、`description`；
- 适用场景；
- 工作流目标；
- Agent 节点顺序；
- 每个 Agent 的职责、输入、输出；
- 比赛演示推荐输入；
- Replay / Report 展示重点；
- 安全边界。

## 导入后的模板约定

导入模板会保存到 `workflow_templates` 表，`stage` 为 `Imported`，`author` 为 `Ai Multi Agent User`。

导入自 Trec/SOLO Skill 的模板会带有：

- `meta.imported_from`；
- `meta.source_file`；
- `meta.imported_at`；
- `meta.template_name`；
- `meta.description`。

系统技能转模板会带有：

- `meta.imported_from = "system_skill"`；
- `meta.source_skill`；
- `toolSkillConfig`；
- `nodeType = "tool_skill"`。

## 比赛演示路径

推荐演示顺序：

1. 打开 Workflow Templates，选择一个官方比赛模板。
2. 点击“导出 Trec/SOLO Skill”，下载 zip 或安装到 Trec/SOLO 项目。
3. 再点击“导入 Skill 为模板”，上传刚才的 zip。
4. 模板列表出现导入模板，打开编辑器，说明节点、边和元信息被恢复。
5. 打开 Skills Store，选择 `web_search` 或 `write_file`，点击“转为工作流模板”。
6. 回到 Workflow Templates，展示系统技能被转换成可编辑工作流。

这条路径重点展示“模板、Skill、工作流、回放、报告”的工程化闭环，不需要现场解释 Trec/SOLO 的全部生态。

## 不要随意改动的边界

- 不要在导入 Skill 时执行任何上传代码。
- 不要把 Trec/SOLO Skill 的所有语义强行映射成 Ai Multi Agent 内部 Agent；无法识别时保持兜底节点和 warnings。
- 不要覆盖用户已有模板；导入模板使用新的 `template_id`。
- 不要把 `.env`、数据库、运行缓存、日志打包进 Trec/SOLO Skill。

## 后续可扩展点

- 增加导入预览，在保存前展示解析出的节点和 warnings。
- 支持把 `SKILL.md` 中更明确的“输入/输出/风险”段落映射到节点字段。
- 增加模板冲突处理，例如同名模板提示覆盖、另存或取消。
- 支持批量导入多个 Trec/SOLO Skill。
