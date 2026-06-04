import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { History, PlayCircle, CheckCircle, XCircle, Search, Clock, Activity, Target, Zap, FileText } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8000`;

function parseJsonField(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function tokenSummary(run) {
  const breakdown = parseJsonField(run?.token_breakdown_json) || {};
  const api = Number(run?.api_tokens ?? breakdown.api_tokens ?? 0);
  const local = Number(run?.local_tokens ?? breakdown.local_tokens ?? 0);
  const total = Number(run?.total_tokens ?? breakdown.total_tokens ?? api + local);
  const real = Number(breakdown.real_tokens || 0);
  const estimated = Number(breakdown.estimated_tokens || 0);
  let source = run?.token_source || breakdown.source || 'none';
  if ((!source || source === 'none') && total) {
    source = estimated > 0 ? 'estimated' : real > 0 ? 'real' : 'estimated';
  }
  return { api, local, total, source };
}

function TokenSummary({ run, compact = false }) {
  const tokens = tokenSummary(run);
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
  const [runs, setRuns] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState(location.state?.filterStatus || 'ALL');
  const [selectedRun, setSelectedRun] = useState(null);
  const [generatingMarkdown, setGeneratingMarkdown] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/runs?limit=50`)
      .then(res => res.json())
      .then(data => {
        setRuns(data.runs || []);
        if (data.runs && data.runs.length > 0) {
          setSelectedRun(data.runs[0]);
        }
      })
      .catch(e => console.error("Failed to load runs", e));
  }, []);

  const filteredRuns = runs.filter(r => {
    if (filterStatus !== 'ALL') {
      if (filterStatus === 'SUCCESS' && !r.success) return false;
      if (filterStatus === 'FAILED' && r.success) return false;
    }
    return r.requirement.toLowerCase().includes(searchTerm.toLowerCase()) || 
           r.run_id.toLowerCase().includes(searchTerm.toLowerCase());
  });

  useEffect(() => {
    if (filteredRuns.length > 0) {
      if (!selectedRun || !filteredRuns.find(r => r.run_id === selectedRun.run_id)) {
        setSelectedRun(filteredRuns[0]);
      }
    } else {
      setSelectedRun(null);
    }
  }, [filteredRuns, selectedRun]);

  const formatTime = (dateStr) => {
    try {
      return new Date(dateStr).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
    } catch { return dateStr; }
  };

  const generateImportantWorkLog = async () => {
    if (!selectedRun?.run_id || generatingMarkdown) return;
    setGeneratingMarkdown(true);
    try {
      const res = await fetch(`${API_BASE}/api/runs/${selectedRun.run_id}/generate-markdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'important_work_log', language: 'zh-CN' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '生成失败');
      alert(`已生成历史重要工作记录，报告 ID：${data.report_id}`);
    } catch (error) {
      alert(`生成历史重要工作记录失败：${error.message}`);
    } finally {
      setGeneratingMarkdown(false);
    }
  };

  return (
    <div style={{ padding: '32px', overflowY: 'hidden', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', margin: 0, display: 'flex', alignItems: 'center', gap: '12px', color: '#cdd6f4' }}>
            <History size={28} color="#89b4fa" />
            运行历史 (Run History)
          </h1>
          <p style={{ color: '#a6adc8', margin: '8px 0 0', fontSize: '0.9rem' }}>
            查看所有 Agent 的执行记录、耗时与 Token 消耗。
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
                <div style={{ flex: 1, textAlign: 'center', color: '#cdd6f4', fontSize: '1rem', fontWeight: 'bold' }}>
                  {status === 'ALL' ? <span key="all">全部</span> : (status === 'SUCCESS' ? <span key="succ">成功</span> : <span key="fail">失败</span>)}
                </div>
              </button>
            ))}
          </div>
          <div style={{ position: 'relative', width: '250px' }}>
            <Search size={16} color="#a6adc8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input 
              type="text" 
              placeholder="搜索需求或 ID..." 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width: '100%', padding: '8px 12px 8px 36px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '8px', color: '#cdd6f4', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, gap: '24px', overflow: 'hidden' }}>
        
        {/* List Panel (Left) */}
        <div style={{ 
          width: '450px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '8px' 
        }}>
          {filteredRuns.map((run) => {
            const isSelected = selectedRun?.run_id === run.run_id;
            return (
              <div 
                key={run.run_id} 
                onClick={() => setSelectedRun(run)}
                style={{ 
                  display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', cursor: 'pointer',
                  background: isSelected ? 'rgba(49, 50, 68, 0.8)' : 'rgba(30, 30, 46, 0.6)', 
                  borderTop: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderRight: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderBottom: `1px solid ${isSelected ? '#89b4fa' : '#313244'}`,
                  borderLeft: `4px solid ${run.success ? '#a6e3a1' : '#f38ba8'}`,
                  borderRadius: '8px', transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'monospace', color: '#89b4fa', fontSize: '0.85rem' }}>{run.run_id}</span>
                  <span style={{ fontSize: '0.75rem', color: '#a6adc8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> {formatTime(run.created_at)}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.95rem', color: '#cdd6f4', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {run.requirement}
                </p>
                <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: '#a6adc8' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Target size={14} /> <span key="qual">质量:</span> {run.quality_score}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Activity size={14} /> <TokenSummary run={run} compact /></span>
                </div>
              </div>
            );
          })}
          {filteredRuns.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px', color: '#6c7086' }}>
              <span key="no">没有找到相关的执行记录。</span>
            </div>
          )}
        </div>

        {/* Details Panel (Right) */}
        <div style={{ 
          flex: 1, overflowY: 'auto', padding: '32px', display: 'flex', flexDirection: 'column',
          background: 'linear-gradient(135deg, rgba(30, 30, 46, 0.8), rgba(49, 50, 68, 0.6))',
          border: '1px solid #313244', borderRadius: '12px', backdropFilter: 'blur(10px)'
        }}>
          {selectedRun ? (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: selectedRun.success ? '#a6e3a1' : '#f38ba8', fontWeight: 'bold' }}>
                      {selectedRun.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                      {selectedRun.success ? <span key="succ">执行成功 (SUCCESS)</span> : <span key="fail">执行失败 (FAILED)</span>}
                    </div>
                    <span style={{ fontSize: '0.9rem', color: '#a6adc8', fontFamily: 'monospace' }}>{selectedRun.run_id}</span>
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#bac2de', display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Clock size={16} /> {formatTime(selectedRun.created_at)}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Target size={16} /> <span key="score">质量评分:</span> <strong style={{ color: '#fab387' }}>{selectedRun.quality_score}/10</strong></span>
                    <TokenSummary run={selectedRun} />
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
                    {generatingMarkdown ? '生成中...' : '生成工作记录'}
                  </button>
                  <button 
                    onClick={() => navigate(`/replay/${selectedRun.run_id}`)}
                    style={{ 
                      background: '#89b4fa', color: '#11111b', border: 'none', padding: '10px 24px', borderRadius: '24px', 
                      display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '1rem',
                      boxShadow: '0 4px 12px rgba(137, 180, 250, 0.3)'
                    }}
                  >
                    <PlayCircle size={20} />
                    进入深度回放
                  </button>
                </div>
              </div>

              <div style={{ background: 'rgba(24, 24, 37, 0.5)', padding: '24px', borderRadius: '12px', border: '1px solid #313244', marginBottom: '24px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#89b4fa', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Zap size={18} /> 原始需求 (Requirement)
                </h3>
                <p style={{ margin: 0, fontSize: '1.1rem', color: '#cdd6f4', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                  {selectedRun.requirement}
                </p>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                <History size={64} color="#6c7086" style={{ marginBottom: '16px' }} />
                <p style={{ color: '#a6adc8', fontSize: '1.1rem' }}>点击上方“进入深度回放”以查看完整事件时间线和 Agent 内部思考过程。</p>
              </div>

            </div>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6c7086', flexDirection: 'column', gap: '16px' }}>
              <History size={48} style={{ opacity: 0.5 }} />
              <p>请在左侧列表中选择一次运行记录以查看详情</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
