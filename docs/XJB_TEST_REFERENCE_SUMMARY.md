# D:\xjb-test 参考项目理解总结

本文件记录对 `D:\xjb-test` 的只读理解。该项目只作为 Ai Multi Agent 文档组织、架构表达和演示说明的参考，不运行、不测试、不修改，也不直接复制代码。

## 核心架构

`D:\xjb-test` 是一个 v2-only 的 AI 多 Agent 平台演示项目，主链路是：

```text
Vue3 + TypeScript
  -> Java Spring Boot Platform API
  -> Python FastAPI Agent Engine
  -> LangGraph / Agents / CodeAgent
  -> MySQL / RunEvent / SSE / Replay
```

它把职责拆得很清楚：Vue 负责页面和可视化，Java 负责平台 API、MySQL、SSE、运行记录和配置管理，Python 负责 Agent Engine、LangGraph、CodeAgent 和报告生成，MySQL 保存任务、事件、模板和报告索引。

## 文档结构特点

最值得借鉴的是文档入口非常明确：

- `README.md` 负责快速启动、技术栈、页面入口和关键文档。
- `docs/DOCUMENT_INDEX.md` 负责把架构、API、运维、UI、Codex 协作、演示、规划拆成导航表。
- `docs/CODEX_PROJECT_CONTEXT.md` 给 AI 协作者提供当前项目定位、稳定契约和修改优先级。
- `docs/MODULE_BOUNDARY.md` 写清 Vue、Java、Python、MySQL、Runner、Docker 的职责边界。
- `docs/SAFE_CHANGE_CHECKLIST.md` 和 `docs/MAINTENANCE_GUIDE.md` 把每次改动后的验证命令和风险项固定下来。
- 演示文档单独存在，例如 `V2_3_MIN_DEMO_SCRIPT.md`、`VIDEO_CODING_GUIDE.md`、`DEFENSE_SCRIPT.md`。

这种组织方式可以让后续 AI 不必每次重新扫完整项目，先读索引、上下文和边界即可开始安全修改。

## 生成逻辑

参考项目的生成逻辑不是单次聊天产物，而是围绕“平台化演示闭环”逐步生成：

1. 先明确 v2-only 主链路，删除或弱化旧入口。
2. 再把 Agent 执行、CodeAgent 文件操作、RunEvent、SSE、Replay、报告和模板统一成可观察流程。
3. 每次新增功能后补文档、补 smoke 测试和演示脚本。
4. 对核心契约设置稳定边界，例如 `run_summary`、`ui_view_model`、`workflow_events`。
5. 把历史文档和当前主文档分开，避免后续维护被旧方案误导。

## 值得 Ai Multi Agent 参考的地方

- 建立 `docs/README.md` 作为文档总入口。
- 保留“项目上下文、系统架构、模块边界、后续生成规则、演示脚本、组件说明”的文档组合。
- 文档中明确哪些文件是核心文件，哪些模块不要现场乱改。
- 比赛展示文档要写演示路径和视觉主次，而不是只列功能。
- 维护文档要写验证命令、风险项和后续 AI 修改顺序。

## 不应该照搬的地方

- 不照搬 Vue + Java + FastAPI + MySQL 的三层平台结构。Ai Multi Agent 当前是 React/Vite + FastAPI + MySQL + Agent 工具层。
- 不照搬 Java Gateway、JPA、Docker Compose 平台层，因为 Ai Multi Agent 没有这条主链路。
- 不照搬 Figma-first 文档口径。Ai Multi Agent 当前重点是 Codex 风格工作台，而不是 Figma 设计同步系统。
- 不照搬受控 CodeAgent 的简化接口定义。Ai Multi Agent 已经有自己的 `agent/tools/fs_tools.py`、终端、工作区绑定和自主模式。
- 不把参考项目的历史文档体系直接堆到 Ai Multi Agent。Ai Multi Agent 只需要围绕后续维护和比赛展示的精简文档组。
