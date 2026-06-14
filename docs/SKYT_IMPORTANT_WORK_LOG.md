# 天韬（SkyT） 历史重要工作记录

本文记录本地 GPU 生成辅助 Markdown 和历史工作记录的机制。

## 目标

本地 GPU 用低成本方式把运行历史、深度回放、Token 消耗、关键错误和最终产物整理成 Markdown。后续 API 调用可以读取这些摘要，减少重复携带完整历史和大段 JSON。

## 支持类型

`POST /api/runs/{run_id}/generate-markdown` 支持：

- `task_summary`：本次任务总结；
- `replay_summary`：深度回放摘要；
- `important_work_log`：历史重要工作记录；
- `api_context`：API 前置上下文压缩。

默认保存到 `reports` 表。传入 workspace 时，可额外写入：

```text
<workspace>/.skyt/important_work_logs/<run_id>_<kind>.md
```

## 核心文件

- `agent/markdown_archivist.py`：读取 run 结构，调用本地 GPU 生成 Markdown。
- `server.py`：`/api/runs/{run_id}/generate-markdown` 接口。
- `frontend/src/views/RunHistory.jsx`：运行历史中触发生成工作记录。

## 失败策略

GPU 生成失败时，不影响主任务。系统会生成 fallback Markdown，并在 run_events 中写入归档事件。

## 后续维护

Markdown 不要保存原始流水账，应保留任务目标、关键步骤、关键文件、错误修复、Token 消耗和后续建议。
