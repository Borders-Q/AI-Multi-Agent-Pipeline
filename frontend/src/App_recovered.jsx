import React, { useState, useEffect, useRef } from 'react';
import { Routes, Route, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Settings, Sparkles, User, Bot, LayoutTemplate, Activity, X, History, FileText, Blocks } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import WorkflowEditor from './components/WorkflowEditor';
import ReactECharts from 'echarts-for-react';
import MermaidChart from './components/MermaidChart';
import Dashboard from './views/Dashboard';
import RunHistory from './views/RunHistory';
import WorkflowReplay from './views/WorkflowReplay';
import Reports from './views/Reports';
import SkillsStore from './views/SkillsStore';
import Workflows from './views/Workflows';
import WorkflowEditorPage from './views/WorkflowEditorPage';
import './index.css';

const CustomSelect = ({ value, options, onChange, title }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find(o => o.value === value) || options[0];

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block', minWidth: '140px', maxWidth: '160px', flexShrink: 0 }} title={title}>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          padding: '15px 24px',
          backgroundColor: 'var(--sys-color-surface-variant)',
          borderRadius: 'var(--sys-radius-full)',
          cursor: 'pointer',
          border: '1px solid var(--sys-color-surface-variant)',
          color: 'var(--sys-color-on-surface)',
          fontWeight: '500',
          fontSize: '1rem',
          transition: 'all 0.2s ease',
          userSelect: 'none',
          boxShadow: 'var(--sys-elevation-1)',
          height: '100%'
        }}
      >
        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{selectedOption?.label}</span>
        <span style={{ 
          display: 'flex', 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </span>
      </div>
      
      {isOpen && (
        <div className="animate-fade-in" style={{
          position: 'absolute',
          bottom: '100%',
          left: 0,
          marginBottom: '12px',
          minWidth: '100%',
          backgroundColor: 'var(--sys-color-surface)',
          border: '1px solid var(--sys-color-surface-variant)',
          borderRadius: '24px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
          zIndex: 1000,
          overflow: 'hidden'
        }}>
          {options.map((opt, i) => (
            <div 
              key={i}
              onClick={() => {
                onChange(opt.value);
                setIsOpen(false);
              }}
              style={{
                padding: '14px 24px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                backgroundColor: value === opt.value ? 'var(--sys-color-primary-container)' : 'transparent',
                color: value === opt.value ? 'var(--sys-color-primary)' : 'var(--sys-color-on-surface)',
                fontWeight: value === opt.value ? 'bold' : 'normal',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                if (value !== opt.value) e.currentTarget.style.backgroundColor = 'var(--sys-color-surface-variant)';
              }}
              onMouseLeave={(e) => {
                if (value !== opt.value) e.currentTarget.style.backgroundColor = 'transparent';
              }}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Caught by ErrorBoundary:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return <span style={{ color: 'red', fontSize: '12px' }}>[娓叉煋閿欒: 鍙兘鏄炕璇戞彃浠跺紩璧风殑搴曞眰鍐茬獊锛屽凡瀹夊叏闅旂]</span>;
    }
    return this.props.children;
  }
}

function App() {
  const [messages, setMessages] = useState([{ role: 'agent', content: '欢迎使用 天韬（SkyT） 智能控制台。系统已就绪，请输入您的需求？' }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [actionLogs, setActionLogs] = useState([]);
  const [activeWorkflow, setActiveWorkflow] = useState([]);
  const [todos, setTodos] = useState([]);
  const [enteredSystem, setEnteredSystem] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isWorkflowPanelOpen, setIsWorkflowPanelOpen] = useState(true);
  const [isWorkflowEditorOpen, setIsWorkflowEditorOpen] = useState(false);
  const [isPlanPanelOpen, setIsPlanPanelOpen] = useState(false);
  const [currentPlanContent, setCurrentPlanContent] = useState("");
  const [backendError, setBackendError] = useState(false);
  const [sessionId, setSessionId] = useState('default');
  const [workflowMode, setWorkflowMode] = useState('deep_thought');
  const [sessions, setSessions] = useState([]);
  const [userLocation, setUserLocation] = useState(null);
  const location = useLocation();
  const chatContainerRef = useRef(null);

  // Fetch Geolocation
  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lon: position.coords.longitude
          });
        },
        (error) => {
          console.warn("Geolocation warning:", error.message);
        },
        { timeout: 10000 }
      );
    }
  }, []);

  // Auto-scroll to bottom when messages change or loading state changes
  const scrollToBottom = (behavior = 'smooth') => {
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior
        });
      }
    }, 50);
  };

  useEffect(() => {
    scrollToBottom('smooth');
  }, [messages, isLoading, actionLogs, enteredSystem]);

  // Model Management
  const [models, setModels] = useState([]);
  const [activeProvider, setActiveProvider] = useState('');
  const [showModelManager, setShowModelManager] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [skills, setSkills] = useState([]);
  const [enabledSkills, setEnabledSkills] = useState([]);
  const [currentView, setCurrentView] = useState('chat'); // 'chat' or 'skills'
  const [skillTab, setSkillTab] = useState('local'); // 'local' or 'market'
  const [marketSkills, setMarketSkills] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importCode, setImportCode] = useState(`def my_custom_tool(param1: str):
    return f"Processed {param1}"

SCHEMA = {
    "name": "my_custom_tool",
    "description": "A custom tool that does something.",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "The input"}
        },
        "required": ["param1"]
    }
}`);
  const [importError, setImportError] = useState('');

  const fetchMarketSkills = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/skills/market`);
      if (res.ok) {
        const data = await res.json();
        setMarketSkills(data.market_skills || []);
      }
    } catch (e) {
      console.log("Failed to fetch market skills:", e);
    }
  };

  useEffect(() => {
    if (currentView === 'skills' && skillTab === 'market' && marketSkills.length === 0) {
      fetchMarketSkills();
    }
  }, [currentView, skillTab]);

  const handleDownloadSkill = async (skillId) => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/skills/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skillId })
      });
      if (res.ok) {
        alert("下载并安装成功！");
        fetchSkills();
        setSkillTab('local');
      } else {
        const err = await res.json();
        alert(`瀹夎澶辫触: ${err.detail}`);
      }
    } catch (e) {
      alert(`缃戠粶閿欒: ${e.message}`);
    }
  };

  const handleImportSkill = async () => {
    setImportError('');
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/skills/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: importCode })
      });
      if (res.ok) {
        alert("鑷畾涔夋妧鑳芥敞鍏ユ垚鍔燂紒");
        setIsImportModalOpen(false);
        fetchSkills();
        setSkillTab('local');
      } else {
        const err = await res.json();
        setImportError(err.detail);
      }
    } catch (e) {
      setImportError(`缃戠粶閿欒: ${e.message}`);
    }
  };

  // Fetch Skills
  const fetchSkills = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/skills`);
      if (res.ok) {
        const data = await res.json();
        const fetchedSkills = data.skills || [];
        setSkills(fetchedSkills);
        // Default to all enabled
        setEnabledSkills(fetchedSkills.map(s => s.function.name));
      }
    } catch (e) {
      console.log("Failed to fetch skills:", e);
    }
  };

  // History Management
  const clearHistory = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/history/clear/${sessionId}`, {
        method: 'POST'
      });
      if (res.ok) {
        setMessages([{ role: 'agent', content: '欢迎使用 天韬（SkyT） 智能控制台。系统已就绪，请输入您的需求？' }]);
        setTodos([]);
        setActionLogs([]);
        setActiveWorkflow([]);
        // Switch to a brand new session so the cleared one is fully abandoned
        setSessionId(Date.now().toString());
        await fetchSessions();
      }
    } catch (e) {
      console.log("Failed to clear history:", e);
    }
  };

  const fetchHistory = async (sid) => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/history/${sid}`);
      if (res.ok) {
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          setMessages([
            { role: 'agent', content: '欢迎使用 天韬（SkyT） 智能控制台。系统已就绪，请输入您的需求？' },
            ...data.history
          ]);
        } else {
          setMessages([{ role: 'agent', content: '欢迎使用 天韬（SkyT） 智能控制台。系统已就绪，请输入您的需求？'}]);
        }
        setTimeout(() => scrollToBottom('auto'), 100);
      }
    } catch (e) {
      console.log("Failed to fetch history:", e);
      setBackendError(true);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (e) {
      console.log("Failed to fetch sessions:", e);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/models`);
      const data = await res.json();
      let loadedModels = data.models || [];
      setModels(loadedModels);
      if (loadedModels.length > 0 && !activeProvider) {
        setActiveProvider(loadedModels[0].provider);
      }
      setBackendError(false);
    } catch (e) {
      console.log("Failed to fetch models");
      setModels([]);
      setBackendError(true);
    }
  };

  useEffect(() => {
    fetchModels();
    fetchSessions();
    fetchSkills();
    fetchHistory(sessionId);
  }, []);

  useEffect(() => {
    fetchHistory(sessionId);
  }, [sessionId]);

  const handleNewChat = () => {
    const newId = Date.now().toString();
    setSessionId(newId);
    setMessages([{ role: 'agent', content: '欢迎使用 天韬（SkyT） 智能控制台。系统已就绪，请输入您的需求？'}]);
    setTodos([]);
    setActionLogs([]);
    setActiveWorkflow([]);
    setCurrentView('chat');
  };

  const handleAddKey = async () => {
    if (!newApiKey) return;
    try {
      await fetch(`http://${window.location.hostname}:8000/api/models/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: newApiKey })
      });
      setNewApiKey('');
      fetchModels();
    } catch (e) {
        alert("无法连接到后端，请确认 server.py 正在运行。");
    }
  };

  const handleRemoveKey = async (provider) => {
    try {
      await fetch(`http://${window.location.hostname}:8000/api/models/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider })
      });
      if (activeProvider === provider) {
        setActiveProvider('');
      }
      fetchModels();
    } catch (e) {
        alert("无法连接到后端，请确认 server.py 正在运行。");
    }
  };

  const handleUpdateAlias = async (provider, alias) => {
    try {
      await fetch(`http://${window.location.hostname}:8000/api/models/alias`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, alias })
      });
      fetchModels();
    } catch (e) {
        alert("无法连接到后端，请确认 server.py 正在运行。");
    }
  };

  const [editingAliasProvider, setEditingAliasProvider] = useState(null);
  const [editingAliasValue, setEditingAliasValue] = useState("");

  const handleStreamResponse = async (res) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        const data = JSON.parse(line);

        if (data.type === 'log') {
          setActionLogs(prev => [...prev, data.log]);
        } else if (data.type === 'workflow') {
          setActiveWorkflow(prev => {
            const existingIdx = prev.findIndex(n => n.node === data.node);
            if (existingIdx !== -1) {
              const next = [...prev];
              next[existingIdx].state = data.state;
              return next;
            }
            return [...prev, { node: data.node, state: data.state }];
          });
        } else if (data.status === 'done') {
          setMessages(prev => {
            const newMsg = { role: 'agent', content: data.plan_content || data.response, type: data.type, routed_by: data.routed_by };
            if (activeWorkflow.length > 0 && data.routed_by === 'Cloud API') {
              newMsg.workflow = [...activeWorkflow];
            }
            return [...prev, newMsg];
          });
          if (data.type === 'plan') {
            // Display plan in sidebar and save content
            setCurrentPlanContent(data.plan_content || data.response);
            setIsPlanPanelOpen(true);
          }
        }
      }
    }
  };

  const sendMessage = async (customMsg = null, isEscalation = false) => {
    const isEvent = customMsg && typeof customMsg === 'object' && customMsg.nativeEvent;
    const textToSend = (!isEvent && typeof customMsg === 'string') ? customMsg : input;
    if (!textToSend || !textToSend.trim() || isLoading) {
      return;
    }

    if (!customMsg) {
      setMessages(prev => [...prev, { role: 'user', content: textToSend }]);
      setInput('');
    } else {
      setMessages(prev => [...prev, { role: 'user', content: '🚀 [用户操作] 启动深度工作流下钻分析...' }]);
    }

    setIsLoading(true);
    setActionLogs([]);
    setActiveWorkflow([]);

    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend, provider: activeProvider, is_approved: false, session_id: sessionId, is_escalation: isEscalation, location: userLocation, enabled_skills: enabledSkills, workflow_mode: workflowMode })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "鍚庣璇锋眰澶辫触");
      }
      await handleStreamResponse(res);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'agent', content: `閿欒: ${e.message}` }]);
    } finally {
      setIsLoading(false);
      setActionLogs([]);
      // setActiveWorkflow([]); // Don't clear it, so it remains visible
      if (messages.length === 1) fetchSessions();
    }
  };

  const approvePlan = async () => {
    setIsLoading(true);
    setActionLogs([]);
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "", provider: activeProvider, is_approved: true, session_id: sessionId, workflow_mode: workflowMode })
      });
      setIsPlanPanelOpen(false);
      await handleStreamResponse(res);
    } catch (e) {
      alert("Error approving plan");
    } finally {
      setIsLoading(false);
      setActionLogs([]);
    }
  };

  const handleEscalate = () => {
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMsg) {
      // the actual text might be "🚀 [用户操作] 鍚姩..." if clicked twice, but let's just send the actual content
      let text = lastUserMsg.content;
        if (text.includes('启动深度工作流下钻')) {
        // find the one before it
          const allUserMsgs = messages.filter(m => m.role === 'user' && !m.content.includes('启动深度工作流下钻'));
        text = allUserMsgs.length > 0 ? allUserMsgs[allUserMsgs.length - 1].content : '';
      }
      if (text) {
        sendMessage(text, true);
      }
    }
  };

  // Antigravity Code Block Renderer
  const MarkdownRenderer = ({ content, type }) => {
    if (type === 'plan') {
      return (
        <div className="plan-block">
          <p style={{ color: 'var(--sys-color-primary)', fontWeight: '500' }}>🚀 架构计划已生成，请在右侧文档面板审查。</p>
        </div>
      );
    }

    // Parse ECharts and Mermaid
    let renderedContent = content || "";
    let echartsOptions = null;
    let mermaidChart = null;

    const echartsMatch = /<ECHARTS_DATA>([\s\S]*?)<\/ECHARTS_DATA>/.exec(renderedContent);
    if (echartsMatch) {
      try {
        const payload = JSON.parse(echartsMatch[1]);

        let seriesData = [];
        if (payload.type === 'pie') {
          seriesData = payload.dataset.map((val, idx) => ({ value: val, name: payload.labels[idx] }));
        } else {
          seriesData = payload.dataset;
        }

        echartsOptions = {
          title: { text: payload.title, textStyle: { color: '#e0e0e0' } },
          tooltip: {},
          backgroundColor: 'transparent',
          textStyle: { color: '#e0e0e0' },
          xAxis: payload.type !== 'pie' ? { data: payload.labels, axisLabel: { color: '#e0e0e0' } } : undefined,
          yAxis: payload.type !== 'pie' ? { axisLabel: { color: '#e0e0e0' } } : undefined,
          series: [{
            type: payload.type,
            data: seriesData,
            itemStyle: payload.type === 'pie' ? { borderRadius: 5 } : undefined
          }]
        };
        renderedContent = renderedContent.replace(echartsMatch[0], '');
      } catch (e) {
        console.error("Failed to parse ECharts data", e);
      }
    }

    const mermaidMatch = /<MERMAID_MINDMAP>([\s\S]*?)<\/MERMAID_MINDMAP>/.exec(renderedContent);
    if (mermaidMatch) {
      mermaidChart = mermaidMatch[1];
      renderedContent = renderedContent.replace(mermaidMatch[0], '');
    }

    return (
      <div className="markdown-body notranslate" translate="no">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '')
              return !inline && match ? (
                <div style={{ borderRadius: '8px', overflow: 'hidden' }}>
                  <div className="code-header">
                    <div className="mac-dots">
                      <div className="red"></div>
                      <div className="yellow"></div>
                      <div className="green"></div>
                    </div>
                    {match[1]}
                  </div>
                  <SyntaxHighlighter
                    {...props}
                    children={String(children).replace(/\n$/, '')}
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{ margin: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
                    showLineNumbers={true}
                  />
                </div>
              ) : (
                <code {...props} className={className} style={{ backgroundColor: 'rgba(128,128,128,0.2)', padding: '2px 4px', borderRadius: '4px' }}>
                  {children}
                </code>
              )
            }
          }}
        >
          {renderedContent}
        </ReactMarkdown>

        {echartsOptions && (
          <div style={{ marginTop: '16px', padding: '16px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
            <ReactECharts option={echartsOptions} theme="dark" style={{ height: '350px' }} />
          </div>
        )}

        {mermaidChart && (
          <MermaidChart chart={mermaidChart} />
        )}
      </div>
    );
  };

  if (!enteredSystem) {
    return (
      <div className="app-container" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div className="card glass animate-fade-in" style={{ width: '100%', maxWidth: '480px', textAlign: 'center', padding: '40px' }}>
          <Sparkles size={48} color="var(--sys-color-primary)" style={{ marginBottom: '24px' }} />
          <h1 style={{ marginBottom: '8px' }}>天韬（SkyT）</h1>
          <p style={{ marginBottom: '32px', color: 'var(--sys-color-on-surface-variant)' }}>高度自治的多智能体指挥控制台。</p>

          <button className="btn-primary" onClick={() => setEnteredSystem(true)} style={{ width: '100%', padding: '12px' }}>进入系统</button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container notranslate" translate="no" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar / Dashboard */}
        <div className={`sidebar glass ${isSidebarOpen ? '' : 'collapsed'}`} style={{ transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)', width: isSidebarOpen ? '280px' : '64px', padding: isSidebarOpen ? '24px' : '24px 8px', overflow: 'hidden', opacity: 1, position: 'relative', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: isSidebarOpen ? 'space-between' : 'center', whiteSpace: 'nowrap', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: 'var(--sys-color-primary-container)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Sparkles size={20} color="var(--sys-color-on-primary-container)" />
              </div>
              <div style={{ display: isSidebarOpen ? 'block' : 'none', opacity: isSidebarOpen ? 1 : 0, transition: 'opacity 0.2s' }}>
                <h2 style={{ fontSize: '1.25rem', margin: 0 }}>天韬（SkyT）</h2>
                <p style={{ margin: 0, fontSize: '0.85rem' }}><span className={`badge badge-${activeProvider || 'unknown'}`}>{activeProvider || '未配置模型'}</span></p>
              </div>
            </div>
            {isSidebarOpen && (
              <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sys-color-on-surface)' }} onClick={() => setShowModelManager(true)}>
                <Settings size={20} />
              </button>
            )}
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--sys-color-surface-variant)', margin: '24px 0', flexShrink: 0 }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1, overflowY: 'auto', overflowX: 'hidden', paddingRight: isSidebarOpen ? '8px' : '0', width: '100%', paddingBottom: '24px' }}>
            
            {/* Navigations */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <NavLink to="/" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', border: 'none' }} title="智能对话">
                <Bot size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>智能对话 (Chat)</span>
              </NavLink>
              <NavLink to="/dashboard" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', border: 'none' }} title="数据看板">
                <Activity size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>数据看板 (Dashboard)</span>
              </NavLink>
              <NavLink to="/history" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', border: 'none' }} title="杩愯璁板綍">
                <History size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>杩愯璁板綍 (History)</span>
              </NavLink>
              <NavLink to="/workflows" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', border: 'none' }} title="工作流库">
                <Blocks size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>工作流库 (Workflows)</span>
              </NavLink>
              <NavLink to="/reports" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', border: 'none' }} title="鎶ュ憡涓績">
                <FileText size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>鎶ュ憡涓績 (Reports)</span>
              </NavLink>
              <NavLink to="/skills" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: isSidebarOpen ? 'flex-start' : 'center', gap: '12px', padding: '12px', marginTop: '8px', border: 'none' }} title="技能大厅">
                <span style={{ fontSize: '18px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px' }}>🧰</span>
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>技能大厅 (Skills)</span>
              </NavLink>
            </div>

            {/* Todo List */}
            <div>
              <h3 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px', color: 'var(--sys-color-on-surface-variant)', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: isSidebarOpen ? 'flex-start' : 'center', whiteSpace: 'nowrap', overflow: 'hidden' }} title="任务清单">
                <LayoutTemplate size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>任务清单 (Todo)</span>
              </h3>
              <div style={{ maxHeight: isSidebarOpen ? '1000px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>
                <div className="card" style={{ padding: '16px', fontSize: '0.9rem' }}>
                  {todos.length === 0 ? (
                    <p style={{ margin: 0 }}>当前暂无任务规划。</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {todos.map((todo, idx) => (
                        <label key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                          <input type="checkbox" style={{ marginTop: '4px' }} disabled />
                          <span style={{ color: 'var(--sys-color-on-surface)' }}>{todo}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>



            {/* History */}
            <div>
              <h3 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px', color: 'var(--sys-color-on-surface-variant)', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: isSidebarOpen ? 'flex-start' : 'center', whiteSpace: 'nowrap', overflow: 'hidden' }} title="会话历史">
                <History size={20} style={{ flexShrink: 0 }} /> 
                <span style={{ maxWidth: isSidebarOpen ? '200px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', whiteSpace: 'nowrap', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>会话历史 (History)</span>
              </h3>
              <div style={{ maxHeight: isSidebarOpen ? '2000px' : '0px', opacity: isSidebarOpen ? 1 : 0, overflow: 'hidden', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    className="btn-primary"
                    onClick={handleNewChat}
                    style={{ marginBottom: '8px', width: '100%', padding: '8px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'pointer' }}
                  >
                    ➕ 新开对话
                  </button>
                  {sessions.map((sess, idx) => (
                    <div
                      key={idx}
                      className="card"
                      onClick={() => { setSessionId(sess.session_id); setCurrentView('chat'); }}
                      style={{
                        padding: '12px',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                        border: sessionId === sess.session_id ? '1px solid var(--sys-color-primary)' : '1px solid transparent',
                        backgroundColor: sessionId === sess.session_id ? 'var(--sys-color-primary-container)' : 'var(--sys-color-surface)',
                        color: sessionId === sess.session_id ? 'var(--sys-color-on-primary-container)' : 'var(--sys-color-on-surface)',
                        transition: 'all 0.2s'
                      }}
                    >
                      <p style={{ margin: 0, fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sess.title}</p>
                      <p style={{ margin: 0, fontSize: '0.75rem', opacity: 0.7 }}>{new Date(sess.created_at).toLocaleString()}</p>
                    </div>
                  ))}

                  <button
                    className="btn-secondary"
                    onClick={() => setShowClearConfirm(true)}
                    style={{ marginTop: '12px', width: '100%', padding: '6px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', border: '1px solid var(--sys-color-error)', color: 'var(--sys-color-error)', background: 'transparent', cursor: 'pointer' }}
                  >
                    🗑️ 清空当前对话
                  </button>
                </div>
              </div>
            </div>

          </div>

          <div style={{ padding: '16px', display: 'flex', justifyContent: 'center' }}>
            {isSidebarOpen ? (
              <button className="btn-secondary" onClick={() => setIsSidebarOpen(false)} style={{ width: '100%', padding: '8px' }}>
                收起侧边栏 ◀
              </button>
            ) : (
              <button className="btn-secondary" onClick={() => setIsSidebarOpen(true)} style={{ padding: '8px 12px', display: 'flex', justifyContent: 'center' }} title="展开侧边栏">
                ▶              </button>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="main-content" style={{ display: 'flex', flexDirection: 'row', overflow: 'hidden' }}>

          {/* Left Column: Chat or Skills */}
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, position: 'relative' }}>

            {/* Floating reopen button */}
            {!isWorkflowPanelOpen && location.pathname === '/' && !isWorkflowEditorOpen && (
              <button
                onClick={() => setIsWorkflowPanelOpen(true)}
                className="glass"
                style={{
                  position: 'absolute',
                  top: '16px',
                  right: '16px',
                  zIndex: 100,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '20px',
                  border: '1px solid var(--sys-color-surface-variant)',
                  cursor: 'pointer',
                  backgroundColor: 'var(--sys-color-surface)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  animation: 'fadeIn 0.3s ease forwards'
                }}
              >
                <Activity size={16} color="var(--sys-color-primary)" />
                <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>展开流转状态</span>
                {activeWorkflow.some(w => w.state === 'running') && (
                  <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ffc107', marginLeft: '4px', animation: 'pulse 1.5s infinite' }} />
                )}
              </button>
            )}

            {/* Floating Editor toggle button */}
            {location.pathname === '/' && (
              <button
                onClick={() => setIsWorkflowEditorOpen(!isWorkflowEditorOpen)}
                className="glass"
                style={{
                  position: 'absolute',
                  top: '16px',
                  right: !isWorkflowPanelOpen && !isWorkflowEditorOpen ? '160px' : '16px',
                  zIndex: 100,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '20px',
                  border: '1px solid var(--sys-color-primary)',
                  cursor: 'pointer',
                  backgroundColor: isWorkflowEditorOpen ? 'var(--sys-color-primary)' : 'var(--sys-color-surface)',
                  color: isWorkflowEditorOpen ? 'var(--sys-color-on-primary)' : 'var(--sys-color-primary)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  animation: 'fadeIn 0.3s ease forwards',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
                }}
              >
                <Settings size={16} />
                <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>
                  {isWorkflowEditorOpen ? '退出编辑' : '配置当前工作流'}
                </span>
              </button>
            )}

            {/* Main content wrap for Routes */}
            <Routes>
              <Route path="/" element={
                <>
                  {(() => {
                    // Chat view only — Skills moved to /skills route
                    return (
                      <React.Fragment>

                        {backendError && (
                          <div style={{ backgroundColor: 'var(--sys-color-error)', color: 'white', padding: '12px', textAlign: 'center', fontWeight: 'bold', zIndex: 100, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px' }}>
                            <span>⚠️ 无法连接到核心系统。请确认后端服务 (server.py) 正在运行。</span>
                            <button
                              onClick={() => {
                                setBackendError(false);
                                fetchModels();
                                fetchHistory();
                              }}
                              style={{ backgroundColor: 'white', color: 'var(--sys-color-error)', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                            >
                              立即重试
                            </button>
                          </div>
                        )}
                        
                        <div style={{ flex: 1, height: '100%', overflow: 'hidden', display: isWorkflowEditorOpen ? 'block' : 'none' }}>
                          {isWorkflowEditorOpen && <WorkflowEditor sessionId={sessionId} />}
                        </div>
                        
                        <div style={{ flex: 1, minHeight: 0, display: isWorkflowEditorOpen ? 'none' : 'flex', flexDirection: 'column' }}>
                          <ErrorBoundary>
                            {messages.length === 0 ? (
                              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                                <Bot size={64} style={{ marginBottom: '16px', color: 'var(--sys-color-primary)' }} />
                                <h2>天韬（SkyT） 鏅鸿兘涓灑</h2>
                                <p>请在下方输入指令。您可以通过侧边栏管理任务流、监控节点或配置云端模型。</p>
                              </div>
                            ) : (
                              <>
                                <div className="chat-container notranslate" translate="no" ref={chatContainerRef}>
                                  {messages.map((msg, idx) => (
                                    <div key={idx} className={`message ${msg.role} animate-fade-in`} style={{ maxWidth: msg.role === 'agent' ? '90%' : '80%' }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '0.8rem', opacity: 0.7 }}>
                                        {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                                        {msg.role === 'user' ? '用户' : '天韬（SkyT） 系统'}
                                        {msg.role === 'agent' && msg.routed_by && (
                                          <span style={{
                                            backgroundColor: msg.routed_by === 'NPU' ? '#1a73e8' : (msg.routed_by?.includes('GPU') ? '#0f9d58' : '#673ab7'),
                                            color: 'white',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            fontSize: '0.7rem',
                                            fontWeight: 'bold',
                                            marginLeft: 'auto'
                                          }}>
                                            {msg.routed_by === 'NPU' ? 'NPU' : (msg.routed_by?.includes('GPU') ? 'GPU' : 'AI')}
                                          </span>
                                        )}
                                      </div>

                                      {/* Scheme A: Inline Workflow Stepper */}
                                      {msg.workflow && msg.workflow.length > 0 && (
                                        <ErrorBoundary>
                                          <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--sys-color-primary)', fontWeight: 'bold', marginBottom: '8px', textTransform: 'uppercase' }}>Agent 鎬濊€冩祦杞妭鐐癸細</div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                                              {msg.workflow.map((node, i) => (
                                                <React.Fragment key={i}>
                                                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', color: node.state === 'done' ? 'var(--sys-color-primary)' : 'var(--sys-color-on-surface)' }}>
                                                    {node.state === 'done' ? <span key="done">✅</span> : <span key="prog">🔄</span>} <span>{node.node}</span>
                                                  </div>
                                                  {i < msg.workflow.length - 1 && <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>→</span>}
                                                </React.Fragment>
                                              ))}
                                            </div>
                                          </div>
                                        </ErrorBoundary>
                                      )}

                                      <ErrorBoundary>
                                        <MarkdownRenderer content={msg.content} type={msg.type} />
                                      </ErrorBoundary>

                                      {/* Escalation Button for GPU buffers */}
                                      {msg.role === 'agent' && msg.routed_by === 'GPU' && !msg.content.includes("非常抱歉") && !msg.content.includes("对不起") && !msg.content.includes("拒绝") && (
                                        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-start' }}>
                                          <button className="btn-primary" onClick={handleEscalate} style={{ fontSize: '0.85rem', padding: '6px 16px', display: 'flex', gap: '6px', alignItems: 'center', backgroundColor: '#673ab7', borderColor: '#673ab7' }}>
                                            <Sparkles size={14} /> 🚀 启动深度工作流下钻 (云端 API)
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                  {isLoading && (
                                    <div className="message agent animate-fade-in" style={{ maxWidth: '90%' }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '0.8rem', opacity: 0.7 }}>
                                        <Bot size={14} /> 天韬（SkyT） 系统
                                      </div>

                                      {actionLogs.length > 0 ? (
                                        <div style={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid #00ff9d', boxShadow: '0 0 10px rgba(0,255,157,0.2)', padding: '16px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                                          <div style={{ color: '#00ff9d', fontWeight: 'bold', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(0,255,157,0.3)', paddingBottom: '8px' }}>
                                            <Activity size={14} className="animate-pulse" /> &lt; 深度运算与工具调用协议激活 /&gt;
                                          </div>
                                          {actionLogs.map((log, i) => (
                                            <div key={i} className="animate-fade-in" style={{ color: log.includes('error') ? '#ff5252' : '#d4d4d4', textShadow: '0 0 2px rgba(255,255,255,0.3)' }}>
                                              <span style={{ color: '#00ff9d', marginRight: '8px' }}>[SYSTEM]</span>{log}
                                            </div>
                                          ))}
                                          <div style={{ display: 'inline-flex', padding: 0, marginTop: '12px', alignItems: 'center', gap: '8px' }}>
                                            <span style={{ color: '#00ff9d' }}>_ </span>
                                            <span className="typing-indicator" style={{ padding: 0 }}>
                                              <span style={{ backgroundColor: '#00ff9d' }}></span><span style={{ backgroundColor: '#00ff9d' }}></span><span style={{ backgroundColor: '#00ff9d' }}></span>
                                            </span>
                                          </div>
                                        </div>
                                      ) : (
                                        <div style={{ padding: '12px', color: '#00ff9d', fontFamily: 'monospace', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px', opacity: 0.8 }}>
                                          <Activity size={14} className="animate-pulse" /> 连接神经元网络...
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  {/* Messages scroller anchor */}
                                </div>

                                <div style={{ padding: '24px', backgroundColor: 'var(--sys-color-surface)', borderTop: '1px solid var(--sys-color-surface-variant)' }}>
                                  <div style={{ display: 'flex', gap: '16px', maxWidth: '1200px', margin: '0 auto', alignItems: 'center' }}>

                                    <CustomSelect
                                      value={activeProvider}
                                      onChange={setActiveProvider}
                                      title="切换当值模型"
                                      options={
                                        models?.length === 0 
                                          ? [{ value: "", label: "未配置模型" }]
                                          : models?.map(m => ({ value: m.provider, label: `${m.provider.toUpperCase()} (${m.model})` })) || []
                                      }
                                    />

                                    <CustomSelect
                                      value={workflowMode}
                                      onChange={setWorkflowMode}
                                      title="切换思维深度模式"
                                      options={[
                                        { value: 'standard', label: '⚡ 标准极速流' },
                                        { value: 'deep_thought', label: '馃 鏍囧噯娣辨€濇祦' },
                                        { value: 'expert_review', label: '🧐 专家审查流' },
                                        { value: 'creative_brainstorm', label: '💡 发散风暴流' }
                                      ]}
                                    />

                                    <input
                                      type="text"
                                      className="input-elegant"
                                      style={{ flex: 1, minWidth: 0 }}
                                      placeholder="请输入您的指令（简单的交由本地，复杂的交由云端）..."
                                      value={input}
                                      onChange={e => setInput(e.target.value)}
                                      onKeyDown={e => e.key === 'Enter' && sendMessage()}
                                      disabled={isLoading}
                                    />
                                    <ErrorBoundary>
                                      <button className="btn-primary" onClick={(e) => sendMessage(null, false)} disabled={isLoading}>
                                        {isLoading ? <span key="loading">发送中</span> : <span key="idle">发送</span>}
                                      </button>
                                    </ErrorBoundary>
                                  </div>
                                </div>
                              </>
                            )}
                          </ErrorBoundary>
                        </div>
                      </React.Fragment>
                      );
                    })()}
                  </>
                } />
              <Route path="/skills" element={
                <SkillsStore
                  skills={skills}
                  enabledSkills={enabledSkills}
                  setEnabledSkills={setEnabledSkills}
                  onImportSkill={() => { fetchSkills(); }}
                />
              } />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/workflows/editor" element={<WorkflowEditorPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/history" element={<RunHistory />} />
              <Route path="/replay/:runId" element={<WorkflowReplay />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          </div>

          {/* Dynamic Workflow Visualization Side Panel */}
          <div className="glass" style={{
            width: isWorkflowPanelOpen ? '400px' : '0px',
            opacity: isWorkflowPanelOpen ? 1 : 0,
            flexShrink: 0,
            transform: isWorkflowPanelOpen ? 'scale(1)' : 'scale(0.8)',
            transformOrigin: 'top right',
            transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            borderLeft: isWorkflowPanelOpen ? '1px solid var(--sys-color-surface-variant)' : 'none',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--sys-color-surface)',
            overflow: 'hidden',
            pointerEvents: isWorkflowPanelOpen ? 'auto' : 'none'
          }}>
            <div style={{ width: '400px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--sys-color-surface-variant)', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} color="var(--sys-color-primary)" />
                执行流 (Execution)
                <button
                  onClick={() => setIsWorkflowPanelOpen(false)}
                  style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sys-color-on-surface)', opacity: 0.7 }}
                  title="收起工作流"
                >
                  <X size={18} />
                </button>
                {activeWorkflow.some(w => w.state === 'running') && (
                  <span style={{ marginLeft: '8px', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', color: '#ffc107' }}>
                    <span className="typing-indicator" style={{ display: 'inline-flex', padding: 0 }}>
                      <span style={{ backgroundColor: '#ffc107', width: 6, height: 6 }}></span>
                      <span style={{ backgroundColor: '#ffc107', width: 6, height: 6 }}></span>
                      <span style={{ backgroundColor: '#ffc107', width: 6, height: 6 }}></span>
                    </span>
                    执行中...
                  </span>
                )}
              </div>

              <div style={{ flex: 1, position: 'relative' }}>
                <WorkflowVisualizer activeWorkflow={activeWorkflow} />
              </div>
            </div>
          </div>

          {/* Dynamic Plan Panel Side Panel */}
          <div className="glass" style={{
            width: isPlanPanelOpen ? '450px' : '0px',
            opacity: isPlanPanelOpen ? 1 : 0,
            flexShrink: 0,
            transform: isPlanPanelOpen ? 'scale(1)' : 'scale(0.8)',
            transformOrigin: 'top right',
            transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            borderLeft: isPlanPanelOpen ? '1px solid var(--sys-color-surface-variant)' : 'none',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'var(--sys-color-surface)',
            overflow: 'hidden',
            pointerEvents: isPlanPanelOpen ? 'auto' : 'none'
          }}>
            <div style={{ width: '450px', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '16px', borderBottom: '1px solid var(--sys-color-surface-variant)', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'var(--sys-color-surface-variant)' }}>
                <LayoutTemplate size={18} color="var(--sys-color-primary)" />
                实施计划审查 (Plan Review)
                <button
                  onClick={() => setIsPlanPanelOpen(false)}
                  style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sys-color-on-surface)', opacity: 0.7 }}
                  title="关闭计划面板"
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '24px' }}>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{currentPlanContent}</ReactMarkdown>
                </div>
              </div>

              <div style={{ padding: '16px', borderTop: '1px solid var(--sys-color-surface-variant)', backgroundColor: 'var(--sys-color-surface)', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button className="btn-primary" style={{ backgroundColor: 'var(--sys-color-surface-variant)', color: 'var(--sys-color-on-surface)' }} onClick={() => setIsPlanPanelOpen(false)}>稍后决定</button>
                  <button className="btn-primary" onClick={approvePlan}>✅ 批准执行 (Approve)</button>
              </div>
            </div>
          </div>
        </div>

        {/* Custom Skill Import Modal */}
        {isImportModalOpen && (
          <div className="modal-overlay">
            <div className="modal-content animate-fade-in" style={{ maxWidth: '800px', width: '90%' }}>
              <button className="modal-close" onClick={() => setIsImportModalOpen(false)}><X size={24} /></button>
              <h2 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={24} color="var(--sys-color-primary)" /> 导入自定义技能              </h2>
              <p style={{ fontSize: '0.9rem', color: 'var(--sys-color-on-surface-variant)', marginBottom: '24px' }}>
                  在此粘贴您自己编写的 Python 工具脚本。必须包含执行函数和符合 OpenAI Tool Call 规范的 schema 字典。系统将动态编译并注入，无需重启。              </p>

              {importError && (
                <div style={{ padding: '12px', backgroundColor: 'rgba(255,0,0,0.1)', color: 'var(--sys-color-error)', borderRadius: '8px', marginBottom: '16px', fontSize: '0.9rem' }}>
                  {importError}
                </div>
              )}

              <textarea
                className="input-elegant"
                style={{ width: '100%', height: '350px', fontFamily: 'monospace', fontSize: '0.9rem', padding: '16px', backgroundColor: '#1e1e1e', color: '#d4d4d4', resize: 'vertical' }}
                value={importCode}
                onChange={e => setImportCode(e.target.value)}
                spellCheck={false}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                <button
                  className="btn-primary"
                  style={{ backgroundColor: 'var(--sys-color-surface-variant)', color: 'var(--sys-color-on-surface)' }}
                  onClick={() => setIsImportModalOpen(false)}
                >
                  取消
                </button>
                <button
                  className="btn-primary"
                  onClick={handleImportSkill}
                >
                  🚀 编译并加载                </button>
              </div>
            </div>
          </div>
        )}

        {/* Model Manager Modal (Card-based UI) */}
        {showModelManager && (
          <div className="modal-overlay">
            <div className="modal-content animate-fade-in" style={{ maxWidth: '800px', width: '90%' }}>
              <button className="modal-close" onClick={() => setShowModelManager(false)}><X size={24} /></button>
              <h2 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Settings size={24} /> 模型与 API Key 管理
              </h2>

              <div style={{ marginBottom: '32px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--sys-color-primary)' }}>宸查厤缃殑妯″瀷</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {models?.length === 0 ? <span style={{ fontSize: '0.9rem', color: 'gray', gridColumn: '1 / -1' }}>暂无模型，请在下方添加</span> : null}
                  {models?.map((m, i) => (
                    <div key={i} style={{
                      padding: '16px',
                      border: '1px solid var(--sys-color-surface-variant)',
                      borderRadius: 'var(--sys-radius-md)',
                      backgroundColor: 'var(--sys-color-surface)',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          {editingAliasProvider === m.provider ? (
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <input
                                autoFocus
                                className="input-elegant"
                                style={{ padding: '4px 8px', fontSize: '0.9rem' }}
                                value={editingAliasValue}
                                onChange={(e) => setEditingAliasValue(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    handleUpdateAlias(m.provider, editingAliasValue);
                                    setEditingAliasProvider(null);
                                  } else if (e.key === 'Escape') {
                                    setEditingAliasProvider(null);
                                  }
                                }}
                              />
                              <button className="btn-primary" style={{ padding: '4px 8px', fontSize: '0.8rem' }} onClick={() => {
                                handleUpdateAlias(m.provider, editingAliasValue);
                                setEditingAliasProvider(null);
                              }}>保存</button>
                            </div>
                          ) : (
                            <h4 style={{ margin: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                              onClick={() => {
                                setEditingAliasProvider(m.provider);
                                setEditingAliasValue(m.alias || "");
                              }}
                        title="点击重命名别名"
                            >
                          {m.alias || "未命名模型"}
                              <span style={{ fontSize: '0.75rem', color: 'var(--sys-color-primary)', fontWeight: 'normal' }}>✏️</span>
                            </h4>
                          )}
                          <div style={{ fontSize: '0.85rem', color: 'var(--sys-color-on-surface-variant)', marginTop: '4px' }}>
                            原生型号: {m.model}
                          </div>
                        </div>
                        <span className={`badge badge-${m.provider}`}>{m.provider.toUpperCase()}</span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'auto', paddingTop: '8px', borderTop: '1px dashed var(--sys-color-surface-variant)' }}>
                        <button onClick={() => handleRemoveKey(m.provider)} style={{ background: 'none', border: 'none', color: 'var(--sys-color-error)', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '500' }}>
                          移除配置
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ padding: '20px', backgroundColor: 'var(--sys-color-surface-variant)', borderRadius: 'var(--sys-radius-md)' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}><Sparkles size={18} /> 鏋侀€熸坊鍔犳柊妯″瀷</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--sys-color-on-surface-variant)', marginBottom: '16px' }}>
                  系统将根据 API Key 的格式自动识别所属平台 (支持 OpenAI, Gemini, DeepSeek, Zhipu 等)。                </p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <input
                    type="password"
                    className="input-elegant"
                    style={{ flex: 1 }}
                    placeholder="鍦ㄦ绮樿创鎮ㄧ殑 API Key..."
                    value={newApiKey}
                    onChange={e => setNewApiKey(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddKey();
                    }}
                  />
                  <button className="btn-primary" onClick={handleAddKey}>立刻添加</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Custom Clear Confirmation Modal */}
      {showClearConfirm && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: 'var(--sys-color-surface)',
            borderRadius: '16px',
            padding: '24px 32px',
            width: '400px',
            maxWidth: '90%',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            border: '1px solid var(--sys-color-surface-variant)'
          }}>
            <h3 style={{ margin: 0, color: 'var(--sys-color-on-surface)', fontSize: '1.25rem' }}>清空当前对话</h3>
            <p style={{ margin: 0, color: 'var(--sys-color-on-surface-variant)', fontSize: '0.95rem' }}>
              确定要清空当前会话的历史记录吗？此操作无法撤销。</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <button 
                className="btn-secondary" 
                onClick={() => setShowClearConfirm(false)}
                style={{ padding: '8px 16px' }}
              >
                取消
              </button>
              <button 
                className="btn-primary" 
                onClick={() => {
                  setShowClearConfirm(false);
                  clearHistory();
                }}
                style={{ padding: '8px 16px', backgroundColor: 'var(--sys-color-error)', color: '#fff', border: 'none' }}
              >
                纭娓呯┖
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
