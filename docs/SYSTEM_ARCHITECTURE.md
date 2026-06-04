# Ai Multi Agent 系统架构

## 总体结构

```text
frontend/
  React + Vite + React Router
  App.jsx / ActionDock / Dashboard / Workflow Editor

server.py
  FastAPI REST + SSE + WebSocket
  模型、聊天、工作区、终端、浏览器、运行记录、报告、技能接口

db.py
  MySQL 表结构与数据访问
  sessions / messages / api_keys / run_records / run_events / reports / workflow_templates / distilled_knowledge

agent/
  router.py       NPU/GPU/API 路由
  llm_client.py   OpenAI-compatible Provider 管理和 Ollama 客户端
  workflow.py     复杂任务工具循环
  tools/          文件、命令、HTTP、搜索、报告、项目工具
  memory.py       长期记忆
  compactor.py    上下文压缩预留
  distillation_worker.py  空闲蒸馏
```

## 前端层

前端是一个工作台壳层，入口为 `frontend/src/App.jsx`。它负责：

- 会话列表、新建对话、切换历史。
- 聊天消息、流式执行日志、审批卡片和 Composer。
- Dashboard、History、Reports、Skills、Workflow 等路由。
- 模型/API Key 弹窗。
- 工作区绑定和发送时携带 `workspace`。
- 右侧 ActionDock 的状态传递。

`frontend/src/codex-workbench.css` 是当前 Codex 风格视觉的主要承载文件。系统深浅色、侧边栏、按钮、弹窗、tooltip、composer、ActionDock 的大部分视觉都应该优先在这里维护。

## 后端接口层

`server.py` 是当前唯一后端主入口。核心接口分组如下：

| 分组 | 接口 | 作用 |
| --- | --- | --- |
| 模型 | `/api/models/*` | 添加、删除、列出模型/API Key，更新别名 |
| 会话 | `/api/sessions`、`/api/history/*` | 会话列表、历史消息、清空历史 |
| 聊天 | `/api/chat`、`/api/chat/stop/{session_id}` | SSE 对话、停止生成 |
| 工作区 | `/api/workspace/bind`、`/api/workspace/run` | 绑定目录、运行工作区命令 |
| 终端 | `/api/terminal/sessions`、WebSocket、DELETE | 创建、连接、关闭 PowerShell 会话 |
| 浏览器 | `/api/browser/open-system` | iframe 失败时用系统浏览器打开 |
| 工作流 | `/api/workflows/templates/*`、`/api/agents` | 模板和 Agent 节点来源 |
| 运行展示 | `/api/dashboard/stats`、`/api/runs`、`/api/runs/{run_id}/events` | Dashboard、History、Replay |
| 报告 | `/api/reports`、`/api/reports/{report_id}` | 报告列表和详情 |
| 技能 | `/api/skills`、`/api/skills/market`、`/api/skills/import` | 工具和技能市场 |

## 模型路由层

Ai Multi Agent 的模型路由不是“所有请求都上 API”。当前策略是：

```text
用户请求
  -> NPU 快速规则
  -> 本地 GPU/Ollama 简单生成、润色、工具搜索
  -> 云端 API 复杂任务、强制 API、审批后执行
```

相关文件：

- `agent/npu_classifier.py`：轻量意图和问候判断。
- `agent/router.py`：路由规则、本地 Ollama 模型发现、简单任务处理。
- `agent/llm_client.py`：Provider 和模型客户端管理。
- `server.py`：`/api/chat` 中决定是否进入 `AgentWorkflowEngine`。

## 复杂任务执行层

复杂任务进入 `agent/workflow.py` 的 `AgentWorkflowEngine.execute_dag`。它会：

- 创建 `run_id` 并写入 `run_records`。
- 加载长期记忆和最近会话历史。
- 根据 `enabled_skills` 选择工具。
- 流式调用模型。
- 执行工具调用并写入 `run_events`。
- 遇到 `APPROVAL_REQUIRED` 时把审批事件发回前端。
- 生成报告并更新运行记录。

工具调用集中由 `agent/skills.py` 注册和分发，文件与命令能力主要在 `agent/tools/fs_tools.py`。

## 数据层

`db.py` 负责建表和数据访问。当前核心表：

- `api_keys`：加密保存 API Key、provider、模型名和别名。
- `sessions`：会话和会话级工作流 JSON。
- `messages`：聊天历史、消息类型和路由来源。
- `run_records`：每次执行的摘要、质量分、Token。
- `run_events`：步骤、工具调用、错误、耗时和详情。
- `reports`：生成报告。
- `distilled_knowledge`：运行日志蒸馏结果。
- `workflow_templates`：工作流模板。
- `agents`：工作流节点库。

不要在前端绕过后端直接访问数据库。

## 稳定契约

后续修改时尽量保持这些契约稳定：

- `/api/chat` 返回 SSE 事件，前端依赖 `type`、`response`、`status`、`routed_by`、`node`、`state`。
- `ChatRequest` 中 `workspace` 和 `autonomy_mode` 影响是否允许主动执行。
- `/api/models` 返回 `{ models: [{ provider, model, alias }] }`。
- `/api/terminal/sessions` 返回 `{ session_id, cwd, shell }`，WebSocket 使用 JSON 事件。
- `run_records` 和 `run_events` 支撑 Dashboard、History、Replay，不要随意改字段语义。
- `agent/tools/fs_tools.py` 对保护文件和危险命令返回 `[APPROVAL_REQUIRED]`，前端据此展示确认需求。

## 当前限制

- 终端是命令级 WebSocket，不是完整 PTY；交互式程序可能不适合在其中运行。
- 内置浏览器优先 iframe，外站可能因安全策略拒绝嵌入，需要用系统浏览器兜底。
- 本地 GPU/Ollama 的质量取决于本机模型和服务状态。
- 自动依赖安装和后台服务启动需要谨慎使用，比赛展示前应提前验证。
- `agent/tools/fs_tools.py` 当前允许绝对路径写入，但保护文件和危险命令会拦截。后续若强化安全，应围绕绑定工作区做边界收紧。
