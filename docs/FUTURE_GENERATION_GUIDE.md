# 后续生成逻辑说明

本文给后续 AI 或开发者使用，目标是避免每次修改都重新阅读整个项目，也避免把 天韬（SkyT） 改偏。

## 修改前阅读顺序

1. `README.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/SYSTEM_ARCHITECTURE.md`
4. `docs/MODULE_BOUNDARY.md`
5. 本文
6. 如果改前端，再读 `docs/FRONTEND_COMPONENT_GUIDE.md`
7. 如果改比赛展示，再读 `docs/COMPETITION_VISUAL_GUIDE.md`
8. 如果改模型路由或 Token 策略，再读 `docs/GPU_API_COLLABORATION.md`

## 基本生成原则

- 先理解现有结构，再做小范围修改。
- 不重新开发整个项目。
- 不把 天韬（SkyT） 改造成参考项目 `D:\xjb-test` 的架构。
- 不为了比赛展示堆无关功能。
- 改 UI 时保持 Codex 风格工作台，不做独立营销首页。
- 改后端时保持 `server.py` 为接口入口，复杂 Agent 逻辑放 `agent/`。
- 改模型路由时坚持本地 GPU 辅助 API，而不是一刀切。
- 改工具能力时保留高风险动作确认。

## 常见任务应该看哪里

| 任务 | 优先查看 |
| --- | --- |
| 模型/API Key 弹窗 | `frontend/src/App.jsx` 的 `ModelManager`、`server.py` 的 `/api/models/*`、`db.py` 的 `api_keys` |
| 聊天输入、发送、停止 | `frontend/src/App.jsx` 的 `ChatComposer`、`handleSend`、`stopChat`、`server.py` 的 `/api/chat` |
| 左侧会话栏 | `frontend/src/App.jsx` 的 `Sidebar`、`SessionItem.jsx`、`db.py` 的 `sessions/messages` |
| 右侧四格面板 | `frontend/src/components/ActionDock.jsx`、`TerminalPanel.jsx`、`server.py` 的终端和浏览器接口 |
| Dashboard 报错或空白 | `frontend/src/views/Dashboard.jsx`、`server.py` 的 `/api/dashboard/stats`、`/api/telemetry`、`/api/runs` |
| Workflow Editor | `frontend/src/views/WorkflowEditorPage.jsx`、`frontend/src/store/workflowStore.js`、`frontend/src/components/WorkflowEditor/*` |
| Skills | `frontend/src/views/SkillsStore.jsx`、`server.py` 的 `/api/skills*`、`cloud_registry/` |
| 运行记录/回放 | `frontend/src/views/RunHistory.jsx`、`WorkflowReplay.jsx`、`db.py` 的 `run_records/run_events` |
| Agent 自动执行 | `server.py` 的 `/api/chat`、`agent/workflow.py`、`agent/tools/fs_tools.py` |
| 本地 GPU 路由 | `agent/router.py`、`agent/llm_client.py`、`agent/npu_classifier.py` |

## 前端生成规则

- 新页面优先放在 `frontend/src/views/`，并在 `App.jsx` 添加 Route。
- 可复用 UI 控件放在 `frontend/src/components/` 或 `frontend/src/components/ui/`。
- 不在业务页面里复制 ActionDock、Sidebar、Composer 的壳层逻辑。
- 弹窗优先复用现有遮罩、`BaseIconButton` 和主题变量。
- tooltip、popover、按钮样式必须跟随深浅色主题。
- 文字不要塞满界面，比赛主线页面应减少说明文字，靠层级和状态表达。

## 后端生成规则

- 新接口优先集中在 `server.py`，并保持接口返回结构简单。
- 数据持久化通过 `db.py` 新增函数，不在多个文件散写 SQL。
- Agent 工具必须通过 `agent/skills.py` 注册。
- 文件、命令、后台服务相关能力优先扩展 `agent/tools/fs_tools.py`。
- 高风险动作必须返回审批需求，不得静默执行。
- 不在日志、响应和文档中输出 API Key 明文。

## 自主执行规则

默认模式是 `supervised_auto`：

- 允许在绑定工作区内读写文件。
- 允许运行测试、构建、安装项目依赖和启动本地服务。
- 未绑定工作区时，不应自动写文件。
- 递归删除、格式化、覆盖密钥文件、写工作区外、全局安装、发布、强推、杀非项目进程必须确认。

实现上必须同时关注：

- `server.py` 中 `ChatRequest.autonomy_mode` 和 `/api/chat`。
- `agent/workflow.py` 中工具调用循环。
- `agent/tools/fs_tools.py` 中危险动作识别和 `APPROVAL_REQUIRED`。
- 前端对 `approval_required` SSE 事件的展示。

## 文档同步规则

修改后根据影响范围同步：

- 改前端组件：更新 `FRONTEND_COMPONENT_GUIDE.md`。
- 改架构或接口：更新 `SYSTEM_ARCHITECTURE.md`。
- 改模块边界或安全策略：更新 `MODULE_BOUNDARY.md`。
- 改比赛展示页面或演示路径：更新 `COMPETITION_VISUAL_GUIDE.md`。
- 改模型路由、本地 GPU、Token 策略：更新 `GPU_API_COLLABORATION.md`。
- 较大改动追加到 `GENERATION_HISTORY.md`。

## 最低验证

常规前端修改：

```powershell
cd E:\比赛\AI Mu\frontend
npm run build
```

常规后端修改：

```powershell
cd E:\比赛\AI Mu
python -m py_compile server.py db.py agent\workflow.py agent\router.py agent\llm_client.py agent\tools\fs_tools.py
```

手动验收重点：

- 首页能进入工作台。
- 会话切换、新建对话、发送消息、停止生成可用。
- 模型/API Key 弹窗能打开、关闭、点击内部不误关闭。
- Dashboard、Reports、Skills、History、Replay、Workflow Editor 路由不空白。
- 右侧浏览器、PowerShell、工作区、执行/修复入口可点击。
- 复杂任务未绑定工作区时能给出绑定提示。
- 高风险动作能触发确认，而不是静默执行。
