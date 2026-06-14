# 天韬（SkyT） 本地 GPU 辅助 API 工作流

本文记录 天韬（SkyT） 中本地 GPU 与云端 API 的分工。

## 分工原则

本地 GPU 不替代 API。它负责低成本辅助：

- 初步理解用户需求；
- 压缩历史和上下文；
- 生成初稿或上下文 Markdown；
- 生成辅助文档和历史重要工作记录；
- 为 API 准备更清晰、更短、更有价值的输入。

云端 API 负责：

- 完整工程、多文件项目、架构设计；
- 高质量稳定生成；
- 比赛展示核心代码；
- 复杂重构和严肃审查。

## 当前流程

1. `/api/chat` 接收用户请求。
2. `agent/router.py` 判断任务复杂度。
3. 简单任务进入 `GPU_CHAT_STREAM`，本地 GPU 流式回复。
4. 复杂工程进入 `GPU_ASSIST`，本地 GPU 只生成整理稿。
5. 前端在 GPU 整理稿下根据内容显示操作：
   - 无代码块：`更改需求` / `确认`
   - 有代码块：`保存到本地` / `启用深度思考`
6. API 调用时携带 `context_bundle`，其中包含用户原始需求、本地 GPU 初稿、压缩上下文和来源 run_id。

## 关键文件

- `agent/router.py`：复杂度判断、GPU chat / assist 路由。
- `server.py`：`context_bundle`、`force_api`、`is_escalation` 调度。
- `frontend/src/App.jsx`：GPU 整理稿按钮和上下文回传。

## 维护要求

不要让复杂工程默认只由本地 GPU 独立完成。新增任务类型时，优先判断是否需要 API 参与最终生成。
