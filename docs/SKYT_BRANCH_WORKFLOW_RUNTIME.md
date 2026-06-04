# 多分支工作流运行机制说明

本文档说明 Ai Multi Agent 工作流第一版轻量动态调度能力：条件分支、else/default、loop/maxIterations 循环重试、AND/OR 汇合，以及这些动作如何进入运行历史和深度回放。

## 设计目标

多分支能力用于比赛演示和后续扩展，重点是“可看懂、可回放、可控”，不是引入复杂工作流引擎。

目标：

- 旧模板继续按顺序运行；
- 新模板可以通过连线属性表达分支、循环、数据映射和汇合；
- 条件表达式只支持白名单简单比较，禁止执行任意 Python/JS；
- 每一次分支选择、跳过、循环、汇合等待都写入运行事件；
- 出现死循环风险时由最大步数和 `maxIterations` 保护。

## 核心文件

- `agent/workflow.py`：工作流动态调度、条件判断、loop、join、运行事件记录。
- `frontend/src/store/workflowStore.js`：边属性默认值、边属性保存、条件表达式校验。
- `frontend/src/components/WorkflowEditor/NodePropertiesPanel.jsx`：选中连线后展示“连线属性”面板。
- `frontend/src/views/WorkflowEditorPage.jsx`：节点库中的分支、汇合、循环节点分类展示。
- `frontend/src/components/WorkflowEditor/CustomAgentNode.jsx`：新增节点类型标签与图标。
- `db.py`：扩展演示 Agent 节点元数据。

## 连线属性

`workflow_json.edges[*].data` 支持：

```json
{
  "edgeType": "control",
  "condition": "",
  "label": "",
  "fromOutputField": "",
  "toInputField": "",
  "loopPolicy": {
    "maxIterations": 3
  }
}
```

`edgeType` 可选：

- `control`：普通顺序连线，旧模板默认值。
- `branch`：条件分支，按 `condition` 选择命中的下游。
- `loop`：循环重试边，必须配置 `loopPolicy.maxIterations`。
- `data`：字段映射边，第一版运行上按顺序边处理，保留映射信息给后续增强。

## 条件表达式

支持格式：

```text
success == true
status == "failed"
retry_count < 3
has_code_blocks == true
quality_score >= 80
```

允许字段：

- `success`
- `test_success`
- `approved`
- `retry_count`
- `max_retry_count`
- `quality_score`
- `coverage_percent`
- `error_log`
- `status`
- `has_code_blocks`

允许操作符：

- `==`
- `!=`
- `>`
- `>=`
- `<`
- `<=`

特殊条件：

- `else`
- `default`
- 空条件

其中 `else/default` 用于兜底分支。不要写函数调用、脚本、正则或复杂表达式。

## 运行调度规则

### 入口节点

执行从没有上游边的节点开始。如果没有明确入口，则退回到拓扑排序的第一个节点。

### 普通边

`control` 和 `data` 边会把目标节点加入执行队列。

### 分支边

同一个节点的多条 `branch` 边按顺序判断：

1. 条件命中第一条边后，只执行该分支；
2. 条件未命中的边写入 `WORKFLOW_BRANCH_SKIPPED`；
3. 如果没有条件命中，使用 `else/default` 兜底边；
4. 命中边写入 `WORKFLOW_BRANCH_SELECTED`。

### 循环边

`loop` 边只有在条件命中且未超过 `maxIterations` 时才会回到目标节点。

事件：

- 命中循环：`WORKFLOW_LOOP_ITERATION`
- 达到上限：`WORKFLOW_LOOP_LIMIT_REACHED`

每个 loop 边必须有 `maxIterations > 0`，前端校验会提示缺失配置。

### AND 汇合

`join_and` 节点等待所有上游节点完成后才继续。

未满足时写入：

- `WORKFLOW_JOIN_WAITING`

满足后写入：

- `WORKFLOW_JOIN_READY`

### OR 汇合

`join_or` 节点只要任一上游完成即可继续。已经执行过的 OR 汇合不会被重复触发，避免多分支重复进入下游。

## 运行事件

新增事件类型：

- `WORKFLOW_BRANCH_SELECTED`
- `WORKFLOW_BRANCH_SKIPPED`
- `WORKFLOW_LOOP_ITERATION`
- `WORKFLOW_LOOP_LIMIT_REACHED`
- `WORKFLOW_JOIN_READY`
- `WORKFLOW_JOIN_WAITING`

这些事件会进入：

- 运行历史；
- 深度回放；
- 报告中心；
- I/O Payload 和 detail JSON。

## 演示 Agent 节点库

新增演示节点包括：

- 需求理解
- 架构规划
- 上下文压缩
- 本地 GPU 草稿
- API 深度生成
- 代码生成
- 文件落盘
- 依赖安装
- 测试验证
- 本地预览部署
- Replay 记录
- Report 总结
- 安全风险检查
- 人工确认
- 条件分支
- 循环重试
- AND 汇合
- OR 汇合

这些节点来自后端 `/api/agents` 和前端内置特殊节点，不新增数据库字段。

## 参考 `D:\xjb-test` 的部分

只借鉴以下思路：

- 分支条件应是结构化元数据，不写死在 UI；
- 运行事件应记录“选中、跳过、等待、循环次数”；
- 深度回放里要能看懂为什么走了某条路径；
- 多分支第一版要有保护上限。

不照搬：

- Vue / Java Gateway 架构；
- 它的完整动态流程引擎；
- 与 Ai Multi Agent 当前比赛展示无关的业务模块。

## 后续可扩展点

- 把 `fromOutputField` / `toInputField` 做成真正的节点输入映射。
- 支持更丰富但仍安全的表达式组合，例如 `success == true && quality_score >= 80`。
- 在 Workflow Editor 中给分支边加不同颜色。
- 在深度回放中把分支路径高亮成一条可视化轨迹。
