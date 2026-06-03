import React, { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  Blocks,
  Bot,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  GitBranch,
  History,
  HelpCircle,
  Menu,
  Plus,
  Send,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Square,
  User,
  X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MermaidChart from './components/MermaidChart';
import ActionDock from './components/ActionDock';
import SessionItem from './components/SessionItem';
import AppTooltip from './components/ui/AppTooltip';
import BaseIconButton from './components/ui/BaseIconButton';
import BasePopover from './components/ui/BasePopover';
import ConfirmDialog from './components/ui/ConfirmDialog';
import SidebarToggle from './components/ui/SidebarToggle';
import Dashboard from './views/Dashboard';
import Reports from './views/Reports';
import RunHistory from './views/RunHistory';
import SkillsStore from './views/SkillsStore';
import WorkflowEditorPage from './views/WorkflowEditorPage';
import WorkflowReplay from './views/WorkflowReplay';
import Workflows from './views/Workflows';
import { zh } from './i18n/zh';
import './index.css';
import './codex-workbench.css';

const API_BASE = `http://${window.location.hostname}:8000`;
const WELCOME_MESSAGE = zh.welcome;
const LOCAL_URL_PATTERN = /https?:\/\/(?:localhost|127(?:\.\d{1,3}){3}|\[::1\])(?::\d+)?(?:\/[^\s`"')<>\]]*)?/i;

const extractFirstLocalUrl = (text = '') => {
  const match = String(text || '').match(LOCAL_URL_PATTERN);
  return match ? match[0].replace(/[.,;，。；]+$/, '') : '';
};

const formatRoutedByLabel = (routedBy) => {
  if (routedBy === 'Cloud API') return 'API';
  return routedBy || '';
};

const workflowNeedsWorkspace = (summary = {}, text = '') => {
  if (!summary) return false;
  if (summary.requires_workspace) return true;
  const policy = summary.artifact_policy || {};
  if (!policy.requires_workspace_when_code) return false;
  return /写|生成|开发|系统|项目|代码|flask|fastapi|django|html|css|js|ts|typescript|python|sqlite|vue|react/i.test(text || '');
};

function parseJsonField(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function normalizeHistoryMessage(message) {
  const metadata = parseJsonField(message.metadata_json);
  return {
    ...message,
    metadata,
    token_usage: metadata?.token_usage || message.token_usage,
    actions: metadata?.actions || message.actions,
    context_bundle: metadata?.context_bundle || message.context_bundle,
    run_id: metadata?.run_id || message.run_id,
  };
}

function normalizeTokenUsage(value) {
  const usage = value?.token_usage || value;
  const realTokens = Number(usage?.real_tokens || 0);
  const estimatedTokens = Number(usage?.estimated_tokens || 0);
  const totalTokens = Number(usage?.total_tokens || 0);
  let source = usage?.source || 'none';
  if ((!source || source === 'none') && totalTokens > 0) {
    source = estimatedTokens > 0 ? 'estimated' : realTokens > 0 ? 'real' : 'estimated';
  }
  return {
    api_tokens: Number(usage?.api_tokens || 0),
    local_tokens: Number(usage?.local_tokens || 0),
    total_tokens: totalTokens,
    estimated_tokens: estimatedTokens,
    real_tokens: realTokens,
    source,
  };
}

function TokenUsageBadge({ usage }) {
  const data = normalizeTokenUsage(usage);
  if (!data.total_tokens) return null;
  const sourceLabel = data.source === 'estimated' ? '估算' : data.source === 'mixed' ? '真实+估算' : data.source === 'real' ? '真实' : '未标明';
  return (
    <div className="token-usage-badge" title={`API ${data.api_tokens} / 本地 ${data.local_tokens} / 总计 ${data.total_tokens}`}>
      <Activity size={13} />
      <span>API {data.api_tokens}</span>
      <span>本地 {data.local_tokens}</span>
      <strong>{data.total_tokens} tokens</strong>
      <em>{sourceLabel}</em>
    </div>
  );
}

function getMainNavItems(iconSize = 18) {
  return [
    { to: '/', label: zh.nav.chat, icon: <Bot size={iconSize} /> },
    { to: '/dashboard', label: zh.nav.dashboard, icon: <Activity size={iconSize} /> },
    { to: '/history', label: zh.nav.history, icon: <History size={iconSize} /> },
    { to: '/workflows', label: zh.nav.workflows, icon: <Blocks size={iconSize} /> },
    { to: '/reports', label: zh.nav.reports, icon: <FileText size={iconSize} /> },
    { to: '/skills', label: zh.nav.skills, icon: <Sparkles size={iconSize} /> },
  ];
}

function ErrorBoundaryFallback({ children }) {
  try {
    return children;
  } catch (error) {
    console.error(error);
    return <span className="inline-error">渲染失败：{error.message}</span>;
  }
}

function OptionPopover({ id, label, value, options, openPanel, setOpenPanel, onChange, icon }) {
  const current = options.find((option) => option.value === value) || options[0];
  const open = openPanel === id;

  return (
    <BasePopover
      open={open}
      onOpenChange={(nextOpen) => setOpenPanel(nextOpen ? id : null)}
      align="start"
      trigger={({ toggle }) => (
        <button className={`composer-chip ${open ? 'active' : ''}`} type="button" onClick={toggle}>
          {icon}
          <span>{label}</span>
          <strong>{current?.label}</strong>
          <ChevronDown size={14} />
        </button>
      )}
    >
      <div className="popover-title">{label}</div>
      <div className="popover-options">
        {options.map((option) => (
          <button
            type="button"
            key={option.value}
            className={option.value === value ? 'selected' : ''}
            onClick={() => {
              onChange(option.value);
              setOpenPanel(null);
            }}
          >
            <span>
              <strong>{option.label}</strong>
              {option.description && <em>{option.description}</em>}
            </span>
            {option.value === value && <Check size={15} />}
          </button>
        ))}
      </div>
    </BasePopover>
  );
}

function isStepRunning(step) {
  const state = String(step?.state || '').toLowerCase();
  return state && !['done', 'completed', 'success', 'failed', 'error'].includes(state);
}

function ExecutionSteps({ workflow = [], logs = [] }) {
  const hasRunningStep = workflow.some(isStepRunning);
  const [manualExpanded, setManualExpanded] = useState(null);
  const expanded = manualExpanded || hasRunningStep;

  if (!workflow.length && !logs.length) return null;
  return (
    <div className={`execution-card ${expanded ? 'expanded' : 'collapsed'}`}>
      <button className="execution-card-title" type="button" onClick={() => setManualExpanded(!expanded)} aria-expanded={expanded}>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Activity size={14} />
        <span>{zh.status.executionTrace}</span>
        <em>{hasRunningStep ? '执行中' : `${workflow.length || logs.length} 项记录`}</em>
      </button>
      {expanded && (
        <div className="execution-card-body">
          {workflow.map((step, index) => (
            <div key={`${step.node}-${index}`} className={`execution-step ${step.state || 'running'}`}>
              <span className="execution-index">{index + 1}</span>
              <span className="execution-step-main">
                <strong>{step.node}</strong>
                {step.description && step.description !== step.node && <small>{step.description}</small>}
              </span>
              {step.token_usage?.total_tokens ? <TokenUsageBadge usage={step.token_usage} /> : null}
              <em>{step.state || 'running'}</em>
            </div>
          ))}
          {logs.slice(-6).map((log, index) => (
            <pre key={`${log}-${index}`}>{log}</pre>
          ))}
        </div>
      )}
    </div>
  );
}

function ApprovalCard({ content }) {
  return (
    <div className="approval-card">
      <strong>需要确认</strong>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      <p>为避免误删、误覆盖或执行危险命令，Ai Multi Agent 已经在自动动作前停下。</p>
    </div>
  );
}

function hasMarkdownCodeBlock(content = '') {
  return /```[\w-]*\s*[\r\n][\s\S]*?```/.test(content || '');
}

function resolveGpuAssistActions(msg) {
  const actions = msg.actions || [];
  const actionKeys = new Set(actions.map((action) => action.key));
  const hasCode = Boolean(msg.context_bundle?.has_code_blocks) || hasMarkdownCodeBlock(msg.content);
  const isGpuDraft = msg.type === 'gpu_draft' || msg.routed_by === 'GPU Assist';

  if (actionKeys.has('save_code_local') || actionKeys.has('deep_think_api')) {
    return [
      { key: 'save_code_local', label: '保存到本地' },
      { key: 'deep_think_api', label: '启用深度思考' },
    ];
  }
  if (isGpuDraft && hasCode) {
    return [
      { key: 'save_code_local', label: '保存到本地' },
      { key: 'deep_think_api', label: '启用深度思考' },
    ];
  }
  if (actions.length) return actions;
  if (isGpuDraft && msg.context_bundle) {
    return [
      { key: 'edit_requirement', label: '更改需求' },
      { key: 'confirm_api', label: '确认' },
    ];
  }
  return [];
}

function GPUAssistActions({ actions = [], onEditRequirement, onConfirmApi, onSaveCodeLocal, onDeepThinkApi }) {
  const actionKeys = new Set(actions.map((action) => action.key));
  const canSaveCode = actionKeys.has('save_code_local');
  const canDeepThink = actionKeys.has('deep_think_api');
  const canConfirm = actionKeys.has('confirm_api') || actionKeys.has('deep_think') || actionKeys.has('direct_api');
  const canEdit = actionKeys.has('edit_requirement') || canConfirm;
  if (!canEdit && !canConfirm && !canSaveCode && !canDeepThink) return null;
  return (
    <div className="gpu-assist-actions">
      {canSaveCode && (
        <button className="codex-button primary" type="button" onClick={onSaveCodeLocal}>
          <Folder size={15} />
          保存到本地
        </button>
      )}
      {canDeepThink && (
        <button className="codex-button subtle" type="button" onClick={onDeepThinkApi}>
          <Sparkles size={15} />
          启用深度思考
        </button>
      )}
      {canEdit && (
        <button className="codex-button subtle" type="button" onClick={onEditRequirement}>
          <SlidersHorizontal size={15} />
          更改需求
        </button>
      )}
      {canConfirm && (
        <button className="codex-button primary" type="button" onClick={onConfirmApi}>
          <Check size={15} />
          确认
        </button>
      )}
    </div>
  );
}

function Sidebar({
  isOpen,
  setIsOpen,
  sessions,
  sessionId,
  activeProvider,
  workspacePath,
  onNewChat,
  onSelectSession,
  onClear,
  onOpenModelManager,
  onDeleteSession,
}) {
  const navItems = getMainNavItems(18);

  return (
    <aside className={`codex-sidebar ${isOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div className="brand-copy">
            <strong>Ai Multi Agent</strong>
            <span>{activeProvider === 'auto' ? zh.sidebar.smartRoute : activeProvider || zh.sidebar.noModel}</span>
          </div>
        <BaseIconButton label={zh.sidebar.modelSettings} tooltip={zh.sidebar.modelSettings} onClick={onOpenModelManager}>
          <Settings size={17} />
        </BaseIconButton>
      </div>

      <button className="new-chat-button" onClick={onNewChat} aria-label={zh.sidebar.newChat}>
        <Plus size={17} />
        <span>{zh.sidebar.newChat}</span>
      </button>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <AppTooltip key={item.to} label={item.label} side="right" disabled={isOpen}>
            <NavLink to={item.to} end={item.to === '/'} className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} aria-label={item.label}>
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          </AppTooltip>
        ))}
      </nav>

      <AppTooltip label={workspacePath || zh.sidebar.workspaceEmpty} side="right" disabled={isOpen}>
        <div className="workspace-chip">
        <Folder size={16} />
          <span>{workspacePath ? workspacePath : zh.sidebar.workspaceEmpty}</span>
        </div>
      </AppTooltip>

      <section className="session-list" aria-hidden={!isOpen}>
          <div className="section-label">
            <span>{zh.sidebar.sessions}</span>
            <button type="button" onClick={onClear}>{zh.sidebar.clearCurrent}</button>
          </div>
          <div className="session-scroll">
            {sessions.map((session) => (
              <SessionItem
                key={session.session_id}
                session={session}
                active={session.session_id === sessionId}
                onSelect={() => onSelectSession(session.session_id)}
                onDelete={() => onDeleteSession(session)}
              />
            ))}
          </div>
      </section>

      <SidebarToggle open={isOpen} onToggle={() => setIsOpen(!isOpen)} />
    </aside>
  );
}

function ModelManager({ open, onClose, models, newApiKey, setNewApiKey, onAddKey, onRemoveKey, onUpdateAlias }) {
  const [editingProvider, setEditingProvider] = useState(null);
  const [editingAlias, setEditingAlias] = useState('');

  if (!open) return null;

  const startEdit = (model) => {
    setEditingProvider(model.provider);
    setEditingAlias(model.alias || '');
  };

  const saveAlias = async (provider) => {
    await onUpdateAlias(provider, editingAlias.trim());
    setEditingProvider(null);
    setEditingAlias('');
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="codex-modal model-manager-modal" onClick={(event) => event.stopPropagation()}>
        <BaseIconButton className="model-manager-close" label="关闭" tooltip="关闭" onClick={onClose}><X size={18} /></BaseIconButton>
        <div className="model-manager-header">
          <div className="model-manager-icon"><Settings size={22} /></div>
          <div>
            <strong>{zh.modelManager.title}</strong>
            <span>管理模型别名、原生型号与 API Key 配置。</span>
          </div>
        </div>

        <div className="model-list">
          <div className="model-section-title">已配置模型</div>
          {models.length === 0 && <p className="model-empty">{zh.modelManager.empty}</p>}
          {models.map((model) => (
            <div key={model.provider} className="model-card">
              <div className="model-card-top">
                <div className="model-card-name">
                  {editingProvider === model.provider ? (
                    <div className="model-alias-edit">
                      <input
                        autoFocus
                        value={editingAlias}
                        onChange={(event) => setEditingAlias(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') saveAlias(model.provider);
                          if (event.key === 'Escape') setEditingProvider(null);
                        }}
                      />
                      <button className="codex-button primary compact" type="button" onClick={() => saveAlias(model.provider)}>保存</button>
                    </div>
                  ) : (
                    <button className="model-alias-button" type="button" onClick={() => startEdit(model)}>
                      <strong>{model.alias || '未命名模型'}</strong>
                      <em>点击重命名</em>
                    </button>
                  )}
                  <span>原生型号：{model.model}</span>
                </div>
                <span className="model-provider-badge">{model.provider}</span>
              </div>
              <div className="model-card-actions">
                <button type="button" onClick={() => onRemoveKey(model.provider)}>{zh.modelManager.remove}</button>
              </div>
            </div>
          ))}
        </div>

        <div className="model-add-card">
          <div>
            <strong>极速添加新模型</strong>
            <span>系统会根据 API Key 格式自动识别平台。</span>
          </div>
          <div className="api-key-row">
            <input
              type="password"
              value={newApiKey}
              onChange={(event) => setNewApiKey(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && onAddKey()}
              placeholder={zh.modelManager.apiKeyPlaceholder}
            />
            <button className="codex-button primary" type="button" onClick={onAddKey}>{zh.modelManager.add}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ msg, MarkdownRenderer, onEditRequirement, onConfirmApi, onSaveCodeLocal, onDeepThinkApi }) {
  const isUser = msg.role === 'user';
  const gpuActions = resolveGpuAssistActions(msg);
  return (
    <article className={`chat-message ${isUser ? 'user' : 'agent'} ${msg.type || ''}`}>
      <div className="message-avatar">{isUser ? <User size={15} /> : <Bot size={15} />}</div>
      <div className="message-body">
        <div className="message-meta">
          <span>{isUser ? zh.status.user : 'Ai Multi Agent'}</span>
          {msg.routed_by && <em>{formatRoutedByLabel(msg.routed_by)}</em>}
        </div>
        <ExecutionSteps workflow={msg.workflow || []} />
        {msg.type === 'approval_required' ? (
          <ApprovalCard content={msg.content || ''} />
        ) : (
          <MarkdownRenderer content={msg.content || ''} type={msg.type} />
        )}
        <GPUAssistActions
          actions={gpuActions}
          onEditRequirement={() => onEditRequirement?.(msg)}
          onConfirmApi={() => onConfirmApi?.(msg)}
          onSaveCodeLocal={() => onSaveCodeLocal?.(msg)}
          onDeepThinkApi={() => onDeepThinkApi?.(msg)}
        />
        <TokenUsageBadge usage={msg.token_usage || msg.metadata?.token_usage} />
      </div>
    </article>
  );
}

function ChatComposer({
  input,
  setInput,
  isLoading,
  activeProvider,
  setActiveProvider,
  models,
  workflowMode,
  setWorkflowMode,
  workflowTemplates = [],
  sessionWorkflowSummary,
  onLoadWorkflowTemplate,
  onClearSessionWorkflow,
  onOpenWorkflowTemplates,
  autonomyMode,
  setAutonomyMode,
  workspacePath,
  onBindWorkspace,
  onSend,
  onAbort,
  focusSignal,
}) {
  const [openPanel, setOpenPanel] = useState(null);
  const textareaRef = useRef(null);
  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    const maxHeight = 220;
    el.style.height = 'auto';
    const nextHeight = Math.min(Math.max(el.scrollHeight, 54), maxHeight);
    el.style.height = `${nextHeight}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden';
  };

  useEffect(() => {
    resizeTextarea();
  }, [input]);

  useEffect(() => {
    if (!focusSignal) return;
    const el = textareaRef.current;
    if (!el) return;
    el.focus();
    const cursor = el.value.length;
    el.setSelectionRange(cursor, cursor);
    resizeTextarea();
  }, [focusSignal]);

  const modelOptions = [
    { value: 'auto', label: zh.composer.autoRoute, description: '由 Ai Multi Agent 自动选择可用模型' },
    ...models.map((model) => ({
      value: model.provider,
      label: model.alias || model.provider,
      description: model.model
    }))
  ];
  const baseWorkflowOptions = [
    { value: 'standard', label: zh.workflowMode.standard, description: '快速完成明确任务' },
    { value: 'deep_thought', label: zh.workflowMode.deep_thought, description: '复杂任务先理解再执行' },
    { value: 'expert_review', label: zh.workflowMode.expert_review, description: '更强调检查与风险' },
    { value: 'creative_brainstorm', label: zh.workflowMode.creative_brainstorm, description: '适合方案发散' },
  ];
  const workflowOptions = sessionWorkflowSummary
    ? [
        {
          value: 'session_workflow',
          label: sessionWorkflowSummary.template_name || '模板工作流',
          description: `${sessionWorkflowSummary.node_count || 0} 节点 · 当前会话已接入`,
        },
        ...baseWorkflowOptions,
      ]
    : baseWorkflowOptions;
  const currentWorkflow = workflowOptions.find((option) => option.value === workflowMode) || workflowOptions[0];
  const autonomyOptions = [
    { value: 'supervised_auto', label: zh.autonomyMode.supervised_auto, description: '普通读写运行主动执行，高风险先确认' },
    { value: 'ask_each_step', label: zh.autonomyMode.ask_each_step, description: '每一步执行前都询问' },
    { value: 'full_auto', label: zh.autonomyMode.full_auto, description: '尽可能自动推进' },
  ];

  return (
    <div className="chat-composer">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            onSend();
          }
        }}
        placeholder={zh.composer.placeholder}
        disabled={isLoading}
      />
      <div className="composer-toolbar">
        <OptionPopover
          id="model"
          label={zh.composer.model}
          icon={<Bot size={15} />}
          value={activeProvider || 'auto'}
          options={modelOptions}
          openPanel={openPanel}
          setOpenPanel={setOpenPanel}
          onChange={setActiveProvider}
        />
        <BasePopover
          open={openPanel === 'workflow'}
          onOpenChange={(nextOpen) => setOpenPanel(nextOpen ? 'workflow' : null)}
          align="start"
          trigger={({ toggle }) => (
            <button className={`composer-chip ${openPanel === 'workflow' ? 'active' : ''}`} type="button" onClick={toggle}>
              <SlidersHorizontal size={15} />
              <span>{zh.composer.workflow}</span>
              <strong>{currentWorkflow?.label}</strong>
              <ChevronDown size={14} />
            </button>
          )}
        >
          <div className="popover-title">{zh.composer.workflow}</div>
          <div className="workflow-popover">
            <div className="workflow-popover-section">
              <span>执行模式</span>
              <div className="popover-options">
                {workflowOptions.map((option) => (
                  <button
                    type="button"
                    key={option.value}
                    className={option.value === workflowMode ? 'selected' : ''}
                    onClick={() => {
                      setWorkflowMode(option.value);
                      setOpenPanel(null);
                    }}
                  >
                    <span>
                      <strong>{option.label}</strong>
                      {option.description && <em>{option.description}</em>}
                    </span>
                    {option.value === workflowMode && <Check size={15} />}
                  </button>
                ))}
              </div>
            </div>
            <div className="workflow-popover-section">
              <span>当前会话工作流</span>
              {sessionWorkflowSummary ? (
                <div className="workflow-current-card">
                  <strong>{sessionWorkflowSummary.template_name || '当前会话工作流'}</strong>
                  <em>{sessionWorkflowSummary.node_count || 0} 节点 / {sessionWorkflowSummary.edge_count || 0} 连线</em>
                  <div>
                    <small>{sessionWorkflowSummary.whether_gpu_needed ? 'GPU' : 'GPU 可选'}</small>
                    <small>{sessionWorkflowSummary.whether_api_needed ? 'API' : 'API 可选'}</small>
                    <small>{sessionWorkflowSummary.requires_workspace ? '需要工作区' : '工作区可选'}</small>
                  </div>
                  <button type="button" onClick={() => { setOpenPanel(null); onClearSessionWorkflow?.(); }}>解除接入</button>
                </div>
              ) : (
                <p className="workflow-empty-note">还没有把模板接入当前对话。</p>
              )}
            </div>
            <div className="workflow-popover-section">
              <span>比赛演示模板</span>
              <div className="workflow-template-list">
                {workflowTemplates.slice(0, 6).map((template) => (
                  <button
                    type="button"
                    key={template.template_id}
                    className={sessionWorkflowSummary?.template_id === template.template_id ? 'active' : ''}
                    onClick={() => {
                      setOpenPanel(null);
                      onLoadWorkflowTemplate?.(template.template_id);
                    }}
                  >
                    <GitBranch size={14} />
                    <span>
                      <strong>{template.title}</strong>
                      <em>{template.node_count || 0} 节点 · {template.whether_gpu_needed ? 'GPU' : 'GPU 可选'} / {template.whether_api_needed ? 'API' : 'API 可选'} · {template.requires_workspace ? '需要工作区' : '工作区可选'}</em>
                    </span>
                  </button>
                ))}
              </div>
              <button className="codex-button subtle compact workflow-library-button" type="button" onClick={() => { setOpenPanel(null); onOpenWorkflowTemplates?.(); }}>
                打开工作流模板库
              </button>
            </div>
          </div>
        </BasePopover>
        <OptionPopover
          id="autonomy"
          label={zh.composer.autonomy}
          icon={<Sparkles size={15} />}
          value={autonomyMode}
          options={autonomyOptions}
          openPanel={openPanel}
          setOpenPanel={setOpenPanel}
          onChange={setAutonomyMode}
        />
        <BasePopover
          open={openPanel === 'workspace'}
          onOpenChange={(nextOpen) => setOpenPanel(nextOpen ? 'workspace' : null)}
          align="start"
          trigger={({ toggle }) => (
            <button className={`composer-chip workspace-button ${workspacePath ? 'bound' : ''}`} type="button" onClick={toggle}>
              <Folder size={15} />
              <span>{zh.composer.workspace}</span>
              <strong>{workspacePath ? zh.composer.workspaceBound : zh.composer.bindWorkspace}</strong>
              <ChevronDown size={14} />
            </button>
          )}
        >
          <div className="popover-title">{zh.composer.workspace}</div>
          <div className="workspace-popover">
            <span>{workspacePath ? '当前绑定目录' : '当前还没有绑定工作区'}</span>
            <strong>{workspacePath || '绑定后 Agent 才能安全读写项目文件'}</strong>
            <button className="codex-button primary" type="button" onClick={() => { setOpenPanel(null); onBindWorkspace(); }}>
              {workspacePath ? '重新绑定' : zh.composer.bindWorkspace}
            </button>
          </div>
        </BasePopover>
        <BasePopover
          open={openPanel === 'help'}
          onOpenChange={(nextOpen) => setOpenPanel(nextOpen ? 'help' : null)}
          align="end"
          trigger={({ toggle }) => (
            <BaseIconButton label={zh.composer.help} tooltip={zh.composer.help} onClick={toggle}>
              <HelpCircle size={16} />
            </BaseIconButton>
          )}
        >
          <div className="popover-title">{zh.composer.help}</div>
          <div className="help-popover">
            <p>直接描述目标，Ai Multi Agent 会先理解项目，再主动修改、运行和修复。</p>
            <p>危险动作会显示确认卡片，不会静默执行。</p>
          </div>
        </BasePopover>
        {isLoading ? (
          <button className="send-button stop" type="button" onClick={onAbort}><Square size={15} /> {zh.composer.stop}</button>
        ) : (
          <button className="send-button" type="button" onClick={onSend}><Send size={15} /> {zh.composer.send}</button>
        )}
      </div>
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([{ role: 'agent', content: WELCOME_MESSAGE }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [actionLogs, setActionLogs] = useState([]);
  const [activeWorkflow, setActiveWorkflow] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => localStorage.getItem('skyt.sidebarOpen') !== 'false');
  const [isPlanPanelOpen, setIsPlanPanelOpen] = useState(false);
  const [currentPlanContent, setCurrentPlanContent] = useState('');
  const [backendError, setBackendError] = useState(false);
  const [sessionId, setSessionId] = useState('default');
  const [workflowMode, setWorkflowMode] = useState('deep_thought');
  const [autonomyMode, setAutonomyMode] = useState('supervised_auto');
  const [sessions, setSessions] = useState([]);
  const [userLocation, setUserLocation] = useState(null);
  const [workspacePath, setWorkspacePath] = useState('');
  const [models, setModels] = useState([]);
  const [activeProvider, setActiveProvider] = useState('auto');
  const [showModelManager, setShowModelManager] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [skills, setSkills] = useState([]);
  const [enabledSkills, setEnabledSkills] = useState([]);
  const [workflowTemplates, setWorkflowTemplates] = useState([]);
  const [sessionWorkflowSummary, setSessionWorkflowSummary] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [pendingDeleteSession, setPendingDeleteSession] = useState(null);
  const [composerFocusSignal, setComposerFocusSignal] = useState(0);
  const [browserTarget, setBrowserTarget] = useState(null);
  const chatContainerRef = useRef(null);
  const shouldAutoScrollRef = useRef(true);
  const navigate = useNavigate();
  const location = useLocation();

  const isNearChatBottom = (element) => {
    if (!element) return true;
    return element.scrollHeight - element.scrollTop - element.clientHeight < 96;
  };

  const handleChatScroll = () => {
    const element = chatContainerRef.current;
    shouldAutoScrollRef.current = isNearChatBottom(element);
  };

  const routeTitle = useMemo(() => {
    if (location.pathname === '/') return zh.nav.chat;
    if (location.pathname.startsWith('/dashboard')) return zh.nav.dashboard;
    if (location.pathname.startsWith('/history')) return zh.nav.history;
    if (location.pathname.startsWith('/workflows')) return zh.nav.workflows;
    if (location.pathname.startsWith('/reports')) return zh.nav.reports;
    if (location.pathname.startsWith('/skills')) return zh.nav.skills;
    if (location.pathname.startsWith('/replay')) return zh.nav.replay;
    return 'Ai Multi Agent';
  }, [location.pathname]);

  useEffect(() => {
    if (!('geolocation' in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (position) => setUserLocation({ lat: position.coords.latitude, lon: position.coords.longitude }),
      (error) => console.warn('Geolocation warning:', error.message),
      { timeout: 10000 }
    );
  }, []);

  useEffect(() => {
    localStorage.setItem('skyt.sidebarOpen', isSidebarOpen ? 'true' : 'false');
  }, [isSidebarOpen]);

  useEffect(() => {
    setTimeout(() => {
      const element = chatContainerRef.current;
      if (!element || !shouldAutoScrollRef.current) return;
      element.scrollTo({ top: element.scrollHeight, behavior: isLoading ? 'auto' : 'smooth' });
    }, 60);
  }, [messages, isLoading, actionLogs]);

  const fetchSessions = async () => {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (res.ok) {
      const data = await res.json();
      setSessions(data.sessions || []);
    }
  };

  const fetchHistory = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/api/history/${sid}`);
      if (!res.ok) return;
      const data = await res.json();
      const historyMessages = (data.history || []).map(normalizeHistoryMessage);
      const lastHistoryMessage = historyMessages[historyMessages.length - 1];
      shouldAutoScrollRef.current = true;
      setMessages(historyMessages.length ? [{ role: 'agent', content: WELCOME_MESSAGE }, ...historyMessages] : [{ role: 'agent', content: WELCOME_MESSAGE }]);
      if (lastHistoryMessage?.role === 'agent' && lastHistoryMessage.type === 'plan') {
        setCurrentPlanContent(lastHistoryMessage.content || '');
        setIsPlanPanelOpen(true);
      } else {
        setCurrentPlanContent('');
        setIsPlanPanelOpen(false);
      }
      setBackendError(false);
    } catch (error) {
      console.error(error);
      setBackendError(true);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models`);
      const data = await res.json();
      setModels(data.models || []);
      setBackendError(false);
    } catch (error) {
      console.error(error);
      setModels([]);
      setBackendError(true);
    }
  };

  const fetchSkills = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/skills`);
      if (!res.ok) return;
      const data = await res.json();
      const fetched = data.skills || [];
      setSkills(fetched);
      setEnabledSkills(fetched.map((skill) => skill.function.name));
    } catch (error) {
      console.error(error);
    }
  };

  const fetchWorkflowTemplates = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/workflows/templates`);
      if (!res.ok) return;
      const data = await res.json();
      setWorkflowTemplates(data.templates || []);
    } catch (error) {
      console.error(error);
    }
  };

  const fetchSessionWorkflow = async (sid = sessionId, activate = false) => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sid}/workflow`);
      if (!res.ok) return null;
      const data = await res.json();
      const summary = data.workflow_summary || null;
      setSessionWorkflowSummary(summary);
      if (activate) {
        setWorkflowMode((mode) => summary ? 'session_workflow' : (mode === 'session_workflow' ? 'deep_thought' : mode));
      }
      return summary;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  useEffect(() => {
    fetchModels();
    fetchSessions();
    fetchSkills();
    fetchWorkflowTemplates();
    fetchSessionWorkflow(sessionId, true);
    fetchHistory(sessionId);
  }, []);

  useEffect(() => {
    fetchHistory(sessionId);
    fetchSessionWorkflow(sessionId, true);
  }, [sessionId]);

  const handleNewChat = () => {
    const nextId = Date.now().toString();
    shouldAutoScrollRef.current = true;
    setSessionId(nextId);
    setMessages([{ role: 'agent', content: WELCOME_MESSAGE }]);
    setActionLogs([]);
    setActiveWorkflow([]);
    setCurrentPlanContent('');
    setIsPlanPanelOpen(false);
    setSessionWorkflowSummary(null);
    setWorkflowMode((mode) => mode === 'session_workflow' ? 'deep_thought' : mode);
    navigate('/');
  };

  const handleSelectSession = (sid) => {
    setSessionId(sid);
    navigate('/');
  };

  const handleClearHistory = async () => {
    setShowClearConfirm(false);
    await fetch(`${API_BASE}/api/history/clear/${sessionId}`, { method: 'POST' });
    handleNewChat();
    fetchSessions();
  };

  const handleDeleteSession = async (targetSession) => {
    if (!targetSession?.session_id) return;
    setPendingDeleteSession(null);
    await fetch(`${API_BASE}/api/history/clear/${targetSession.session_id}`, { method: 'POST' });
    const remaining = sessions.filter((session) => session.session_id !== targetSession.session_id);
    setSessions(remaining);
    if (targetSession.session_id === sessionId) {
      const nextSession = remaining[0];
      if (nextSession?.session_id) {
        handleSelectSession(nextSession.session_id);
      } else {
        handleNewChat();
      }
    }
    fetchSessions();
  };

  const handleAddKey = async () => {
    if (!newApiKey.trim()) return;
    await fetch(`${API_BASE}/api/models/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: newApiKey.trim() })
    });
    setNewApiKey('');
    fetchModels();
  };

  const handleRemoveKey = async (provider) => {
    await fetch(`${API_BASE}/api/models/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider })
    });
    fetchModels();
  };

  const handleUpdateAlias = async (provider, alias) => {
    await fetch(`${API_BASE}/api/models/alias`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, alias })
    });
    fetchModels();
  };

  const handleBindWorkspace = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/bind`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setWorkspacePath(data.path);
        setMessages((prev) => [...prev, { role: 'agent', content: `工作区已绑定：\`${data.path}\`` }]);
        return data.path;
      }
      return null;
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', type: 'error', content: `绑定工作区失败：${error.message}` }]);
      return null;
    }
  };

  const handleRunCommand = async (command) => {
    const res = await fetch(`${API_BASE}/api/workspace/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, workspace: workspacePath })
    });
    const data = await res.json();
    setMessages((prev) => [...prev, { role: 'agent', content: `已请求执行：\`${command}\`\n\n${data.output || ''}` }]);
    const url = data.browser_url || extractFirstLocalUrl(`${command}\n${data.output || ''}`);
    if (url) {
      setBrowserTarget({ url, source: 'command', ts: Date.now() });
    }
  };

  const handleLoadWorkflowTemplateToSession = async (templateId) => {
    try {
      const templateRes = await fetch(`${API_BASE}/api/workflows/templates/${templateId}`);
      if (!templateRes.ok) throw new Error('模板读取失败');
      const templateData = await templateRes.json();
      const template = templateData.template;
      const saveRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_json: template.workflow_json }),
      });
      const saveData = await saveRes.json().catch(() => ({}));
      if (!saveRes.ok) throw new Error(saveData.detail || '会话工作流保存失败');
      const summary = saveData.workflow_summary || {
        template_id: template.template_id,
        template_name: template.title,
        node_count: template.node_count,
        edge_count: template.edge_count,
        whether_api_needed: template.whether_api_needed,
        whether_gpu_needed: template.whether_gpu_needed,
        requires_workspace: template.requires_workspace,
        artifact_policy: template.artifact_policy,
        preview_policy: template.preview_policy,
      };
      setSessionWorkflowSummary(summary);
      setWorkflowMode('session_workflow');
      setMessages((prev) => [...prev, {
        role: 'agent',
        routed_by: 'System',
        content: `已接入当前会话工作流：\`${summary.template_name || template.title}\`\n\n之后在底部工作流选择“${summary.template_name || '模板工作流'}”时，发送消息会按该模板执行。`
      }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', type: 'error', content: `接入工作流模板失败：${error.message}` }]);
    }
  };

  const handleClearSessionWorkflow = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_json: null }),
      });
      if (!res.ok) throw new Error('解除接入失败');
      setSessionWorkflowSummary(null);
      setWorkflowMode((mode) => mode === 'session_workflow' ? 'deep_thought' : mode);
      setMessages((prev) => [...prev, { role: 'agent', routed_by: 'System', content: '已解除当前会话工作流接入。' }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', type: 'error', content: `解除工作流失败：${error.message}` }]);
    }
  };

  const handleStreamResponse = async (res) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let workflowSnapshot = [];
    let tokenUsageSnapshot = null;

    const upsertWorkflowSnapshot = (event) => {
      const existingIdx = workflowSnapshot.findIndex((item) => item.node === event.node);
      const nextStep = {
        node: event.node,
        state: event.state,
        routed_by: event.routed_by,
        description: event.description,
        token_usage: event.token_usage,
      };
      if (existingIdx >= 0) {
        workflowSnapshot = workflowSnapshot.map((item, index) => index === existingIdx ? { ...item, ...nextStep } : item);
      } else {
        workflowSnapshot = [...workflowSnapshot, nextStep];
      }
      return workflowSnapshot;
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        let data;
        try {
          data = JSON.parse(line);
        } catch (error) {
          console.warn('Failed to parse stream line', line, error);
          continue;
        }

        if (data.type === 'browser_open' && data.url) {
          setBrowserTarget({ url: data.url, source: data.source || 'workflow', ts: Date.now(), run_id: data.run_id });
          continue;
        }

        if (data.type === 'log') {
          setActionLogs((prev) => [...prev, data.log]);
          continue;
        }

        if (data.type === 'workflow' || data.type === 'execution_step') {
          const nextWorkflow = upsertWorkflowSnapshot(data);
          setActiveWorkflow(nextWorkflow);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'agent' && last.status === 'streaming') {
              next[next.length - 1] = { ...last, workflow: nextWorkflow };
            }
            return next;
          });
          continue;
        }

        if (data.type === 'token_usage') {
          tokenUsageSnapshot = data.token_usage || normalizeTokenUsage(data);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'agent') {
              next[next.length - 1] = { ...last, token_usage: tokenUsageSnapshot };
            }
            return next;
          });
          continue;
        }

        if (data.type === 'approval_required') {
          setMessages((prev) => [...prev, {
            role: 'agent',
            type: 'approval_required',
            content: data.response || data.plan_content || '',
            routed_by: data.routed_by,
            workflow: workflowSnapshot.length ? [...workflowSnapshot] : undefined,
            token_usage: tokenUsageSnapshot || undefined
          }]);
          continue;
        }

        if (data.status === 'streaming') {
          const incomingType = data.type || 'message';
          const incomingContent = data.plan_content || data.response || '';
          if (incomingType === 'plan') {
            setCurrentPlanContent(incomingContent);
            setIsPlanPanelOpen(true);
          }
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'agent' && last.type === incomingType) {
              next[next.length - 1] = {
                ...last,
                content: incomingContent,
                routed_by: data.routed_by,
                workflow: workflowSnapshot.length ? [...workflowSnapshot] : last.workflow,
                token_usage: tokenUsageSnapshot || last.token_usage,
                actions: data.actions || last.actions,
                context_bundle: data.context_bundle || last.context_bundle,
                run_id: data.run_id || last.run_id,
                status: 'streaming'
              };
            } else {
              next.push({
                role: 'agent',
                type: incomingType,
                content: incomingContent,
                routed_by: data.routed_by,
                workflow: workflowSnapshot.length ? [...workflowSnapshot] : undefined,
                token_usage: tokenUsageSnapshot || undefined,
                actions: data.actions || undefined,
                context_bundle: data.context_bundle || undefined,
                run_id: data.run_id || undefined,
                status: 'streaming'
              });
            }
            return next;
          });
          continue;
        }

        if (data.status === 'done') {
          const incomingType = data.type || 'message';
          const incomingContent = data.plan_content || data.response || '';
          setMessages((prev) => {
            const next = [...prev];
            const newMsg = {
              role: 'agent',
              type: incomingType,
              content: incomingContent,
              routed_by: data.routed_by,
              workflow: workflowSnapshot.length ? [...workflowSnapshot] : undefined,
              token_usage: data.token_usage || tokenUsageSnapshot || undefined,
              actions: data.actions || undefined,
              context_bundle: data.context_bundle || undefined,
              run_id: data.run_id || undefined
            };
            const last = next[next.length - 1];
            if (last?.role === 'agent' && last.type === incomingType) {
              next[next.length - 1] = newMsg;
            } else {
              next.push(newMsg);
            }
            return next;
          });
          if (incomingType === 'plan') {
            setCurrentPlanContent(incomingContent);
            setIsPlanPanelOpen(true);
          }
        }
      }
    }
  };

  const sendMessage = async (customText = null, isEscalation = false, options = {}) => {
    const textToSend = typeof customText === 'string' ? customText : input;
    if (!textToSend.trim() || isLoading) return;
    let requestStarted = false;
    try {
      const shouldRunSessionWorkflow = workflowMode === 'session_workflow' && sessionWorkflowSummary && !options.force_api && !options.context_bundle;
      const workflowSummaryForRequest = options.workflowSummary || (shouldRunSessionWorkflow ? sessionWorkflowSummary : null);
      let requestWorkspace = options.workspaceOverride || workspacePath;
      if (workflowNeedsWorkspace(workflowSummaryForRequest, textToSend) && !requestWorkspace) {
        const selected = await handleBindWorkspace();
        if (!selected) {
          setMessages((prev) => [...prev, {
            role: 'agent',
            routed_by: 'System',
            content: `已取消运行「${workflowSummaryForRequest?.template_name || workflowSummaryForRequest?.title || '工作流模板'}」。该模板需要先绑定工作区后才能写入项目文件。`
          }]);
          return;
        }
        requestWorkspace = selected;
      }

      shouldAutoScrollRef.current = true;
      const displayText = options.displayText || textToSend;
      setMessages((prev) => [...prev, { role: 'user', content: displayText }]);
      setInput('');
      setIsLoading(true);
      requestStarted = true;
      setActionLogs([]);
      setActiveWorkflow([]);

      const contextBundle = options.context_bundle || (shouldRunSessionWorkflow ? {
        action: 'workflow_template_demo',
        template_id: sessionWorkflowSummary.template_id,
        template_name: sessionWorkflowSummary.template_name || '当前会话工作流',
      } : null);
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          provider: activeProvider,
          is_approved: false,
          session_id: sessionId,
          is_escalation: isEscalation,
          location: userLocation,
          enabled_skills: enabledSkills,
          workflow_mode: workflowMode,
          workspace: requestWorkspace,
          autonomy_mode: options.autonomy_mode || autonomyMode,
          force_api: Boolean(options.force_api || shouldRunSessionWorkflow),
          context_bundle: contextBundle
        })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      await handleStreamResponse(res);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', type: 'error', content: `执行失败：${error.message}` }]);
    } finally {
      if (requestStarted) {
        setIsLoading(false);
        setActionLogs([]);
        fetchSessions();
      }
    }
  };

  const handleEditRequirementFromDraft = (msg) => {
    const original = msg.context_bundle?.original_message || '';
    setInput(original || msg.content || '');
    setComposerFocusSignal((value) => value + 1);
    navigate('/');
  };

  const handleConfirmApiFromDraft = (msg) => {
    const bundle = {
      ...(msg.context_bundle || {}),
      original_message: msg.context_bundle?.original_message || msg.content || '',
      gpu_draft: msg.context_bundle?.gpu_draft || msg.content || '',
      context_md: msg.context_bundle?.context_md || msg.content || '',
      source_run_id: msg.context_bundle?.source_run_id || msg.run_id,
      action: 'direct_api'
    };
    sendMessage(bundle.original_message || '基于本地 GPU 初稿调用 API 深度方案', false, {
      force_api: true,
      context_bundle: bundle,
      displayText: '确认，生成 API 深度计划'
    });
  };

  const handleSaveCodeLocalFromDraft = async (msg) => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/gpu-draft/save-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          response_text: msg.content || msg.context_bundle?.gpu_draft || '',
          workspace: workspacePath || null,
          run_id: msg.run_id || msg.context_bundle?.source_run_id || null
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      if (data.status === 'success') {
        const savedList = (data.saved_files || []).map((file) => `- \`${file}\``).join('\n');
        setMessages((prev) => [...prev, {
          role: 'agent',
          content: `已保存 GPU 代码草稿到：\`${data.target_dir}\`\n\n${savedList}`,
          routed_by: 'System'
        }]);
      } else {
        setMessages((prev) => [...prev, {
          role: 'agent',
          content: data.message || '没有保存任何文件。',
          routed_by: 'System'
        }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'agent', type: 'error', content: `保存到本地失败：${error.message}` }]);
    } finally {
      setIsLoading(false);
      fetchSessions();
    }
  };

  const handleDeepThinkApiFromDraft = (msg) => {
    const bundle = {
      ...(msg.context_bundle || {}),
      original_message: msg.context_bundle?.original_message || msg.content || '',
      gpu_draft: msg.context_bundle?.gpu_draft || msg.content || '',
      context_md: msg.context_bundle?.context_md || msg.content || '',
      source_run_id: msg.context_bundle?.source_run_id || msg.run_id,
      action: 'deep_think'
    };
    sendMessage(bundle.original_message || '基于本地 GPU 代码草稿启用深度思考', false, {
      force_api: true,
      context_bundle: bundle,
      displayText: '启用深度思考'
    });
  };

  const handleRunWorkflowTemplate = async (prompt, template = {}) => {
    navigate('/');
    const loadedSummary = await fetchSessionWorkflow(sessionId, true);
    const workflowSummary = {
      ...(loadedSummary || {}),
      template_id: template.templateId || loadedSummary?.template_id,
      template_name: template.templateName || loadedSummary?.template_name,
      requires_workspace: template.requiresWorkspace ?? loadedSummary?.requires_workspace,
      artifact_policy: template.artifactPolicy || loadedSummary?.artifact_policy,
      preview_policy: template.previewPolicy || loadedSummary?.preview_policy,
    };
    await sendMessage(prompt, false, {
      force_api: true,
      autonomy_mode: 'supervised_auto',
      workflowSummary,
      context_bundle: {
        action: 'workflow_template_demo',
        template_id: template.templateId,
        template_name: template.templateName,
      },
      displayText: `运行工作流模板：${template.templateName || 'Workflow Template'}\n\n${prompt}`,
    });
  };

  const handleAbort = async () => {
    await fetch(`${API_BASE}/api/chat/stop/${sessionId}`, { method: 'POST' }).catch(() => {});
    setIsLoading(false);
  };

  const approvePlan = async () => {
    setIsLoading(true);
    setActionLogs([]);
    setActiveWorkflow([]);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          provider: activeProvider,
          is_approved: true,
          session_id: sessionId,
          workflow_mode: workflowMode,
          workspace: workspacePath,
          autonomy_mode: autonomyMode
        })
      });
      setIsPlanPanelOpen(false);
      await handleStreamResponse(res);
    } finally {
      setIsLoading(false);
      setActionLogs([]);
      fetchSessions();
    }
  };

  const MarkdownRenderer = ({ content, type }) => {
    if (type === 'plan') {
      return <div className="plan-placeholder">计划已生成，请在右侧计划面板审查。</div>;
    }

    let renderedContent = content || '';
    let mermaidChart = null;
    const mermaidMatch = /<MERMAID_MINDMAP>([\s\S]*?)<\/MERMAID_MINDMAP>/.exec(renderedContent);
    if (mermaidMatch) {
      mermaidChart = mermaidMatch[1];
      renderedContent = renderedContent.replace(mermaidMatch[0], '');
    }

    return (
      <ErrorBoundaryFallback>
        <div className="markdown-body notranslate" translate="no">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children, ...props }) => {
                if (href?.startsWith('command:')) {
                  const cmd = href.replace('command:', '');
                  return <button className="codex-button primary inline-command-button" onClick={() => handleRunCommand(cmd)}>{children}</button>;
                }
                return <a href={href} {...props} target="_blank" rel="noreferrer">{children}</a>;
              },
              code({ inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <div className="code-card">
                    <div className="code-header">{match[1]}</div>
                    <SyntaxHighlighter {...props} style={vscDarkPlus} language={match[1]} PreTag="div" customStyle={{ margin: 0 }} showLineNumbers>
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  </div>
                ) : (
                  <code {...props} className={className}>{children}</code>
                );
              }
            }}
          >
            {renderedContent}
          </ReactMarkdown>
          {mermaidChart && <MermaidChart chart={mermaidChart} />}
        </div>
      </ErrorBoundaryFallback>
    );
  };

  return (
    <div className="codex-app notranslate" translate="no">
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        sessions={sessions}
        sessionId={sessionId}
        activeProvider={activeProvider}
        workspacePath={workspacePath}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onClear={() => setShowClearConfirm(true)}
        onOpenModelManager={() => setShowModelManager(true)}
        onDeleteSession={setPendingDeleteSession}
      />

      <main className="codex-main">
        <header className="workspace-header">
          <div className="workspace-header-start">
            <button className="mobile-menu-button" type="button" aria-label={isSidebarOpen ? zh.sidebar.collapse : zh.sidebar.expand} onClick={() => setIsSidebarOpen(!isSidebarOpen)}><Menu size={18} /></button>
            <div className="workspace-title">
              <span>Ai Multi Agent</span>
              <strong>{routeTitle}</strong>
            </div>
          </div>
          <div className="workspace-header-status">
            {backendError && <em className="backend-warning">{zh.status.backendDisconnected}</em>}
          </div>
        </header>

        <Routes>
          <Route path="/" element={(
            <section className="chat-workspace">
              <div className="chat-scroll" ref={chatContainerRef} onScroll={handleChatScroll}>
                {messages.map((msg, index) => (
                  <ChatMessage
                    key={`${index}-${msg.role}-${msg.type || 'message'}`}
                    msg={msg}
                    MarkdownRenderer={MarkdownRenderer}
                    onEditRequirement={handleEditRequirementFromDraft}
                    onConfirmApi={handleConfirmApiFromDraft}
                    onSaveCodeLocal={handleSaveCodeLocalFromDraft}
                    onDeepThinkApi={handleDeepThinkApiFromDraft}
                  />
                ))}
                {isLoading && (
                  <article className="chat-message agent loading">
                    <div className="message-avatar"><Bot size={15} /></div>
                    <div className="message-body">
                      <div className="message-meta"><span>Ai Multi Agent</span><em>{zh.status.working}</em></div>
                      <ExecutionSteps workflow={activeWorkflow} logs={actionLogs} />
                      <div className="thinking-row"><span /> <span /> <span /> 正在动手处理...</div>
                    </div>
                  </article>
                )}
              </div>
              <ChatComposer
                input={input}
                setInput={setInput}
                isLoading={isLoading}
                activeProvider={activeProvider}
                setActiveProvider={setActiveProvider}
                models={models}
                workflowMode={workflowMode}
                setWorkflowMode={setWorkflowMode}
                workflowTemplates={workflowTemplates}
                sessionWorkflowSummary={sessionWorkflowSummary}
                onLoadWorkflowTemplate={handleLoadWorkflowTemplateToSession}
                onClearSessionWorkflow={handleClearSessionWorkflow}
                onOpenWorkflowTemplates={() => navigate('/workflows')}
                autonomyMode={autonomyMode}
                setAutonomyMode={setAutonomyMode}
                workspacePath={workspacePath}
                onBindWorkspace={handleBindWorkspace}
                onSend={() => sendMessage()}
                onAbort={handleAbort}
                focusSignal={composerFocusSignal}
              />
            </section>
          )} />
          <Route path="/skills" element={<div className="routed-view"><SkillsStore skills={skills} enabledSkills={enabledSkills} setEnabledSkills={setEnabledSkills} onImportSkill={fetchSkills} /></div>} />
          <Route path="/workflows" element={<div className="routed-view"><Workflows sessionId={sessionId} onRunWorkflowTemplate={handleRunWorkflowTemplate} workspacePath={workspacePath} onBindWorkspace={handleBindWorkspace} /></div>} />
          <Route path="/workflows/editor" element={<div className="routed-view flush"><WorkflowEditorPage /></div>} />
          <Route path="/dashboard" element={<div className="routed-view"><Dashboard /></div>} />
          <Route path="/history" element={<div className="routed-view"><RunHistory /></div>} />
          <Route path="/replay/:runId" element={<div className="routed-view"><WorkflowReplay /></div>} />
          <Route path="/reports" element={<div className="routed-view"><Reports /></div>} />
        </Routes>
      </main>

      <ActionDock
        workspacePath={workspacePath}
        activeWorkflow={activeWorkflow}
        actionLogs={actionLogs}
        currentPlanContent={currentPlanContent}
        isPlanPanelOpen={isPlanPanelOpen}
        onPlanClose={() => setIsPlanPanelOpen(false)}
        onApprovePlan={approvePlan}
        onBindWorkspace={handleBindWorkspace}
        onNavigate={navigate}
        onNewChat={handleNewChat}
        browserTarget={browserTarget}
      />

      <ModelManager
        open={showModelManager}
        onClose={() => setShowModelManager(false)}
        models={models}
        newApiKey={newApiKey}
        setNewApiKey={setNewApiKey}
        onAddKey={handleAddKey}
        onRemoveKey={handleRemoveKey}
        onUpdateAlias={handleUpdateAlias}
      />

      <ConfirmDialog
        open={showClearConfirm}
        heading={zh.confirm.clearTitle}
        description={zh.confirm.clearDescription}
        cancelLabel={zh.confirm.cancel}
        confirmLabel={zh.confirm.clear}
        danger
        onCancel={() => setShowClearConfirm(false)}
        onConfirm={handleClearHistory}
      />
      <ConfirmDialog
        open={Boolean(pendingDeleteSession)}
        heading={zh.confirm.deleteTitle}
        description={zh.confirm.deleteDescription}
        cancelLabel={zh.confirm.cancel}
        confirmLabel={zh.confirm.delete}
        danger
        onCancel={() => setPendingDeleteSession(null)}
        onConfirm={() => handleDeleteSession(pendingDeleteSession)}
      />
    </div>
  );
}

export default App;
