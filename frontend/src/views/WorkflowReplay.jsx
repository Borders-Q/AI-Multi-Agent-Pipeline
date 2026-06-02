import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Play, Pause, FastForward, RotateCcw, Cpu, Zap, Activity, Clock, Terminal, Search, Filter, ShieldAlert, Code, Copy, ChevronDown, ChevronRight } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import WorkflowVisualizer from '../components/WorkflowVisualizer';

const API_BASE = `http://${window.location.hostname}:8000`;

const INPUT_PAYLOAD_KEYS = new Set([
  'args',
  'arguments',
  'input',
  'inputs',
  'inputdata',
  'request',
  'requirement',
  'prompt',
  'messages',
  'command',
  'cwd',
  'path',
  'filepath',
  'content',
  'query',
  'params',
  'parameters',
  'body',
]);

const OUTPUT_PAYLOAD_KEYS = new Set([
  'result',
  'response',
  'reply',
  'output',
  'outputs',
  'stdout',
  'stderr',
  'error',
  'summary',
  'preview',
  'codepreview',
  'code',
  'qualityscore',
  'report',
  'messageout',
]);

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function normalizePayloadKey(key) {
  return String(key || '').toLowerCase().replace(/[_\-\s]/g, '');
}

function stringifyPayload(value) {
  if (value === undefined || value === null) return '';
  if (typeof value === 'string') return value.replace(/\\n/g, '\n');
  try {
    return JSON.stringify(value, null, 2).replace(/\\n/g, '\n');
  } catch {
    return String(value);
  }
}

function safeParsePayload(raw) {
  if (raw === undefined || raw === null || raw === '') {
    return { kind: 'empty', value: null, formatted: '', error: null };
  }

  if (typeof raw !== 'string') {
    return { kind: 'json', value: raw, formatted: stringifyPayload(raw), error: null };
  }

  const trimmed = raw.trim();
  if (!trimmed) {
    return { kind: 'empty', value: null, formatted: '', error: null };
  }

  try {
    let parsed = JSON.parse(trimmed);
    if (typeof parsed === 'string' && /^[\[{]/.test(parsed.trim())) {
      try {
        parsed = JSON.parse(parsed);
      } catch {
        // Keep the first parsed string if it is not valid nested JSON.
      }
    }
    return { kind: 'json', value: parsed, formatted: stringifyPayload(parsed), error: null };
  } catch (error) {
    return {
      kind: 'text',
      value: trimmed.replace(/\\n/g, '\n'),
      formatted: trimmed.replace(/\\n/g, '\n'),
      error: error.message,
    };
  }
}

function collectPayloadEntries(source, input, output, meta) {
  Object.entries(source || {}).forEach(([key, value]) => {
    const normalized = normalizePayloadKey(key);
    if (INPUT_PAYLOAD_KEYS.has(normalized)) {
      input[key] = value;
      return;
    }
    if (OUTPUT_PAYLOAD_KEYS.has(normalized)) {
      output[key] = value;
      return;
    }
    if (normalized === 'detail' && isRecord(value)) {
      const nestedMeta = {};
      collectPayloadEntries(value, input, output, nestedMeta);
      if (Object.keys(nestedMeta).length > 0) meta[key] = nestedMeta;
      return;
    }
    meta[key] = value;
  });
}

function splitPayload(parsedPayload, event) {
  const input = {};
  const output = {};
  const meta = {
    event_type: event?.event_type || '',
    agent: event?.agent || '',
    status: event?.status || '',
    duration_ms: event?.duration_ms ?? '',
  };

  if (parsedPayload.kind === 'json') {
    if (isRecord(parsedPayload.value)) {
      collectPayloadEntries(parsedPayload.value, input, output, meta);
    } else {
      meta.raw_payload = parsedPayload.value;
    }
  } else if (parsedPayload.kind === 'text') {
    meta.raw_payload = parsedPayload.value;
    meta.parse_error = parsedPayload.error;
  } else {
    meta.note = '该事件没有记录 detail_json。';
  }

  return { input, output, meta };
}

function isEmptyPayload(value) {
  if (value === undefined || value === null) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (isRecord(value)) return Object.keys(value).length === 0;
  return false;
}

function payloadSummary(value) {
  if (isEmptyPayload(value)) return '0 fields';
  if (Array.isArray(value)) return `${value.length} items`;
  if (isRecord(value)) return `${Object.keys(value).length} fields`;
  return `${stringifyPayload(value).length} chars`;
}

function PayloadSection({ title, description, value, emptyText, tone = 'neutral', defaultCollapsed = false, language = 'json' }) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [copied, setCopied] = useState(false);
  const empty = isEmptyPayload(value);
  const content = stringifyPayload(value);

  const copyPayload = async () => {
    if (empty) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className={`payload-section ${tone} ${collapsed ? 'collapsed' : ''}`}>
      <div className="payload-section-head">
        <button className="payload-toggle" type="button" onClick={() => setCollapsed(!collapsed)} aria-expanded={!collapsed}>
          {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
          <span>{title}</span>
        </button>
        <div className="payload-section-actions">
          <em>{payloadSummary(value)}</em>
          <button className="payload-copy-button" type="button" onClick={copyPayload} disabled={empty}>
            <Copy size={13} />
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </div>
      {description && <p className="payload-section-desc">{description}</p>}
      {!collapsed && (
        empty ? (
          <div className="payload-empty">{emptyText}</div>
        ) : (
          <div className="payload-code-shell">
            <SyntaxHighlighter
              language={language}
              style={vscDarkPlus}
              customStyle={{ margin: 0, padding: '14px', background: 'transparent', fontSize: '0.78rem' }}
              showLineNumbers={content.split('\n').length > 2}
              wrapLongLines={true}
            >
              {content}
            </SyntaxHighlighter>
          </div>
        )
      )}
    </section>
  );
}

function PayloadViewer({ event }) {
  const parsedPayload = safeParsePayload(event?.detail_json);
  const sections = splitPayload(parsedPayload, event);
  const rawTitle = parsedPayload.kind === 'text' ? '原始文本 / 异常数据' : '原始 / 元信息';

  return (
    <div className="io-payload-viewer">
      <div className="payload-viewer-topline">
        <span className={`payload-state ${parsedPayload.kind}`}>
          {parsedPayload.kind === 'json' ? 'JSON 已格式化' : parsedPayload.kind === 'text' ? '非标准 JSON' : '无 detail_json'}
        </span>
        {parsedPayload.error && <em>解析失败：{parsedPayload.error}</em>}
      </div>
      <PayloadSection
        title="输入 Payload"
        description="模型、工具或事件执行前使用的参数、需求、命令和上下文。"
        value={sections.input}
        emptyText="该事件没有可识别的输入字段。"
        tone="input"
      />
      <PayloadSection
        title="输出 Payload"
        description="模型、工具或事件执行后的结果、响应、stdout/stderr、摘要和错误。"
        value={sections.output}
        emptyText="该事件没有可识别的输出字段。"
        tone="output"
      />
      <PayloadSection
        title={rawTitle}
        description="未归类字段和事件元信息会保留在这里，避免展示优化时丢失原始数据。"
        value={sections.meta}
        emptyText="没有额外元信息。"
        tone="raw"
        defaultCollapsed={parsedPayload.kind === 'json'}
        language={parsedPayload.kind === 'text' ? 'text' : 'json'}
      />
    </div>
  );
}

function extractTokenUsage(event) {
  const parsedPayload = safeParsePayload(event?.detail_json);
  if (parsedPayload.kind === 'json' && isRecord(parsedPayload.value)) {
    const usage = parsedPayload.value.token_usage || parsedPayload.value.detail?.token_usage;
    if (usage) return usage;
  }
  return null;
}

function TokenUsagePanel({ event }) {
  const usage = extractTokenUsage(event);
  if (!usage?.total_tokens) return null;
  const source = usage.source || ((usage.estimated_tokens || 0) > 0 ? 'estimated' : (usage.real_tokens || 0) > 0 ? 'real' : 'estimated');
  const sourceLabel = source === 'estimated' ? '估算' : source === 'mixed' ? '真实+估算' : source === 'real' ? '真实' : '未标明';
  const rows = [
    ['API', usage.api_tokens || 0, '#89b4fa'],
    ['本地 GPU/NPU', usage.local_tokens || 0, '#a6e3a1'],
    ['总计', usage.total_tokens || 0, '#cba6f7'],
  ];
  return (
    <div className="replay-token-panel">
      <div className="replay-token-panel-head">
        <Activity size={14} />
        <strong>Token Usage</strong>
        <em>{sourceLabel}</em>
      </div>
      <div className="replay-token-grid">
        {rows.map(([label, value, color]) => (
          <div key={label}>
            <span>{label}</span>
            <strong style={{ color }}>{Number(value).toLocaleString()}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WorkflowReplay() {
  const { runId } = useParams();
  const [events, setEvents] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [selectedEvent, setSelectedEvent] = useState(null);
  
  // New features state
  const [speed, setSpeed] = useState(1);
  const [filterAgent, setFilterAgent] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/runs/${runId}/events`)
      .then(res => res.json())
      .then(data => {
        setEvents(data.events || []);
        if (data.events && data.events.length > 0) {
          setCurrentIndex(data.events.length - 1);
          setSelectedEvent(data.events[data.events.length - 1]);
        }
      })
      .catch(e => console.error("Failed to load run events", e));
  }, [runId]);

  useEffect(() => {
    let timer;
    if (playing && currentIndex < events.length - 1) {
      timer = setTimeout(() => {
        setCurrentIndex(prev => {
          const nextIdx = prev + 1;
          setSelectedEvent(events[nextIdx]);
          // Auto-scroll timeline
          if (scrollRef.current) {
            const activeEl = scrollRef.current.children[nextIdx];
            if (activeEl) {
              activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
          }
          return nextIdx;
        });
      }, 800 / speed);
    } else if (playing && currentIndex >= events.length - 1) {
      setPlaying(false);
    }
    return () => clearTimeout(timer);
  }, [playing, currentIndex, events, speed]);

  const handlePlay = () => {
    if (currentIndex >= events.length - 1) {
      setCurrentIndex(-1);
    }
    setPlaying(true);
  };

  const getEventIcon = (type, agent) => {
    if (agent === 'NPU' || type === 'LLM_THINK') return <Cpu size={16} color="#89b4fa" />;
    if (agent === 'GPU' || type === 'TOOL_CALL') return <Zap size={16} color="#f9e2af" />;
    if (agent === 'CodeAgent') return <Code size={16} color="#a6e3a1" />;
    if (type === 'BLOCK' || type === 'ERROR') return <ShieldAlert size={16} color="#f38ba8" />;
    return <Activity size={16} color="#cba6f7" />;
  };

  const filteredEvents = events.filter(ev => {
    if (filterAgent !== 'ALL' && ev.agent !== filterAgent) return false;
    if (filterStatus !== 'ALL' && ev.status !== filterStatus) return false;
    if (searchQuery && !ev.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const uniqueAgents = ['ALL', ...new Set(events.map(e => e.agent).filter(Boolean))];

  return (
    <div className="workflow-replay-page">
      
      {/* Header & Controls */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Link to="/history" style={{ color: '#cdd6f4', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ padding: '8px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)' }}><ArrowLeft size={20} /></div>
          </Link>
          <div>
            <h1 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#cdd6f4' }}>
              细粒度工作流回放
            </h1>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#89b4fa', fontFamily: 'monospace', marginTop: '4px' }}>
              TARGET_ID: {runId}
            </p>
          </div>
        </div>

        {/* Playback Controls */}
        <div style={{ display: 'flex', gap: '12px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', padding: '8px 16px', borderRadius: '24px', alignItems: 'center' }}>
          <select 
            value={speed} 
            onChange={e => setSpeed(Number(e.target.value))}
            style={{ background: 'transparent', border: 'none', color: '#a6adc8', outline: 'none', cursor: 'pointer' }}
          >
            <option value={0.5}>0.5x</option>
            <option value={1}>1.0x</option>
            <option value={2}>2.0x</option>
            <option value={4}>4.0x</option>
          </select>
          <div style={{ width: '1px', height: '16px', background: '#313244' }}></div>
          <button onClick={() => { setCurrentIndex(-1); setPlaying(false); }} style={{ background: 'none', border: 'none', color: '#a6adc8', cursor: 'pointer' }} title="重置"><RotateCcw size={18} /></button>
          <button onClick={playing ? () => setPlaying(false) : handlePlay} style={{ background: '#89b4fa', color: '#11111b', border: 'none', padding: '6px 16px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
            {playing ? <Pause size={16} /> : <Play size={16} />} {playing ? <span key="pause">暂停</span> : <span key="play">播放</span>}
          </button>
          <button onClick={() => { setCurrentIndex(events.length - 1); setPlaying(false); setSelectedEvent(events[events.length - 1]); }} style={{ background: 'none', border: 'none', color: '#a6adc8', cursor: 'pointer' }} title="跳到末尾"><FastForward size={18} /></button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', padding: '6px 12px', borderRadius: '8px' }}>
          <Filter size={14} color="#a6adc8" />
          <select value={filterAgent} onChange={e => setFilterAgent(e.target.value)} style={{ background: 'transparent', border: 'none', color: '#cdd6f4', outline: 'none', fontSize: '0.85rem' }}>
            {uniqueAgents.map(a => <option key={a} value={a}>{a === 'ALL' ? '所有 Agent' : a}</option>)}
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', padding: '6px 12px', borderRadius: '8px' }}>
          <Filter size={14} color="#a6adc8" />
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ background: 'transparent', border: 'none', color: '#cdd6f4', outline: 'none', fontSize: '0.85rem' }}>
            <option value="ALL">所有状态</option>
            <option value="SUCCESS">成功 (SUCCESS)</option>
            <option value="ERROR">失败 (ERROR)</option>
          </select>
        </div>
        <div style={{ position: 'relative', flex: 1, maxWidth: '300px' }}>
          <Search size={14} color="#a6adc8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input 
            type="text" 
            placeholder="搜索事件内容..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ width: '100%', padding: '8px 12px 8px 32px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '8px', color: '#cdd6f4', outline: 'none', boxSizing: 'border-box' }}
          />
        </div>
      </div>

      {/* Visualizer Timeline */}
      <div style={{ marginBottom: '24px', height: '200px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '12px', overflow: 'hidden' }}>
        <WorkflowVisualizer activeWorkflow={
          events.slice(0, currentIndex + 1)
            .filter(e => e.agent && e.agent !== 'System')
            .map(e => ({
              node: e.agent,
              state: e.status === 'SUCCESS' ? 'completed' : e.status === 'ERROR' ? 'error' : 'running'
            }))
            .reduce((acc, current) => {
              const x = acc.find(item => item.node === current.node);
              if (!x) return acc.concat([current]);
              x.state = current.state;
              return acc;
            }, [])
        } />
      </div>

      <div className="replay-workspace-grid">
        
        {/* Timeline (Left) */}
        <div ref={scrollRef} className="replay-timeline-panel">
          {filteredEvents.length === 0 ? <p style={{ color: '#a6adc8', textAlign: 'center' }}>无匹配事件</p> : filteredEvents.map((ev, idx) => {
            const globalIdx = events.findIndex(e => e.id === ev.id);
            const isVisible = globalIdx <= currentIndex || !playing;
            const isSelected = selectedEvent?.id === ev.id;
            
            return (
              <div 
                key={idx} 
                onClick={() => setSelectedEvent(ev)}
                style={{ 
                  display: 'flex', 
                  gap: '16px', 
                  opacity: isVisible ? 1 : 0.3, 
                  cursor: 'pointer',
                  position: 'relative',
                  padding: '12px',
                  borderRadius: '8px',
                  backgroundColor: isSelected ? 'rgba(137, 180, 250, 0.1)' : 'transparent',
                  border: isSelected ? '1px solid rgba(137, 180, 250, 0.3)' : '1px solid transparent',
                  transition: 'all 0.2s',
                  marginBottom: '4px'
                }}
              >
                {/* Timeline Line */}
                {idx < filteredEvents.length - 1 && (
                  <div style={{ position: 'absolute', left: '27px', top: '40px', bottom: '-16px', width: '2px', backgroundColor: isVisible ? '#45475a' : '#313244' }}></div>
                )}
                
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '16px', 
                  backgroundColor: ev.status === 'SUCCESS' ? 'rgba(166, 227, 161, 0.1)' : 'rgba(243, 139, 168, 0.1)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  border: `2px solid ${ev.status === 'SUCCESS' ? (isSelected ? '#a6e3a1' : '#45475a') : '#f38ba8'}`,
                  zIndex: 2
                }}>
                  {getEventIcon(ev.event_type, ev.agent)}
                </div>
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#cdd6f4' }}>{ev.agent || ev.event_type}</div>
                    <span style={{ fontSize: '0.7rem', color: '#a6adc8', background: '#313244', padding: '2px 6px', borderRadius: '4px' }}>
                      {ev.event_type}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#bac2de', marginBottom: '8px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {ev.message}
                  </div>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: '#6c7086' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={12} /> {ev.duration_ms} ms</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Details Panel (Right) */}
        <div className="replay-detail-panel">
          {selectedEvent ? (
            <div className="animate-fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', borderBottom: '1px solid #313244', paddingBottom: '16px' }}>
                <div>
                  <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '12px', color: '#cdd6f4' }}>
                    {getEventIcon(selectedEvent.event_type, selectedEvent.agent)}
                    {selectedEvent.agent || selectedEvent.event_type} 
                  </h2>
                  <div style={{ fontSize: '0.85rem', color: '#a6adc8' }}>{new Date(selectedEvent.created_at).toLocaleString()}</div>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <span style={{ 
                    padding: '4px 12px', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 'bold',
                    backgroundColor: selectedEvent.status === 'SUCCESS' ? 'rgba(166, 227, 161, 0.2)' : 'rgba(243, 139, 168, 0.2)', 
                    color: selectedEvent.status === 'SUCCESS' ? '#a6e3a1' : '#f38ba8' 
                  }}>
                    {selectedEvent.status}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 12px', borderRadius: '12px', fontSize: '0.85rem', backgroundColor: '#313244', color: '#cdd6f4' }}>
                    <Clock size={14} /> {selectedEvent.duration_ms} ms
                  </span>
                </div>
              </div>
              
              <div style={{ marginBottom: '24px', background: 'rgba(24, 24, 37, 0.5)', padding: '16px', borderRadius: '8px', border: '1px solid #313244' }}>
                <h4 style={{ color: '#89b4fa', margin: '0 0 8px 0', fontSize: '0.85rem', textTransform: 'uppercase' }}>执行摘要</h4>
                <p style={{ margin: 0, fontSize: '1rem', color: '#cdd6f4', lineHeight: '1.6' }}>{selectedEvent.message}</p>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h4 style={{ color: '#89b4fa', margin: '0 0 8px 0', fontSize: '0.85rem', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={14} /> 输入/输出载荷 (I/O JSON Payload)
                </h4>
                <TokenUsagePanel event={selectedEvent} />
                <PayloadViewer event={selectedEvent} />
              </div>
            </div>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6c7086', flexDirection: 'column', gap: '16px' }}>
              <Activity size={48} style={{ opacity: 0.5 }} />
              <p>请在左侧时间线中选择或播放事件以查看详情</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
