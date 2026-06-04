# Ai Multi Agent 项目持续优化文档

本文用于后续开发、维护、继续生成代码和 vibe coding。它不是用户说明书，也不是宣传材料，而是帮助后续接手者快速理解“应该优化哪里、不要乱动哪里、如何验证”的维护文档。

## 当前整体优化目标

Ai Multi Agent 当前定位是比赛展示型 AI 工作台。优化方向应该围绕：

- 工作台使用体验更接近 Codex。
- 运行历史、深度回放和报告能清楚解释“系统做了什么”。
- 本地 GPU、云 API、工具调用和安全确认的关系更清晰。
- UI 在深色/浅色、左右侧栏展开/折叠、不同屏幕宽度下保持稳定。
- 后续 AI 编程助手进入项目时，不需要重新阅读整个项目。

不要把 Ai Multi Agent 重构成另一个项目，也不要为了展示复杂而堆无关功能。

## 当前已发现的问题

- 深度回放里的 `I/O JSON Payload` 原先是一整块 `detail_json` 代码块，输入、输出、元信息混在一起。
- 大段 JSON 虽然有格式化，但缺少复制、折叠、空状态、异常 JSON 回退和信息分区。
- 左侧会话历史区域被通用 `max-width: 210px` 规则限制，导致内容看起来过度靠左，右侧留白不自然。
- 顶部“智能对话 / 数据看板”等入口原先主要存在于左侧栏，主内容 header 只有当前页面标题，视觉重心偏左。

## 本次 I/O JSON Payload 优化记录

涉及文件：

- `frontend/src/views/WorkflowReplay.jsx`
- `frontend/src/codex-workbench.css`

原逻辑：

- `WorkflowReplay.jsx` 直接把 `selectedEvent.detail_json` 传给 `SyntaxHighlighter`。
- `formatJSON` 尝试 `JSON.parse`，失败就展示原字符串。
- 没有输入/输出区分，也没有复制、折叠和清晰空状态。

现逻辑：

- 新增 `safeParsePayload`：处理空值、标准 JSON、非标准字符串和异常 JSON。
- 新增 `splitPayload`：把字段启发式分成输入 Payload、输出 Payload、原始/元信息。
- 新增 `PayloadSection`：每个区块有标题、字段数量、复制按钮、折叠/展开和滚动代码区。
- 新增 `PayloadViewer`：统一承载 I/O Payload 展示。

字段划分原则：

- 输入优先：`args`、`arguments`、`input`、`inputs`、`request`、`requirement`、`prompt`、`messages`、`command`、`cwd`、`path`、`filePath`、`content` 等。
- 输出优先：`result`、`response`、`reply`、`output`、`stdout`、`stderr`、`error`、`summary`、`preview`、`code_preview` 等。
- 未识别字段和事件元信息保留在“原始 / 元信息”，避免展示优化导致信息丢失。

待确认：

- 后续如果后端开始明确输出 `input_payload` 和 `output_payload` 字段，前端应优先使用后端结构化字段，而不是继续只靠启发式拆分。

## 参考 D:\xjb-test 的可借鉴思路

只读参考内容：

- `frontend-vue/src/views/WorkflowReplay.vue`
- `frontend-vue/src/components/ReplayEventCard.vue`
- `frontend-vue/src/components/ReplayControlPanel.vue`

借鉴点：

- 回放页面把摘要、筛选、播放控制、时间线、当前事件拆成清晰层级。
- `ReplayEventCard` 对事件状态、Agent、CodeAgent、安全阻断和 detail 做分层展示。
- `detailJson` 使用折叠区域，避免大段数据默认撑开页面。
- 卡片内部对长内容设置最大高度和滚动。
- 搜索范围包含 `eventText`、`message` 和 `detailJson`。

没有照搬的内容：

- 没有迁移 Vue/Element Plus 组件。
- 没有迁移 Java Gateway 或 RunEvent 数据结构。
- 没有改 Ai Multi Agent 后端 API 和数据库。

## 运行历史 / 深度回放 / Payload 当前逻辑

当前链路：

```text
Agent 执行或工具调用
  -> db.save_run_event(run_id, event_type, agent, status, message, detail_json, duration_ms)
  -> GET /api/runs
  -> RunHistory.jsx 选择运行记录
  -> /replay/:runId
  -> WorkflowReplay.jsx 请求 /api/runs/{run_id}/events
  -> 时间线 + 当前事件详情 + PayloadViewer
```

核心文件：

- `server.py`：`/api/runs`、`/api/runs/{run_id}/events`。
- `db.py`：`run_records`、`run_events`、`save_run_event`、`get_run_events`。
- `frontend/src/views/RunHistory.jsx`：运行历史入口。
- `frontend/src/views/WorkflowReplay.jsx`：深度回放页面和 Payload 展示。
- `frontend/src/components/WorkflowVisualizer.jsx`：回放顶部可视化流程。

不要随意重构：

- 不要改变 `/api/runs/{run_id}/events` 的返回结构。
- 不要修改 `run_events.detail_json` 的数据库语义。
- 不要把回放页面改成只能依赖某一种事件类型。
- 不要为了 Payload 展示引入过重 JSON 编辑器依赖。

## 本次 UI 布局优化记录

### 左侧历史会话

涉及文件：

- `frontend/src/codex-workbench.css`

问题原因：

- `.session-list` 被放进了 `.brand-copy, .new-chat-button span, .sidebar-link span, .workspace-chip span, .session-list` 这组规则。
- 该规则设置了 `max-width: 210px`，而侧边栏宽度是 `292px`，所以历史区域不能充分使用侧边栏宽度。

本次方案：

- 将 `.session-list` 从通用 `max-width` 规则中拆出。
- 设置 `.session-list { width: 100%; max-width: none; }`。
- 优化 `.session-scroll`、`.session-item`、`.session-main` 的宽度、间距、删除按钮列宽和 padding。
- 不改 `SessionItem.jsx` 的选中、点击、删除逻辑。

### 深度回放主布局

涉及文件：

- `frontend/src/views/WorkflowReplay.jsx`
- `frontend/src/codex-workbench.css`

问题原因：

- Ai Multi Agent 工作台右侧 ActionDock 展开时，主内容区会变窄。
- 回放页原先固定使用 `400px` 时间线 + 右侧详情面板，在较窄主内容区里会把 I/O Payload 挤得很窄。

本次方案：

- 给回放页增加 `.workflow-replay-page`、`.replay-workspace-grid`、`.replay-timeline-panel`、`.replay-detail-panel`。
- 时间线宽度改为 `clamp(260px, 36%, 400px)`，宽屏保持左右并排。
- 使用 container query：当回放页可用宽度不足时，时间线和详情上下排列，Payload 独占更宽区域。
- 只调整布局承载方式，不改播放、筛选、事件选择和数据请求逻辑。

### 顶部导航入口

涉及文件：

- `frontend/src/App.jsx`
- `frontend/src/codex-workbench.css`

本次方案：

- 在 `App.jsx` 中新增 `getMainNavItems`，左侧栏和顶部导航复用同一组路由入口。
- 在 `.workspace-header` 中增加 `.workspace-top-nav`。
- 使用三栏 grid：左侧标题区、中间导航、右侧状态区。
- 小屏幕下隐藏 top nav，避免遮挡标题和后端错误提示。

维护注意：

- 顶部导航只改变入口展示位置，不改变路由。
- 如果后续新增页面，应同步检查 `getMainNavItems`。
- 如果比赛展示需要减少干扰，可以用 CSS 隐藏部分 top nav，但不要删除路由。

## 后续可继续优化的方向

- 为 `detail_json` 建立后端结构化规范，例如 `input_payload`、`output_payload`、`meta_payload`。
- 回放事件增加“只看工具调用”“只看失败”“只看写文件”等快捷筛选。
- 对 CodeAgent、NPU、GPU、Cloud API 使用更明确的状态颜色和图标。
- Dashboard 增加本地 GPU 命中次数、API Token 消耗、蒸馏节省估算。
- 把 `WorkflowReplay.jsx` 中大量 inline style 逐步迁移到 CSS 类，但不要一次性大重构。
- 继续检查深浅色主题下 tooltip、popover、弹窗和代码块的对比度。

## 比赛展示需要保留和突出

- 工作台三栏结构。
- 右侧 ActionDock 四格入口。
- 运行历史到深度回放的闭环。
- I/O Payload 的输入、输出、原始信息分区。
- 本地 GPU + API 协作逻辑。
- Workflow Editor 的可视化编排。
- 报告、Dashboard、Replay 形成的可观察链路。

辅助功能如技能市场、模型设置、终端和内置浏览器可以展示，但不应抢占比赛主线。
