# Ai Multi Agent数据蒸馏机制

本文记录 `db.py::distill_run_data` 与 `agent/distillation_worker.py` 的维护规则。

## 目标

Ai Multi Agent数据蒸馏是一种“以时间换空间”的工程策略：后台牺牲少量处理时间，把长上下文、多 Agent、多步骤任务产生的冗余日志压缩为可回放摘要，换取数据库长期轻量、可维护和可持续运行。

## 保留内容

蒸馏时必须保留：

- 用户需求与运行摘要；
- 最终输出、报告索引和关键产物；
- 失败事件、错误摘要和安全阻断；
- 重要工具调用、代码生成摘要；
- `token_usage`、`model_info`；
- `input_payload` / `output_payload` 的核心摘要；
- `execution_step` 的主线信息。

## 压缩内容

优先压缩：

- 重复的成功状态流转；
- 大段临时 JSON；
- 超长中间 payload；
- 不影响复盘的临时模型输出；
- 已经可以被摘要表达的工具结果。

压缩后的 `detail_json` 不会被清空，而是写回：

```json
{
  "distillation": {
    "distilled": true,
    "strategy": "time_for_space",
    "summary": "...",
    "original_bytes": 12345,
    "preserved_fields": []
  }
}
```

## 核心文件

- `db.py`：`distill_run_data`，事件分级和压缩写回。
- `agent/distillation_worker.py`：空闲时扫描大体积运行记录并触发蒸馏。
- `frontend/src/views/WorkflowReplay.jsx`：深度回放读取压缩后的摘要。

## 后续维护

新增事件类型时，先判断它是“必须完整保留”“可摘要压缩”还是“冗余状态”。不要再使用 `detail_json = NULL` 作为默认清理策略。
