import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Folder,
  Globe2,
  LayoutTemplate,
  Maximize2,
  Play,
  RefreshCw,
  ShieldCheck,
  TerminalSquare,
  Wrench,
  X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ActionCard from './ActionCard';
import TerminalPanel from './TerminalPanel';
import BaseIconButton from './ui/BaseIconButton';
import { zh } from '../i18n/zh';

const API_BASE = `http://${window.location.hostname}:8000`;
const DEFAULT_BROWSER_URL = 'http://127.0.0.1:5173/dashboard';
const clampDockWidth = (value) => Math.min(760, Math.max(320, Number(value) || 380));

function BrowserPanel({ target, onRequestWide }) {
  const [url, setUrl] = useState(DEFAULT_BROWSER_URL);
  const [currentUrl, setCurrentUrl] = useState(DEFAULT_BROWSER_URL);
  const [history, setHistory] = useState([DEFAULT_BROWSER_URL]);
  const [key, setKey] = useState(0);

  useEffect(() => {
    if (!target?.url) return;
    const next = /^https?:\/\//i.test(target.url) ? target.url : `https://${target.url}`;
    setUrl(next);
    setCurrentUrl(next);
    setHistory((prev) => (prev[prev.length - 1] === next ? prev : [...prev, next]));
    setKey((value) => value + 1);
  }, [target?.url, target?.ts]);

  const navigate = () => {
    const next = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    setCurrentUrl(next);
    setUrl(next);
    setHistory((prev) => [...prev, next]);
  };

  const goBack = () => {
    setHistory((prev) => {
      if (prev.length <= 1) return prev;
      const next = prev.slice(0, -1);
      setCurrentUrl(next[next.length - 1]);
      setUrl(next[next.length - 1]);
      return next;
    });
  };

  const openSystem = async () => {
    await fetch(`${API_BASE}/api/browser/open-system`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: currentUrl })
    });
  };

  return (
    <div className="dock-panel browser-panel">
      <div className="browser-toolbar">
        <BaseIconButton label="后退" tooltip="后退" onClick={goBack}><ArrowLeft size={16} /></BaseIconButton>
        <BaseIconButton label="刷新" tooltip="刷新" onClick={() => setKey((value) => value + 1)}><RefreshCw size={16} /></BaseIconButton>
        <input
          value={url}
          aria-label="浏览器地址"
          placeholder="输入网址"
          onChange={(event) => setUrl(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && navigate()}
        />
        <BaseIconButton label="打开" tooltip="打开" onClick={navigate}><Globe2 size={16} /></BaseIconButton>
        <BaseIconButton label="宽屏预览" tooltip="宽屏预览" onClick={onRequestWide}><Maximize2 size={16} /></BaseIconButton>
        <BaseIconButton label="在系统浏览器打开" tooltip="在系统浏览器打开" onClick={openSystem}><ExternalLink size={16} /></BaseIconButton>
      </div>
      <div className="browser-frame-shell">
        <iframe key={`${currentUrl}-${key}`} src={currentUrl} aria-label="天韬（SkyT） 内置浏览器" sandbox="allow-same-origin allow-scripts allow-forms allow-popups" />
        <div className="browser-fallback">
          <strong>页面拒绝嵌入时</strong>
          <span>使用右上角“在系统浏览器打开”继续访问。</span>
        </div>
      </div>
    </div>
  );
}

function PlanPanel({ currentPlanContent, onApprove, onClose }) {
  return (
    <div className="dock-panel plan-review-panel">
      <div className="dock-panel-header">
        <LayoutTemplate size={18} />
        <span>计划审查</span>
        <BaseIconButton label="关闭计划" tooltip="关闭计划" onClick={onClose}><X size={16} /></BaseIconButton>
      </div>
      <div className="plan-review-body markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{currentPlanContent || '暂无待审查计划。'}</ReactMarkdown>
      </div>
      <div className="plan-review-actions">
        <button className="codex-button subtle" type="button" onClick={onClose}>稍后</button>
        <button className="codex-button primary" type="button" onClick={onApprove}>批准执行</button>
      </div>
    </div>
  );
}

function WorkflowPanel({ workflow, logs }) {
  return (
    <div className="dock-panel mini-workflow-panel">
      <div className="dock-panel-header">
        <Activity size={18} />
        <span>执行与修复</span>
      </div>
      <div className="mini-steps">
        {workflow.length === 0 && logs.length === 0 ? (
          <p>暂无运行中的任务。</p>
        ) : null}
        {workflow.map((step, index) => (
          <div key={`${step.node}-${index}`} className={`mini-step ${step.state || 'running'}`}>
            <span>{index + 1}</span>
            <strong>{step.node}</strong>
            {step.token_usage?.total_tokens ? <small>{step.token_usage.total_tokens} tokens</small> : null}
            <em>{step.state || 'running'}</em>
          </div>
        ))}
        {logs.slice(-8).map((log, index) => (
          <pre key={`${log}-${index}`}>{log}</pre>
        ))}
      </div>
    </div>
  );
}

function WorkspacePanel({ workspacePath, onBindWorkspace }) {
  return (
    <div className="dock-panel workspace-panel">
      <div className="dock-panel-header">
        <Folder size={18} />
        <span>工作区</span>
      </div>
      <div className="workspace-panel-body">
        <span>{workspacePath ? '当前绑定目录' : '还没有绑定工作区'}</span>
        <strong>{workspacePath || '绑定后 天韬（SkyT） 才会在明确项目边界内读写和运行。'}</strong>
        <button className="codex-button primary" type="button" onClick={onBindWorkspace}>
          {workspacePath ? '重新绑定工作区' : '绑定工作区'}
        </button>
      </div>
    </div>
  );
}

export default function ActionDock({
  workspacePath,
  activeWorkflow,
  actionLogs,
  currentPlanContent,
  isPlanPanelOpen,
  onPlanClose,
  onApprovePlan,
  onBindWorkspace,
  onNavigate,
  onNewChat,
  browserTarget,
}) {
  const [isOpen, setIsOpen] = useState(() => localStorage.getItem('skyt.actionDockOpen') !== 'false');
  const [mode, setMode] = useState('home');
  const [queuedCommand, setQueuedCommand] = useState('');
  const [dockWidth, setDockWidth] = useState(() => clampDockWidth(localStorage.getItem('skyt.actionDockWidth') || 380));
  const dragStateRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('skyt.actionDockOpen', isOpen ? 'true' : 'false');
  }, [isOpen]);

  useEffect(() => {
    localStorage.setItem('skyt.actionDockWidth', String(dockWidth));
  }, [dockWidth]);

  useEffect(() => {
    if (isPlanPanelOpen) setIsOpen(true);
  }, [isPlanPanelOpen]);

  useEffect(() => {
    if (!browserTarget?.url) return;
    setIsOpen(true);
    setDockWidth((value) => clampDockWidth(Math.max(value, 680)));
    if (isPlanPanelOpen) onPlanClose?.();
    setMode('browser');
  }, [browserTarget?.url, browserTarget?.ts]);

  const startResize = (event) => {
    event.preventDefault();
    dragStateRef.current = { startX: event.clientX, startWidth: dockWidth };
    document.body.classList.add('resizing-action-dock');

    const handleMove = (moveEvent) => {
      if (!dragStateRef.current) return;
      const nextWidth = dragStateRef.current.startWidth + (dragStateRef.current.startX - moveEvent.clientX);
      setDockWidth(clampDockWidth(nextWidth));
    };
    const handleUp = () => {
      dragStateRef.current = null;
      document.body.classList.remove('resizing-action-dock');
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  };

  const openMode = (nextMode) => {
    if (!isOpen) setIsOpen(true);
    if (isPlanPanelOpen && nextMode !== 'plan') onPlanClose?.();
    setMode(nextMode);
  };

  const recommendations = useMemo(() => [
    { label: '打开本地数据看板', icon: <Globe2 size={14} />, action: () => openMode('browser') },
    {
      label: workspacePath ? '在 PowerShell 运行构建' : '先绑定工作区',
      icon: <TerminalSquare size={14} />,
      action: () => workspacePath ? (openMode('terminal'), setQueuedCommand('cd frontend; npm run build')) : openMode('workspace')
    },
    { label: '查看运行历史', icon: <Activity size={14} />, action: () => onNavigate('/history') },
    { label: '新建对话', icon: <Play size={14} />, action: onNewChat },
  ], [workspacePath, onBindWorkspace, onNavigate, onNewChat, isOpen, isPlanPanelOpen]);

  const visibleMode = isPlanPanelOpen ? 'plan' : mode;
  const cards = [
    { key: 'browser', label: '浏览器', description: '打开本地或网页', icon: <Globe2 size={20} />, onClick: () => openMode('browser') },
    { key: 'terminal', label: 'PowerShell', description: '工作区终端', icon: <TerminalSquare size={20} />, onClick: () => openMode('terminal') },
    { key: 'workspace', label: '工作区', description: workspacePath ? '已绑定目录' : '选择目录', icon: <Folder size={20} />, onClick: () => openMode('workspace') },
    { key: 'workflow', label: '执行/修复', description: '运行与问题定位', icon: <Wrench size={20} />, onClick: () => openMode('workflow') },
  ];

  if (!isOpen) {
    return (
      <aside className="action-dock collapsed" aria-label="行动面板">
        <BaseIconButton className="dock-collapse-button" label="展开行动面板" tooltip="展开行动面板" tooltipSide="left" onClick={() => setIsOpen(true)}>
          <ChevronLeft size={18} />
        </BaseIconButton>
        <div className="dock-rail">
          {cards.map((card) => (
            <BaseIconButton
              key={card.key}
              className="dock-rail-button"
              label={card.label}
              tooltip={card.label}
              tooltipSide="left"
              active={visibleMode === card.key}
              onClick={card.onClick}
            >
              {card.icon}
            </BaseIconButton>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside className="action-dock open" aria-label="行动面板" style={{ width: dockWidth, minWidth: dockWidth }}>
      <div className="dock-resize-handle" role="separator" aria-label="调整行动面板宽度" onPointerDown={startResize} />
      <div className="action-dock-header">
        <div>
          <span>行动面板</span>
          <strong>天韬（SkyT） 工作台</strong>
        </div>
        <BaseIconButton className="dock-collapse-button" label="折叠行动面板" tooltip="折叠行动面板" tooltipSide="left" onClick={() => setIsOpen(false)}>
          <ChevronRight size={18} />
        </BaseIconButton>
      </div>

      <span className="autonomy-pill"><ShieldCheck size={14} /> {zh.autonomyMode.supervised_auto}</span>

      <div className="action-grid">
        {cards.map((card) => (
          <ActionCard
            key={card.key}
            icon={card.icon}
            label={card.label}
            description={card.description}
            active={visibleMode === card.key || (card.key === 'workspace' && Boolean(workspacePath) && visibleMode === 'home')}
            onClick={card.onClick}
          />
        ))}
      </div>

      {visibleMode === 'home' && (
        <div className="dock-panel recommendation-panel">
          <h3>推荐操作</h3>
          {recommendations.map((item) => (
            <button key={item.label} type="button" onClick={item.action}>
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
      {visibleMode === 'browser' && <BrowserPanel target={browserTarget} onRequestWide={() => setDockWidth(clampDockWidth(760))} />}
      {visibleMode === 'terminal' && (
        <TerminalPanel
          active={visibleMode === 'terminal'}
          workspacePath={workspacePath}
          queuedCommand={queuedCommand}
          onQueuedCommandConsumed={() => setQueuedCommand('')}
        />
      )}
      {visibleMode === 'workspace' && <WorkspacePanel workspacePath={workspacePath} onBindWorkspace={onBindWorkspace} />}
      {visibleMode === 'workflow' && <WorkflowPanel workflow={activeWorkflow} logs={actionLogs} />}
      {visibleMode === 'plan' && <PlanPanel currentPlanContent={currentPlanContent} onApprove={onApprovePlan} onClose={onPlanClose} />}
    </aside>
  );
}
