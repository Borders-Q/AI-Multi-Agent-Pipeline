# 天韬（SkyT） 文档索引

本文是 `docs/` 的总入口。天韬（SkyT） 当前定位为比赛展示型 AI 工作台，核心是把对话、工作区、模型路由、执行日志、浏览器、PowerShell、工作流、运行记录和报告组织为一个可维护的本地系统。

## 推荐阅读顺序

| 顺序 | 文档 | 用途 |
| --- | --- | --- |
| 1 | `PROJECT_OVERVIEW.md` | 快速理解项目目标、已完成能力和核心文件 |
| 2 | `SYSTEM_ARCHITECTURE.md` | 理解前端、后端、数据库、Agent、GPU/API 的数据流 |
| 3 | `MODULE_BOUNDARY.md` | 判断修改应该落在哪个模块，哪些位置不要乱动 |
| 4 | `FUTURE_GENERATION_GUIDE.md` | 给后续 AI 或开发者的生成、维护、验证规则 |
| 5 | `FRONTEND_COMPONENT_GUIDE.md` | 前端页面、组件、弹窗、模型设置和状态关系 |
| 6 | `COMPETITION_VISUAL_GUIDE.md` | 比赛展示视觉重点、演示路径和弱化项 |
| 7 | `GPU_API_COLLABORATION.md` | 本地 GPU 辅助云 API 的策略和边界 |
| 8 | `GENERATION_HISTORY.md` | 已有生成过程和本次整理记录 |
| 9 | `PROJECT_OPTIMIZATION_GUIDE.md` | 后续持续优化、UI 调整和 vibe coding 记录 |
| 10 | `SKYT_FUTURE_OPTIMIZATION_ROADMAP.md` | Token 统计、执行过程可视化、本地 GPU + API 协作后续路线图 |
| 11 | `SKYT_DATA_DISTILLATION.md` | 天韬（SkyT）数据蒸馏、事件保留和压缩规则 |
| 12 | `SKYT_GPU_API_WORKFLOW.md` | 本地 GPU 辅助 API 的分工和按钮流程 |
| 13 | `SKYT_STREAMING_OUTPUT.md` | GPU/API/执行步骤流式输出链路 |
| 14 | `SKYT_UI_OUTPUT_STRUCTURE.md` | 输入框、执行步骤、最终回答和 Token 的 UI 分层 |
| 15 | `SKYT_IMPORTANT_WORK_LOG.md` | GPU 生成辅助 Markdown 和历史重要工作记录 |
| 16 | `SKYT_WORKFLOW_TEMPLATES_DEMO.md` | Workflow Templates 比赛演示模板、节点结构和闭环路径 |
| 17 | `SKYT_TRAE_SKILL_EXPORT.md` | 工作流模板与编辑器工作流导出 Trec/SOLO Skill 的接口、结构和演示路径 |
| 18 | `SKYT_SKILL_WORKFLOW_ROUNDTRIP.md` | Trec/SOLO Skill 导入为模板、系统技能转模板和双向转换闭环 |
| 19 | `SKYT_BRANCH_WORKFLOW_RUNTIME.md` | 条件分支、else、loop、AND/OR 汇合的轻量运行机制 |
| 20 | `XJB_TEST_REFERENCE_SUMMARY.md` | 参考项目 `D:\xjb-test` 的只读理解总结 |

## 当前主文档

- `PROJECT_OVERVIEW.md`：项目总览和核心目标。
- `SYSTEM_ARCHITECTURE.md`：系统结构、请求链路和稳定契约。
- `MODULE_BOUNDARY.md`：模块职责和改动边界。
- `GENERATION_HISTORY.md`：生成过程记录。
- `FUTURE_GENERATION_GUIDE.md`：后续生成逻辑说明。
- `FRONTEND_COMPONENT_GUIDE.md`：前端功能与组件管理。
- `COMPETITION_VISUAL_GUIDE.md`：比赛演示视觉效果。
- `GPU_API_COLLABORATION.md`：本地 GPU + API 协作策略。
- `PROJECT_OPTIMIZATION_GUIDE.md`：持续优化记录和后续维护建议。
- `SKYT_FUTURE_OPTIMIZATION_ROADMAP.md`：Token、执行回放和 GPU/API 协作的后续优化路线。
- `SKYT_DATA_DISTILLATION.md`：天韬（SkyT）数据蒸馏机制。
- `SKYT_GPU_API_WORKFLOW.md`：GPU 辅助 API 工作流。
- `SKYT_STREAMING_OUTPUT.md`：流式输出链路。
- `SKYT_UI_OUTPUT_STRUCTURE.md`：对话输出 UI 分层。
- `SKYT_IMPORTANT_WORK_LOG.md`：GPU 归档 Markdown 和重要工作记录。
- `SKYT_WORKFLOW_TEMPLATES_DEMO.md`：Workflow Templates 比赛演示模板。
- `SKYT_TRAE_SKILL_EXPORT.md`：Workflow Template / Workflow Editor 导出 Trec/SOLO Skill。
- `SKYT_SKILL_WORKFLOW_ROUNDTRIP.md`：Skill 导出、导入、系统技能转模板闭环。
- `SKYT_BRANCH_WORKFLOW_RUNTIME.md`：多分支、循环与汇合工作流运行规则。
- `XJB_TEST_REFERENCE_SUMMARY.md`：参考项目总结。

## 维护口径

- README 负责快速入口，详细规则放在 `docs/`。
- 前端组件变更同步检查 `FRONTEND_COMPONENT_GUIDE.md`。
- 运行历史、深度回放、I/O Payload、导航和布局优化同步检查 `PROJECT_OPTIMIZATION_GUIDE.md`。
- Agent、模型路由、工具调用或安全规则变更同步检查 `SYSTEM_ARCHITECTURE.md`、`MODULE_BOUNDARY.md` 和 `GPU_API_COLLABORATION.md`。
- 比赛展示相关 UI 改动同步检查 `COMPETITION_VISUAL_GUIDE.md`。
- Workflow Templates 或工作流演示改动同步检查 `SKYT_WORKFLOW_TEMPLATES_DEMO.md`。
- Skill 导入导出、系统技能转模板改动同步检查 `SKYT_TRAE_SKILL_EXPORT.md` 和 `SKYT_SKILL_WORKFLOW_ROUNDTRIP.md`。
- 条件分支、循环、汇合、连线属性或动态调度改动同步检查 `SKYT_BRANCH_WORKFLOW_RUNTIME.md`。
- 不把运行产物、日志、缓存、`node_modules` 或 `__pycache__` 当作核心文档来源。

## Trec/SOLO Skill 导出

- `SKYT_TRAE_SKILL_EXPORT.md`：说明 Workflow Template / Workflow Editor 如何一键导出为 Trec/SOLO 项目级 Skill，包含生成目录、接口、比赛演示路径和维护边界。
- `SKYT_SKILL_WORKFLOW_ROUNDTRIP.md`：说明 Trec/SOLO Skill 如何导入回 Workflow Template，以及 Skills Store 中的系统技能如何转为工作流模板。
