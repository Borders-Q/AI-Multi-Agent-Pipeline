# 天韬（SkyT） 对话输出结构

本文记录聊天窗口中输入框、执行步骤、最终回答和 Token 区域的 UI 规则。

## 输入框

`frontend/src/App.jsx::ChatComposer` 使用 textarea auto-resize：

- 短文本保持较小高度；
- 长文本自动增高；
- 最大高度约 220px；
- 超过后 textarea 内部滚动；
- 发送或清空后恢复默认高度。

## 输出层级

每条 AI 消息只保留一个主视觉容器：`message-body`。

`markdown-body` 只负责 Markdown 排版，不再作为第二层蓝色框。代码块、列表、标题和 Mermaid 仍由 Markdown renderer 处理。

## 执行步骤

执行步骤由 `ExecutionSteps` 渲染，独立于最终回答：

- 执行中默认展开；
- 执行结束后默认折叠；
- 用户可手动展开；
- 不展示隐藏推理链，只展示可理解的阶段摘要。

## Token 区域

Token 使用 `TokenUsageBadge` 单独显示，区分 API、本地和总计，并标记真实或估算来源。

## 核心文件

- `frontend/src/App.jsx`
- `frontend/src/codex-workbench.css`

## 后续维护

不要把执行日志塞回最终回答正文，也不要给 Markdown 正文增加新的嵌套卡片背景。
