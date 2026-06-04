export const zh = {
  welcome: '欢迎使用 Ai Multi Agent 工作台。你可以直接描述任务，我会主动阅读项目、修改代码并运行验证；遇到删除、覆盖关键文件、工作区外写入等高风险动作时会先请求确认。',
  nav: {
    chat: '智能对话',
    dashboard: '数据看板',
    history: '运行历史',
    workflows: '工作流',
    reports: '报告中心',
    skills: '技能大厅',
    replay: '运行回放'
  },
  sidebar: {
    modelSettings: '模型设置',
    newChat: '新建对话',
    workspace: '工作区',
    workspaceEmpty: '未绑定工作区',
    sessions: '会话历史',
    clearCurrent: '清空当前',
    collapse: '折叠侧边栏',
    expand: '展开侧边栏',
    deleteSession: '删除会话',
    emptySession: '新对话',
    smartRoute: '智能路由',
    noModel: '未配置模型'
  },
  composer: {
    placeholder: '@agent 或直接描述你要改的功能。Shift+Enter 换行。',
    model: '模型',
    workflow: '工作流',
    autonomy: '自主模式',
    workspace: '工作区',
    bindWorkspace: '绑定工作区',
    workspaceBound: '工作区已绑定',
    send: '发送',
    stop: '停止',
    autoRoute: '智能路由',
    settings: '设置',
    help: '帮助'
  },
  workflowMode: {
    standard: '标准执行',
    deep_thought: '深度思考',
    expert_review: '专家复核',
    creative_brainstorm: '创意发散'
  },
  autonomyMode: {
    supervised_auto: '强自主可确认',
    ask_each_step: '逐步询问',
    full_auto: '完全自动'
  },
  status: {
    backendDisconnected: '后端未连接',
    working: '正在处理',
    executionTrace: '执行步骤',
    routeBy: '路由',
    user: '你'
  },
  confirm: {
    clearTitle: '清空当前对话？',
    clearDescription: '这会删除当前会话记录，并开启一个新对话。',
    deleteTitle: '删除这个会话？',
    deleteDescription: '会话消息和历史入口会被移除；如果它正被打开，Ai Multi Agent 会自动切换到新对话。',
    cancel: '取消',
    clear: '清空',
    delete: '删除'
  },
  modelManager: {
    title: '模型与 API Key',
    empty: '暂无模型配置。',
    remove: '移除',
    apiKeyPlaceholder: '粘贴 API Key...',
    add: '添加'
  }
};
