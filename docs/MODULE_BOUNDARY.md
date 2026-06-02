# 模块划分与改动边界

本文用于判断后续修改应该落在哪个模块，并提醒哪些地方不要随意改。

## 前端工作台

路径：

- `frontend/src/App.jsx`
- `frontend/src/codex-workbench.css`
- `frontend/src/App.css`
- `frontend/src/index.css`
- `frontend/src/components/`
- `frontend/src/views/`

职责：

- 提供 Codex 风格工作台 UI。
- 管理会话、聊天、路由、模型弹窗、左侧栏和右侧 ActionDock。
- 展示 Dashboard、Reports、History、Replay、Skills、Workflow。
- 通过后端 API 获取数据，不直接访问数据库。

边界：

- 不在前端直接执行系统命令。
- 不在前端保存明文 API Key 到 localStorage。
- 不把后端运行逻辑写进 React 组件。
- UI 视觉调整优先保持工作台风格，不做大型营销页。

## 后端 API

路径：

- `server.py`

职责：

- 暴露 FastAPI REST、SSE 和 WebSocket。
- 连接前端、数据库、Agent、工具和系统能力。
- 处理模型配置、聊天、终端、浏览器、工作区、运行记录和报告。

边界：

- 不把所有复杂业务继续堆进接口函数。复杂 Agent 执行应在 `agent/workflow.py`。
- 不返回明文 API Key。
- 不绕过 `db.py` 直接散落 SQL。
- 修改接口返回结构时必须检查前端调用点。

## 数据访问

路径：

- `db.py`

职责：

- 初始化 MySQL 数据库和表结构。
- 加密保存 API Key。
- 保存会话、消息、运行记录、事件、报告、模板和蒸馏结果。

边界：

- 表结构变更要保持旧数据可兼容。
- 不在文档或日志输出密钥明文。
- 不把大块 UI 逻辑写入数据层。

## Agent 路由与执行

路径：

- `agent/router.py`
- `agent/workflow.py`
- `agent/llm_client.py`
- `agent/npu_classifier.py`

职责：

- 判断请求走 NPU、GPU、本地 Ollama还是云 API。
- 复杂任务执行、工具调用、事件记录和报告生成。
- Provider 和模型客户端管理。

边界：

- 不把本地 GPU 当成所有任务的替代品。
- 不让云 API 接收未经筛选的长日志和无关上下文。
- 不随意改变工具调用事件格式。
- 不在路由层写 UI 文案主逻辑，展示层文案优先放前端。

## 工具层

路径：

- `agent/tools/fs_tools.py`
- `agent/tools/web_skills.py`
- `agent/tools/http_tools.py`
- `agent/tools/project_tools.py`
- `agent/tools/report_tools.py`
- `agent/skills.py`

职责：

- 注册可供模型调用的工具。
- 提供文件读写、命令执行、后台服务、搜索、HTTP、报告等能力。
- 对高风险动作返回审批需求。

边界：

- 危险动作必须保留确认机制。
- `.env`、密钥文件、SSH/GPG 目录等保护路径不能静默覆盖。
- 后续新增工具必须有清晰参数和失败返回。
- 不把比赛展示文案和页面结构写在工具层。

## 工作流编辑器

路径：

- `frontend/src/views/WorkflowEditorPage.jsx`
- `frontend/src/store/workflowStore.js`
- `frontend/src/components/WorkflowEditor/`
- `server.py` 的 `/api/workflows/templates/*` 和 `/api/agents`
- `db.py` 的 `workflow_templates`、`agents`

职责：

- 提供节点库、画布、连线、属性面板和模板保存。
- 作为比赛展示中的“可视化编排”亮点。

边界：

- 不要把画布节点等同于完整真实 LangGraph 执行语义。
- 修改节点结构时同步检查保存、加载、校验和属性面板。
- 不要让 Workflow Editor 抢走聊天工作台主线。

## 右侧行动面板

路径：

- `frontend/src/components/ActionDock.jsx`
- `frontend/src/components/TerminalPanel.jsx`
- `server.py` 的终端、浏览器和工作区接口

职责：

- 提供浏览器、PowerShell、工作区、执行/修复四格入口。
- 展示推荐操作和当前执行状态。

边界：

- 浏览器 iframe 被拒绝嵌入时只做清晰 fallback。
- 终端是用户手动输入通道，Agent 自动执行仍走工具层和安全规则。
- 不把大量设置项塞进 ActionDock。

## 文档与生成产物

路径：

- `docs/`
- `README.md`
- `frontend/README.md`
- `outputs/`
- `logs/`
- `workspace/`

职责：

- `docs/` 维护项目结构、架构、演示、前端和 GPU/API 协作逻辑。
- `outputs/`、`logs/`、`workspace/` 是运行产物和用户工作空间。

边界：

- 不把 `outputs/`、`logs/`、`__pycache__`、`node_modules` 当成核心源码。
- 文档应记录当前真实结构，不写未实现的大型规划当作已完成能力。
- 比赛文档要突出核心价值，不堆所有辅助功能。
