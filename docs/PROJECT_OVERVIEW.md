# Ai Multi Agent 项目总览

## 核心目标

Ai Multi Agent 的目标是做一个可用于比赛展示和本地开发协作的 AI 工作台。它不是普通聊天页面，也不是单纯的工作流编辑器，而是把以下能力放到同一个工作台里：

- 对话式任务入口。
- Codex 风格左侧会话栏、中间聊天区、右侧行动面板。
- 本地 GPU/Ollama 与云端 API 协作。
- 工作区绑定、文件读写、命令运行和后台服务启动。
- PowerShell、内置浏览器、执行/修复状态和推荐操作。
- Dashboard、History、Replay、Reports、Skills、Workflow Editor 等业务页面。
- 模型/API Key 配置和模型别名管理。

后续修改的重点应该是让核心闭环更稳定、更清晰、更适合展示，而不是继续堆无关功能。

## 已完成能力

- 前端壳层：`frontend/src/App.jsx` 已组织主工作台、左侧会话、路由、中间聊天和模型弹窗。
- 右侧行动面板：`frontend/src/components/ActionDock.jsx` 提供浏览器、PowerShell、工作区、执行/修复四个入口。
- 内置终端：`frontend/src/components/TerminalPanel.jsx` 通过 WebSocket 连接后端 PowerShell session。
- 内置浏览器：ActionDock 内部 `BrowserPanel` 通过 iframe 展示 URL，并用 `/api/browser/open-system` 作为兜底。
- 模型管理：前端 `ModelManager` 对接后端 `/api/models/add`、`/api/models/remove`、`/api/models`、`/api/models/alias`。
- 会话历史：`db.py` 中 `sessions`、`messages` 表支撑会话列表和历史消息。
- 运行记录：`run_records`、`run_events`、`reports` 支撑 Dashboard、History、Replay 和 Reports。
- 工作流：`frontend/src/views/WorkflowEditorPage.jsx` 和 `frontend/src/store/workflowStore.js` 支撑节点画布、属性面板和模板保存。
- 本地模型路由：`agent/router.py` 优先处理 NPU 快速意图、本地 GPU/Ollama 简单响应和云 API 复杂任务。
- 自主执行：`server.py` 的 `/api/chat` 支持 `autonomy_mode`，复杂任务在绑定工作区后进入 Codex 式主动执行。
- 工具安全：`agent/tools/fs_tools.py` 对危险命令、保护文件和部分高风险操作返回 `APPROVAL_REQUIRED`。

## 主要用户流程

### 对话到执行

```text
用户输入
  -> frontend/src/App.jsx ChatComposer
  -> POST /api/chat
  -> server.py chat_endpoint
  -> agent/router.py 判断 NPU/GPU/API 路由
  -> agent/workflow.py 或直接响应
  -> SSE 流式返回消息、步骤、工具调用和审批请求
  -> App.jsx 渲染聊天消息与 ExecutionSteps
```

### 工作区到主动修改

```text
绑定工作区
  -> /api/workspace/bind
  -> App.jsx 保存 workspacePath
  -> ChatRequest.workspace 传给后端
  -> AgentWorkflowEngine 工具调用
  -> agent/tools/fs_tools.py 读写、运行、启动服务
```

### 运行记录到展示

```text
Agent 执行
  -> db.create_run_record / save_run_event
  -> /api/dashboard/stats、/api/runs、/api/runs/{run_id}/events
  -> Dashboard / RunHistory / WorkflowReplay / Reports
```

## 核心文件

| 文件或目录 | 作用 |
| --- | --- |
| `server.py` | FastAPI 主入口、聊天、模型、工作区、终端、浏览器、Dashboard、运行记录接口 |
| `db.py` | MySQL 连接、表结构初始化、会话、消息、运行记录、报告、模型密钥保存 |
| `agent/router.py` | NPU/GPU/API 意图路由、本地 Ollama 选择、简单任务处理 |
| `agent/workflow.py` | 复杂任务执行循环、工具调用、运行事件、报告生成 |
| `agent/tools/fs_tools.py` | 文件读写、命令执行、后台服务和高风险动作拦截 |
| `agent/llm_client.py` | API Key 识别、多 Provider 客户端、本地 Ollama 客户端和流式调用 |
| `frontend/src/App.jsx` | 前端主壳层、聊天、侧边栏、路由、模型弹窗 |
| `frontend/src/components/ActionDock.jsx` | 右侧行动面板、浏览器、PowerShell、工作区、执行/修复 |
| `frontend/src/store/workflowStore.js` | 工作流节点、边、Agent 元信息和校验状态 |
| `frontend/src/views/*` | Dashboard、Reports、History、Replay、Skills、Workflow 页面 |

## 展示重点与辅助能力

比赛展示的主线应该集中在：

1. Codex 风格工作台体验。
2. 本地 GPU + 云 API 的协作路由。
3. 绑定工作区后的主动执行和安全确认。
4. Dashboard、执行步骤、运行记录、Replay、Reports 的可观察闭环。
5. Workflow Editor 作为可视化编排亮点。

辅助能力包括技能市场、内置浏览器、PowerShell、模型别名、报表列表等。它们用于增强可信度和可用性，但不应该抢走展示主线。
