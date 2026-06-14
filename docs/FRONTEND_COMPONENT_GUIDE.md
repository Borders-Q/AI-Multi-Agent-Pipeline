# 前端功能与组件管理文档

本文用于快速定位 天韬（SkyT） 前端页面和组件，方便后续频繁修改 UI、弹窗、模型设置和比赛展示效果。

## 前端入口

| 文件 | 作用 |
| --- | --- |
| `frontend/src/main.jsx` | React 挂载入口 |
| `frontend/src/App.jsx` | 主工作台壳层、路由、会话、聊天、模型弹窗、状态管理 |
| `frontend/src/codex-workbench.css` | 当前 Codex 风格工作台主样式 |
| `frontend/src/App.css` | 业务页面和部分旧样式 |
| `frontend/src/index.css` | 全局基础样式和主题变量 |
| `frontend/src/i18n/zh.js` | 中文文案常量 |

## 当前页面

| 路由 | 页面文件 | 作用 |
| --- | --- | --- |
| `/` | `App.jsx` 内聊天工作区 | 主对话、执行步骤、Composer、工作区与模型选择 |
| `/dashboard` | `views/Dashboard.jsx` | 总览指标、Telemetry、运行、报告和图表 |
| `/history` | `views/RunHistory.jsx` | 运行历史列表 |
| `/replay/:runId` | `views/WorkflowReplay.jsx` | 按事件回放某次执行 |
| `/reports` | `views/Reports.jsx` | 报告列表和详情 |
| `/skills` | `views/SkillsStore.jsx` | 技能市场、导入、下载和启用状态 |
| `/workflows` | `views/Workflows.jsx` | 工作流模板列表 |
| `/workflows/editor` | `views/WorkflowEditorPage.jsx` | React Flow 工作流编辑器 |

## App.jsx 内部核心组件

| 组件 | 作用 | 重点状态 |
| --- | --- | --- |
| `Sidebar` | 左侧导航、会话历史、新建对话、模型设置、工作区状态 | `sessions`、`sessionId`、`workspacePath`、`isOpen` |
| `ModelManager` | 模型与 API Key 弹窗 | `models`、`newApiKey`、`editingProvider`、`editingAlias` |
| `ChatMessage` | 用户和 天韬（SkyT） 消息渲染 | `msg.role`、`msg.type`、`msg.routed_by` |
| `ExecutionSteps` | 步骤和日志卡片 | `activeWorkflow`、`actionLogs` |
| `ApprovalCard` | 危险动作或缺少工作区时的确认提示 | `approval_required` 事件 |
| `ChatComposer` | 底部多行输入、模型、工作流模式、工作区、发送/停止 | `input`、`provider`、`workflowMode`、`workspacePath`、`loading` |
| `OptionPopover` | Composer 中模型和模式选择小浮层 | `openPanel` |

### 模型/API Key 设置

相关文件：

- `frontend/src/App.jsx` 的 `ModelManager`。
- `server.py` 的 `/api/models/add`、`/api/models/remove`、`/api/models`、`/api/models/alias`。
- `db.py` 的 `api_keys` 表和 API Key 加密函数。

当前关闭方式：

- 点击右上角关闭按钮。
- 点击遮罩层关闭。
- 点击弹窗内部内容不会关闭。

后续修改时不要改变模型列表、添加 Key、删除 Key、别名编辑的核心逻辑，除非明确要改模型管理功能。

## 右侧 ActionDock

文件：

- `frontend/src/components/ActionDock.jsx`
- `frontend/src/components/ActionCard.jsx`
- `frontend/src/components/TerminalPanel.jsx`

四个固定入口：

| 入口 | 组件/逻辑 | 作用 |
| --- | --- | --- |
| 浏览器 | `BrowserPanel` | iframe 打开本地或外部 URL，失败时提示系统浏览器打开 |
| PowerShell | `TerminalPanel` | 通过 `/api/terminal/sessions` 和 WebSocket 连接后端 PowerShell |
| 工作区 | `WorkspacePanel` | 显示当前绑定目录，触发 `onBindWorkspace` |
| 执行/修复 | `WorkflowPanel` | 展示当前步骤和最近日志 |

推荐操作由 `recommendations` 数组生成，包括打开 Dashboard、运行构建、查看历史、新建对话。

## 工作流编辑器

文件：

- `frontend/src/views/WorkflowEditorPage.jsx`
- `frontend/src/store/workflowStore.js`
- `frontend/src/components/WorkflowEditor/Toolbar.jsx`
- `frontend/src/components/WorkflowEditor/NodePropertiesPanel.jsx`
- `frontend/src/components/WorkflowEditor/CustomAgentNode.jsx`
- `frontend/src/components/WorkflowEditor.css`

关系：

```text
WorkflowEditorPage
  -> useWorkflowStore
  -> ReactFlow 节点和边
  -> Toolbar 保存模板
  -> NodePropertiesPanel 编辑节点属性
  -> CustomAgentNode 渲染节点
  -> server.py /api/agents 和 /api/workflows/templates/*
```

`frontend/src/components/WorkflowEditor.jsx` 是较早的编辑器实现，当前主路由使用的是 `views/WorkflowEditorPage.jsx`。后续优先维护 `WorkflowEditorPage.jsx` 和 `workflowStore.js`。

## UI 基础组件

| 文件 | 作用 |
| --- | --- |
| `components/ui/BaseIconButton.jsx` | 图标按钮、tooltip 入口、active 状态 |
| `components/ui/AppTooltip.jsx` | hover 提示气泡 |
| `components/ui/BasePopover.jsx` | 点击触发的轻量弹层 |
| `components/ui/ConfirmDialog.jsx` | 确认对话框 |
| `components/ui/SidebarToggle.jsx` | 侧边栏折叠按钮 |
| `components/SessionItem.jsx` | 会话列表项 |
| `components/SystemTelemetry.jsx` | 系统资源卡片 |
| `components/MermaidChart.jsx` | Mermaid 渲染 |
| `components/WorkflowVisualizer.jsx` | 工作流可视化摘要 |

这些组件影响整体一致性，修改时优先保证深浅色、z-index、hover 状态和键盘关闭行为。

## 状态关系

`App.jsx` 是前端大部分状态的中心：

- `sessions`、`sessionId`、`messages` 管理会话。
- `models`、`provider`、`newApiKey` 管理模型。
- `workspacePath` 管理工作区。
- `activeWorkflow`、`actionLogs`、`currentPlanContent` 管理执行过程。
- `enabledSkills` 管理技能启用。
- `autonomyMode`、`workflowMode` 管理生成方式。

`workflowStore.js` 是工作流编辑器独立状态中心：

- 节点、边、Agent 列表。
- 当前选中节点和边。
- 节点属性、输入输出字段、CodeAgent 配置。
- 校验问题。

## 比赛展示核心组件

优先展示：

- `App.jsx` 主工作台。
- `ActionDock.jsx` 四格行动面板。
- `Dashboard.jsx` 指标和图表。
- `WorkflowEditorPage.jsx` 可视化编排。
- `WorkflowReplay.jsx` 执行回放。
- `Reports.jsx` 报告。

辅助组件：

- `SkillsStore.jsx` 技能市场。
- `TerminalPanel.jsx` 和 `BrowserPanel`，用于证明系统可直接操作本地环境。
- `ModelManager`，用于展示多模型/API Key 管理，但不应占据主线太久。

不建议随意改动：

- `App.jsx` 的 SSE 解析和消息状态合并。
- `workflowStore.js` 的节点结构和保存格式。
- `TerminalPanel.jsx` 的 WebSocket 协议。
- `ModelManager` 与 `/api/models/*` 的字段契约。

## 修改定位速查

- 想改按钮 hover 或 tooltip：看 `BaseIconButton.jsx`、`AppTooltip.jsx`、`codex-workbench.css`。
- 想改聊天气泡宽度和左右布局：看 `ChatMessage` 和 `.chat-message` 样式。
- 想改底部输入框：看 `ChatComposer` 和 `.chat-composer` 样式。
- 想改模型设置弹窗：看 `ModelManager` 和 `.model-manager-*` 样式。
- 想改左侧栏折叠：看 `Sidebar`、`SidebarToggle.jsx` 和 `.sidebar-*` 样式。
- 想改右侧栏折叠：看 `ActionDock.jsx` 和 `.action-dock-*` 样式。
- 想改 Dashboard 数据：看 `Dashboard.jsx` 和 `server.py` 的 `/api/dashboard/stats`。
- 想改工作流节点：看 `workflowStore.js`、`CustomAgentNode.jsx`、`NodePropertiesPanel.jsx`。
