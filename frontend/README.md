# Ai Multi Agent 前端

这里是 Ai Multi Agent 的 React + Vite 工作台前端，不再使用默认 Vite 模板说明。

## 启动与构建

```powershell
cd E:\比赛\Ai Multi Agent\frontend
npm install
npm run dev -- --host 127.0.0.1
```

```powershell
npm run build
```

前端默认调用 `http://<当前主机>:8000`，相关常量分布在 `src/App.jsx`、`src/components/ActionDock.jsx`、`src/components/TerminalPanel.jsx` 和各个 `src/views/*.jsx` 文件中。

## 入口文件

- `src/main.jsx`：React 挂载入口。
- `src/App.jsx`：主工作台壳层、左侧栏、聊天区、模型/API Key 弹窗、会话状态和路由。
- `src/codex-workbench.css`：Codex 风格工作台布局和组件视觉。
- `src/App.css`、`src/index.css`：基础样式、主题变量和历史样式。

## 组件文档

前端页面、核心组件、弹窗、模型设置、输入输出和比赛展示相关说明见：

```text
../docs/FRONTEND_COMPONENT_GUIDE.md
```

修改前端功能时优先阅读该文档，避免每次重新扫完整项目。
