# 天韬（SkyT） 后续优化路线图

本文面向后续维护、继续生成代码和 vibe coding，不是宣传文案。重点记录 天韬（SkyT） 继续演进时应遵守的数据结构、Token 统计、执行过程可视化和本地 GPU + API 协作边界。

## 1. 当前定位

天韬（SkyT） 是比赛展示型 AI 工作台，核心价值不是堆功能数量，而是让评委和用户看到一个能对话、能绑定工作区、能执行任务、能记录运行过程、能回放 I/O Payload 的本地 AI Agent 系统。

后续优化要优先服务三个目标：

- 对话与执行过程可信：用户知道 天韬（SkyT） 现在在做什么。
- 运行历史可复盘：每次任务的输入、输出、工具调用、模型调用和 Token 消耗可追踪。
- 本地 GPU 辅助 API：本地模型负责预处理、压缩和轻量生成，API 负责关键高质量生成。

## 2. 本轮新增稳定契约

后端新增 Token 统计结构，推荐所有模型调用都写入：

```json
{
  "api_tokens": 0,
  "local_tokens": 0,
  "total_tokens": 0,
  "real_tokens": 0,
  "estimated_tokens": 0,
  "source": "real | estimated | mixed | none",
  "calls": []
}
```

`run_events.detail_json` 推荐保持以下结构：

```json
{
  "input_payload": {},
  "output_payload": {},
  "token_usage": {},
  "model_info": {},
  "execution_step": {}
}
```

不要让前端直接依赖模型原始返回结构。前端应优先消费 `token_usage`、`input_payload`、`output_payload` 和 `execution_step`。

## 3. Token 统计规则

API Token 必须优先读取 provider 返回的真实 `usage`：

- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `prompt_tokens_details.cached_tokens`
- `completion_tokens_details.reasoning_tokens`

只有缺失 `usage` 时才允许估算。估算值必须标记为 `source: "estimated"`，不能冒充真实消耗。

本地 GPU/Ollama 优先读取：

- `prompt_eval_count`
- `eval_count`

如果本地模型不返回这些字段，才使用估算。NPU 静态规则命中、硬编码安全回复、普通系统动作不应伪造 Token。

## 4. 执行过程展示规则

对话窗口展示的是用户可理解的真实过程，例如：

- 接收需求并进行意图路由。
- 本地 GPU 进行快速响应或上下文整理。
- API 生成计划或执行关键任务。
- 工具执行、文件写入、命令运行。
- Token 汇总写入运行历史。

不要展示模型隐藏推理链，不要把 provider 的原始 `reasoning_content` 当成“深思过程”输出。需要表达复杂思考时，用高层状态描述即可。

## 5. 运行历史与深度回放

`run_records` 是任务摘要表，适合显示列表、状态、质量分、Token 汇总。

`run_events` 是细粒度回放表，适合记录：

- 每次模型调用的输入摘要和输出预览。
- 工具调用参数和结果。
- Token usage。
- 执行步骤状态。
- 错误和安全阻断。

后续如果继续扩展回放，不要把所有展示逻辑塞进 `message` 字段，应优先扩展 `detail_json` 的结构化字段。

## 6. 本地 GPU + API 协作方向

适合本地 GPU 处理：

- 用户输入整理。
- 上下文筛选。
- 长历史压缩。
- 简单问答、格式润色、初稿生成。
- API 调用前的关键信息提取。
- API 返回后的摘要和展示整理。

必须优先交给 API 的任务：

- 高风险代码修改计划。
- 长链路工程实现。
- 需要稳定性和准确性的关键生成。
- 多文件复杂重构。
- 需要严格推理、审查或比赛演示主流程的输出。

目标是减少无效上下文进入 API，而不是让本地 GPU 盲目承担超出能力范围的任务。

## 7. 与 D:\xjb-test 的参考关系

`D:\xjb-test` 值得参考的不是具体代码，而是结构思想：

- 稳定的 `run_summary / ui_view_model / workflow_events` 数据契约。
- 前端优先消费稳定视图模型，不直接解析后端内部状态。
- 运行历史、事件时间线、深度回放、detail JSON 折叠展示分层清晰。
- 文档中明确哪些结构不能随意破坏。

天韬（SkyT） 不应照搬它的 Vue/Java Gateway 架构，也不应把比赛工作台改造成另一个项目形态。

## 8. 后续优先优化清单

1. 为 Token 统计辅助模块补充单元测试样例。
2. 将更多工具调用结果统一写成 `input_payload/output_payload`。
3. 为 Dashboard 增加 API Token、本地 Token、估算比例趋势图。
4. 将本地 GPU 的上下文压缩结果单独存入可回放事件。
5. 为执行步骤增加失败原因和恢复建议。
6. 为比赛演示准备一条固定可复现的“需求输入 -> 执行 -> 历史 -> 回放”路径。

## 9. 不建议随意改动的区域

- `db.py` 中已有表结构和增量迁移逻辑。
- `/api/chat` 的 SSE 事件兼容字段。
- `run_records.total_tokens` 旧字段。
- `WorkflowReplay.jsx` 的 Payload Viewer 分区逻辑。
- 模型/API Key 管理弹窗与模型保存逻辑。

如需重构这些区域，先补兼容层，再替换调用方。

## 10. 人工待确认

- 不同云 API provider 对流式 usage 的支持程度不同，后续需要用实际 Key 验证。
- Ollama 不同模型和版本返回的 token 字段可能不同，后续可增加更多兼容字段。
- 当前 Token 估算使用轻量字符规则，后续如引入 tokenizer，应继续保持“估算必须标记”的原则。
