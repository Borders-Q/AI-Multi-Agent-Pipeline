# 生成过程记录

本文记录 Ai Multi Agent 已有生成思路和本轮整理结果，方便后续 AI 或开发者继续接手时理解项目为什么长成现在这样。

## 早期方向

Ai Multi Agent 早期目标是构建一个本地 AI 智能体系统，核心强调：

- Ai Multi Agent 作为本地 AI 中枢。
- NPU/GPU/API 分层协作。
- 工具调用、技能市场和本地执行能力。
- 对话、工作流、报告和可视化展示。

项目中保留了一些修复脚本、日志、测试文件和输出产物，例如 `fix_*.py`、`logs/`、`outputs/`。这些文件反映了生成和调试过程，但不是后续维护的主要入口。

## Codex 风格工作台改造

后续生成把前端从普通聊天界面改成更接近 Codex 的工作台：

- 左侧：会话、导航、模型设置、工作区状态。
- 中间：聊天流、执行步骤、Composer。
- 右侧：ActionDock，包含浏览器、PowerShell、工作区、执行/修复。
- Dashboard、Reports、Skills、Workflow 等业务页面继续保留，通过路由嵌入新壳层。

对应核心文件：

- `frontend/src/App.jsx`
- `frontend/src/codex-workbench.css`
- `frontend/src/components/ActionDock.jsx`
- `frontend/src/components/TerminalPanel.jsx`
- `frontend/src/components/ui/*`

## 主动执行能力

Ai Multi Agent 的“手伸得更长”主要体现在：

- `/api/chat` 支持 `autonomy_mode`，默认 `supervised_auto`。
- 绑定工作区后，复杂任务可直接进入 `AgentWorkflowEngine`。
- Agent 可调用文件、命令、后台服务等工具。
- 高风险动作由 `agent/tools/fs_tools.py` 返回 `[APPROVAL_REQUIRED]`，不静默执行。

这条路线的目标是让普通读写、运行、安装、启动服务更主动，同时保留删除、覆盖密钥、强推、全局安装等危险动作的确认边界。

## 本轮修复记录

本轮先修复“模型与 API Key”弹窗无法关闭问题：

- 修改 `frontend/src/App.jsx` 的 `ModelManager`。
- 给 `.modal-backdrop` 增加 `onClick={onClose}`。
- 给 `.codex-modal.model-manager-modal` 增加 `onClick={(event) => event.stopPropagation()}`。
- 保留原有右上角关闭按钮和所有模型/API Key 配置逻辑。

这样实现的原因是：问题只在关闭交互，不需要重构弹窗系统；遮罩层负责关闭，弹窗内部阻止冒泡，可以保证点击输入框、按钮、模型卡片时不误关闭。

后续如果继续修改该弹窗，优先查看：

- `frontend/src/App.jsx` 中的 `ModelManager`。
- `frontend/src/codex-workbench.css` 中 `.model-manager-*`、`.modal-backdrop`、`.codex-modal` 相关样式。
- `server.py` 中 `/api/models/*`。
- `db.py` 中 `api_keys` 表和 `save_api_key`、`update_api_key_alias`、`get_all_api_keys`。

## 本轮文档整理记录

本轮参考了 `D:\xjb-test` 的文档组织方式，但没有复制其代码和三层平台架构。Ai Multi Agent 新增了：

- 项目总览。
- 系统架构。
- 模块边界。
- 后续生成规则。
- 前端组件管理。
- 比赛视觉展示。
- 本地 GPU + API 协作策略。
- 参考项目理解总结。

## 后续记录规则

以后每次较大改动后，在本文追加一小节即可，不需要写成长篇日报。每条记录至少包含：

- 改动目标。
- 修改的核心文件。
- 保留或改变了哪些契约。
- 如何验证。
- 哪些后续风险需要注意。
