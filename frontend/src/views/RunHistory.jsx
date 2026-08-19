import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { History, PlayCircle, CheckCircle, XCircle, Search, Clock, Activity, Target, Zap, FileText, MessageSquare, Layers } from 'lucide-react';

const API_BASE = '';

function parseJsonField(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function tokenSummary(record) {
  const breakdown = parseJsonField(record?.token_breakdown_json) || {};
  const api = Number(record?.api_tokens ?? breakdown.api_tokens ?? 0);
  const local = Number(record?.local_tokens ?? breakdown.local_tokens ?? 0);
  const total = Number(record?.total_tokens ?? breakdown.total_tokens ?? api + local);
  const real = Number(breakdown.real_tokens || 0);
  const estimated = Number(breakdown.estimated_tokens || 0);
  let source = record?.token_source || breakdown.source || 'none';
  if ((!source || source === 'none') && total) {
    source = estimated > 0 ? 'estimated' : real > 0 ? 'real' : 'estimated';
  }
  return { api, local, total, source };
}

function TokenSummary({ record, compact = false }) {
  const tokens = tokenSummary(record);
  const sourceLabel = tokens.source === 'estimated' ? '估算' : tokens.source === 'mixed' ? '真实+估算' : tokens.source === 'none' ? '无消耗' : '真实';
  if (compact) {
    return <span>API {tokens.api} / 本地 {tokens.local} / 总 {tokens.total} · {sourceLabel}</span>;
  }
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
      <Activity size={16} />
      <span>Token:</span>
      <strong style={{ color: '#89b4fa' }}>API {tokens.api.toLocaleString()}</strong>
      <strong style={{ color: '#a6e3a1' }}>本地 {tokens.local.toLocaleString()}</strong>
      <strong style={{ color: '#cba6f7' }}>总计 {tokens.total.toLocaleString()}</strong>
      <em style={{ color: '#a6adc8', fontStyle: 'normal', fontSize: '0.8rem' }}>{sourceLabel}</em>
    </span>
  );
}

export default function RunHistory() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sessions, setSessions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState(location.state?.filterStatus || 'ALL');
  const [selectedSession, setSelectedSession] = useState(null);
  const [generatingMarkdown, setGeneratingMarkdown] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/runs/sessions?limit=50`)
      .then(res => res.json())
      .then(data => {
        const list = data.sessions || [];
        setSessions(list);
        if (list.length > 0) {
          setSelectedSession(list[0]);
        }
      })
      .catch(e => console.error('Failed to load run sessions', e));
  }, []);

  const filteredSessions = useMemo(() => {
    const query = searchTerm.toLowerCase();
    return sessions.filter(session => {
      if (filterStatus !== 'ALL') {
        if (filterStatus === 'SUCCESS' && !session.success) return false;
        if (filterStatus === 'FAILED' && session.success) return false;
      }
      const haystack = [
        session.session_id,
        session.title,
        session.requirement,
        session.first_requirement,
        session.latest_run_id,
      ].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(query);
    });
  }, [sessions, filterStatus, searchTerm]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (filteredSessions.length > 0) {
        if (!selectedSession || !filteredSessions.find(item => item.session_id === selectedSession.session_id)) {
          setSelectedSession(filteredSessions[0]);
        }
      } else {
        setSelectedSession(null);
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [filteredSessions, selectedSession]);

  const formatTime = (dateStr) => {
    try {
      return new Date(dateStr).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    } catch { return dateStr; }
  };

  const waitForTask = async (taskId) => {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '任务状态读取失败');
      const task = data.task || {};
      if (['succeeded', 'failed', 'cancelled'].includes(task.status)) return task;
      await new Promise((resolve) => window.setTimeout(resolve, 750));
    }
    throw new Error('报告生成超时，请到任务状态中查看。');
  };

  const generateImportantWorkLog = async () => {
    if (!selectedSession?.session_id || generatingMarkdown) return;
    setGeneratingMarkdown(true);
    try {
      const res = await fetch(`${API_BASE}/api/runs/sessions/${encodeURIComponent(selectedSession.session_id)}/generate-markdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'important_work_log', language: 'zh-CN' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '生成失败');
      const task = data.task_id ? await waitForTask(data.task_id) : data;
      if (task.status && task.status !== 'succeeded') throw new Error(task.error_text || '报告生成失败');
      const result = task.result || task;
      alert(`已生成历史会话工作记录，报告 ID：${result.report_id || '已完成'}`);
    } catch (error) {
      alert(`生成历史会话工作记录失败：${error.message}`);
    } finally {
      setGeneratingMarkdown(false);
    }
  };

  const openReplay = () => {
    if (!selectedSession?.session_id) return;
    navigate(`/replay/session/${encodeURIComponent(selectedSession.session_id)}`);
  };

  return (
    <div style={{ padding: '32px', overflowY: 'hidden', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', margin: 0, display: 'flex', alignItems: 'center', gap: '12px', color: '#cdd6f4' }}>
            <History size={28} color="#89b4fa" />
            运行历史 (Run History)
          </h1>
          <p style={{ color: '#a6adc8', margin: '8px 0 0', fontSize: '0.9rem' }}>
            按历史会话聚合展示完整 Agent 执行记录、耗时与 Token 消耗。
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '8px', overflow: 'hidden' }}>
            {['ALL', 'SUCCESS', 'FAILED'].map(status => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                style={{
                  background: filterStatus === status ? '#313244' : 'transparent',
                  color: filterStatus === status ? '#cdd6f4' : '#6c7086',
                  border: 'none', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                <div style={{ flex: 1, textAlign: 'center', color: filterStatus === status ? '#cdd6f4' : '#a6adc8', fontSize: '1rem', fontWeight: 'bold' }}>
                  {status === 'ALL' ? '全部' : (status === 'SUCCESS' ? '成功' : '失败')}
                </div>
              </button>
            ))}
          </div>
          <div style={{ position: 'relative', width: '250px' }}>
            <Search size={16} color="#a6adc8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="搜索会话、需求或 ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%', padding: '8px 12px 8px 36px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '8px', color: '#cdd6f4', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, gap: '24px', overflow: 'hidden' }}>
        <div style={{ width: '450px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '8px' }}>
          {filteredSessions.map((session) => {
            const isSelected = selectedSession?.session_id === session.session_id;
            const failedCount = Number(session.failed_count || 0);
            return (
              <div
                key={session.session_id}
                onClick={() => setSelectedSession(session)}
                style={{
                  display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', cursor: 'pointer',
                  background: isSelected ? 'rgba(49, 50, 68, 0.88)' : 'rgba(30, 30, 46, 0.6)',
                  borderTop: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderRight: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderBottom: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderLeft: `4px solid ${failedCount > 0 ? '#f38ba8' : '#a6e3a1'}`,
                  borderRadius: '8px', transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#89b4fa', fontSize: '0.78rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {session.session_id}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#a6adc8', display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                    <Clock size={12} /> {formatTime(session.last_run_at || session.created_at)}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '1rem', color: '#cdd6f4', fontWeight: 700, display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {session.title || '未命名历史会话'}
                </p>
                <p style={{ margin: 0, fontSize: '0.86rem', color: '#a6adc8', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {session.requirement || session.first_requirement || '暂无需求摘要'}
                </p>
                <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: '#a6adc8', flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Layers size={14} /> {session.run_count || 0} 次运行</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Target size={14} /> 质量 {Number(session.quality_score || 0).toFixed(1)}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Activity size={14} /> <TokenSummary record={session} compact /></span>
                </div>
              </div>
            );
          })}
          {filteredSessions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px', color: '#6c7086' }}>
              没有找到相关的历史会话。
            </div>
          )}
        </div>

        <div style={{
          flex: 1, overflowY: 'auto', padding: '32px', display: 'flex', flexDirection: 'column',
          background: 'linear-gradient(135deg, rgba(30, 30, 46, 0.8), rgba(49, 50, 68, 0.6))',
          border: '1px solid #313244', borderRadius: '12px', backdropFilter: 'blur(10px)'
        }}>
          {selectedSession ? (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', gap: '18px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: selectedSession.success ? '#a6e3a1' : '#f38ba8', fontWeight: 'bold' }}>
                      {selectedSession.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                      {selectedSession.success ? '会话执行成功 (SUCCESS)' : '会话存在失败 (FAILED)'}
                    </div>
                    <span style={{ fontSize: '0.9rem', color: '#a6adc8', fontFamily: 'monospace' }}>{selectedSession.session_id}</span>
                  </div>
                  <h2 style={{ color: '#cdd6f4', margin: '0 0 12px', fontSize: '1.45rem' }}>
                    {selectedSession.title || '未命名历史会话'}
                  </h2>
                  <div style={{ fontSize: '0.9rem', color: '#bac2de', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Clock size={16} /> {formatTime(selectedSession.first_run_at)} - {formatTime(selectedSession.last_run_at)}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Layers size={16} /> {selectedSession.run_count || 0} 次运行</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Target size={16} /> 质量评分: <strong style={{ color: '#fab387' }}>{Number(selectedSession.quality_score || 0).toFixed(1)}/10</strong></span>
                    <TokenSummary record={selectedSession} />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <button
                    onClick={generateImportantWorkLog}
                    disabled={generatingMarkdown}
                    style={{
                      background: 'rgba(49, 50, 68, 0.85)', color: '#cdd6f4', border: '1px solid #45475a', padding: '10px 18px', borderRadius: '24px',
                      display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', cursor: generatingMarkdown ? 'wait' : 'pointer', fontSize: '0.92rem'
                    }}
                  >
                    <FileText size={18} />
                    {generatingMarkdown ? '生成中...' : '生成会话工作记录'}
                  </button>
                  <button
                    onClick={openReplay}
                    style={{
                      background: '#89b4fa', color: '#11111b', border: 'none', padding: '10px 24px', borderRadius: '24px',
                      display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '1rem',
                      boxShadow: '0 4px 12px rgba(137, 180, 250, 0.3)'
                    }}
                  >
                    <PlayCircle size={20} />
                    进入会话深度回放
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '24px' }}>
                <Metric label="成功运行" value={selectedSession.success_count || 0} tone="#a6e3a1" />
                <Metric label="失败运行" value={selectedSession.failed_count || 0} tone="#f38ba8" />
                <Metric label="累计 Token" value={Number(selectedSession.total_tokens || 0).toLocaleString()} tone="#cba6f7" />
                <Metric label="最近 Run" value={selectedSession.latest_run_id || '-'} tone="#89b4fa" small />
              </div>

              <div style={{ background: 'rgba(24, 24, 37, 0.5)', padding: '24px', borderRadius: '12px', border: '1px solid #313244', marginBottom: '24px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#89b4fa', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Zap size={18} /> 最近需求 (Latest Requirement)
                </h3>
                <p style={{ margin: 0, fontSize: '1.05rem', color: '#cdd6f4', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                  {selectedSession.requirement || '暂无最近需求摘要'}
                </p>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.55, textAlign: 'center' }}>
                <MessageSquare size={64} color="#6c7086" style={{ marginBottom: '16px' }} />
                <p style={{ color: '#a6adc8', fontSize: '1.08rem', maxWidth: '640px', lineHeight: 1.7 }}>
                  运行历史现在按“历史会话”聚合。点击“进入会话深度回放”可查看完整问答、每次运行开始/结束、Agent 内部事件与工具调用。
                </p>
              </div>
            </div>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6c7086', flexDirection: 'column', gap: '16px' }}>
              <History size={48} style={{ opacity: 0.5 }} />
              <p>请在左侧列表中选择一个历史会话以查看详情</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone, small = false }) {
  return (
    <div style={{ border: '1px solid #313244', background: 'rgba(24, 24, 37, 0.42)', borderRadius: '12px', padding: '16px' }}>
      <div style={{ color: '#a6adc8', fontSize: '0.82rem', marginBottom: '8px' }}>{label}</div>
      <div style={{ color: tone, fontSize: small ? '0.95rem' : '1.45rem', fontWeight: 800, fontFamily: small ? 'monospace' : 'inherit', wordBreak: 'break-all' }}>
        {value}
      </div>
    </div>
  );
}
