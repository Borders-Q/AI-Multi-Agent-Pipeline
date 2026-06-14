# 天韬（SkyT） 项目入口

天韬（SkyT） 是一个面向比赛展示和本地开发协作的 AI 工作台。当前主线不是重新做一个通用聊天网页，而是把“对话、工作区、执行日志、浏览器、PowerShell、工作流、报告和模型配置”组织成一个接近 Codex 使用体验的本地系统。

## 快速启动

后端默认运行在 `http://127.0.0.1:8000`，前端默认运行在 `http://127.0.0.1:5173`。

```powershell
.\一键启动.bat
```

也可以分开启动：

```powershell
cd E:\比赛\AI Mu
python server.py
```

```powershell
cd E:\比赛\AI Mu\frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 当前主链路

```text
React + Vite 工作台
  -> FastAPI server.py
  -> db.py / MySQL
  -> agent/router.py / agent/workflow.py
  -> 本地 Ollama/GPU、NPU 快速分类、云端 API
  -> 工具层、运行记录、报告、技能市场和工作流
```

## 核心文档

从 `docs/README.md` 进入完整文档。最常用的阅读顺序：

1. `docs/PROJECT_OVERVIEW.md`
2. `docs/SYSTEM_ARCHITECTURE.md`
3. `docs/MODULE_BOUNDARY.md`
4. `docs/FUTURE_GENERATION_GUIDE.md`
5. `docs/FRONTEND_COMPONENT_GUIDE.md`
6. `docs/COMPETITION_VISUAL_GUIDE.md`
7. `docs/GPU_API_COLLABORATION.md`

`docs/XJB_TEST_REFERENCE_SUMMARY.md` 记录了对 `D:\xjb-test` 的只读参考总结。该项目只作为文档组织和架构表达方式参考，不作为 天韬（SkyT） 的代码来源。

## 维护原则

- 不要把 天韬（SkyT） 改造成 `D:\xjb-test` 的 Vue + Java + FastAPI 三层平台。
- 前端 UI 修改优先保持 Codex 风格工作台，不做营销落地页。
- 后端接口改动前先看 `server.py`、`db.py`、`agent/workflow.py` 和 `agent/tools/fs_tools.py`。
- 模型与 API Key 相关逻辑集中看 `frontend/src/App.jsx` 中的 `ModelManager` 和 `server.py` 中的 `/api/models/*`。
- 比赛展示优先讲清核心闭环，不堆无关功能。
