import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, CheckCircle2, CirclePause, Play, RefreshCw, RotateCcw, ShieldCheck, Square, Workflow } from 'lucide-react';

const API_BASE = '';
const ACTIVE_STATES = new Set(['queued', 'running', 'paused', 'waiting_approval']);

function statusTone(status) {
  if (status === 'succeeded') return '#a6e3a1';
  if (['failed', 'cancelled'].includes(status)) return '#f38ba8';
  if (['running', 'waiting_approval'].includes(status)) return '#89b4fa';
  return '#f9e2af';
}

function statusLabel(status) {
  return ({ queued: '排队中', running: '运行中', paused: '已暂停', waiting_approval: '等待审批', succeeded: '已通过', failed: '失败', cancelled: '已取消' })[status] || status || '未知';
}

export default function WorkflowRunConsole() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    if (!runId) return;
    try {
      const [runResponse, eventResponse] = await Promise.all([
        fetch(`${API_BASE}/api/workflows/runs/${encodeURIComponent(runId)}`),
        fetch(`${API_BASE}/api/workflows/runs/${encodeURIComponent(runId)}/events`),
      ]);
      const runPayload = await runResponse.json();
      const eventPayload = await eventResponse.json();
      if (!runResponse.ok) throw new Error(runPayload.detail || '运行读取失败');
      setData(runPayload);
      setEvents(eventPayload.events || []);
      setNotice('');
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    const interval = window.setInterval(() => { void load(); }, 1800);
    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
    };
  }, [load]);

  const run = data?.run || {};
  const nodeRuns = data?.nodes;
  const nodes = useMemo(() => nodeRuns || [], [nodeRuns]);
  const active = ACTIVE_STATES.has(run.status);
  const latestNodes = useMemo(() => {
    const map = new Map();
    nodes.forEach((node) => map.set(node.node_id, node));
    return [...map.values()];
  }, [nodes]);

  const action = async (name, body = {}) => {
    setActionBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/workflows/runs/${encodeURIComponent(runId)}/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail?.message || payload.detail || '操作失败');
      await load();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) return <div style={{ padding: 32, color: '#cdd6f4' }}>正在加载工作流运行...</div>;
  if (!data) return <div style={{ padding: 32, color: '#f38ba8' }}>{notice || '运行不存在。'}</div>;

  return (
    <div style={{ padding: 28, height: '100%', overflowY: 'auto', boxSizing: 'border-box', color: '#cdd6f4', background: 'var(--sys-color-background)' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap', marginBottom: 24 }}>
        <div>
          <button type="button" onClick={() => navigate('/workflows')} style={{ border: 0, background: 'transparent', color: '#a6adc8', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer', padding: 0 }}>
            <ArrowLeft size={16} /> 返回工作流
          </button>
          <h1 style={{ margin: '16px 0 8px', fontSize: '1.7rem', display: 'flex', alignItems: 'center', gap: 10 }}><Workflow size={25} color="#89b4fa" />{run.workflow_spec?.title || runId}</h1>
          <div style={{ color: '#a6adc8', fontFamily: 'monospace', fontSize: '.82rem' }}>{runId} · 计划版本 {run.plan_revision || 1}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <strong style={{ color: statusTone(run.status), border: `1px solid ${statusTone(run.status)}`, padding: '8px 12px', borderRadius: 18 }}>{statusLabel(run.status)}</strong>
          <button type="button" onClick={() => void load()} title="刷新运行状态" style={iconButton}><RefreshCw size={16} /></button>
          {run.status === 'paused' && <button type="button" disabled={actionBusy} onClick={() => void action('resume')} style={primaryButton}><Play size={16} />恢复</button>}
          {run.status === 'waiting_approval' && <button type="button" disabled={actionBusy} onClick={() => void action('approve')} style={primaryButton}><ShieldCheck size={16} />批准</button>}
          {run.status === 'running' && <button type="button" disabled={actionBusy} onClick={() => void action('pause')} style={secondaryButton}><CirclePause size={16} />暂停</button>}
          {active && <button type="button" disabled={actionBusy} onClick={() => void action('cancel', { reason: '控制台取消' })} style={dangerButton}><Square size={15} />取消</button>}
          {['failed', 'cancelled'].includes(run.status) && <button type="button" disabled={actionBusy} onClick={() => void action('rollback')} style={secondaryButton}><RotateCcw size={16} />回滚</button>}
          {['failed', 'cancelled'].includes(run.status) && <button type="button" disabled={actionBusy} onClick={() => void action('replan', { reason: '从控制台请求重规划' })} style={primaryButton}><RotateCcw size={16} />重规划</button>}
        </div>
      </header>

      {notice && <div style={{ marginBottom: 16 }}><AlertCircle size={16} /> {notice}</div>}
      <section style={metricGrid}>
        <Metric label="模型调用" value={run.model_calls || 0} />
        <Metric label="Token" value={Number(run.total_tokens || 0).toLocaleString()} />
        <Metric label="节点尝试" value={nodes.length} />
        <Metric label="检查点" value={(data.checkpoints || []).length} />
        <Metric label="重规划" value={`${run.replan_count || 0}/${run.max_replans || 3}`} />
      </section>

      <main style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(340px, .85fr)', gap: 18, alignItems: 'start' }}>
        <section style={panel}>
          <h2 style={sectionTitle}><Workflow size={18} /> 节点执行时间线</h2>
          <div style={{ display: 'grid', gap: 10 }}>
            {latestNodes.length ? latestNodes.map((node) => (
              <article key={node.node_id} style={{ border: '1px solid #313244', borderLeft: `4px solid ${statusTone(node.status)}`, borderRadius: 8, padding: 14, background: 'rgba(30,30,46,.65)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <strong>{node.node_id}</strong><span style={{ color: statusTone(node.status) }}>{statusLabel(node.status)}</span>
                </div>
                <div style={{ color: '#a6adc8', marginTop: 7, fontSize: '.84rem' }}>尝试 {node.attempt || 1} · {node.model_profile || 'auto'} {node.provider ? `· ${node.provider}` : ''}</div>
                {node.error_text && <div style={{ color: '#f38ba8', marginTop: 8 }}>{node.error_text}</div>}
                {node.evidence?.length > 0 && <div style={{ color: '#a6e3a1', marginTop: 8 }}>已记录 {node.evidence.length} 条证据</div>}
              </article>
            )) : <div style={{ color: '#a6adc8' }}>节点尚未开始执行。</div>}
          </div>
        </section>

        <section style={panel}>
          <h2 style={sectionTitle}><CheckCircle2 size={18} /> 运行事件</h2>
          <div style={{ display: 'grid', gap: 9, maxHeight: 520, overflowY: 'auto' }}>
            {events.slice().reverse().map((event, index) => (
              <div key={`${event.id || event.created_at}-${index}`} style={{ borderBottom: '1px solid #313244', paddingBottom: 9 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: '.82rem' }}><strong>{event.event_type}</strong><span style={{ color: statusTone(String(event.status || '').toLowerCase()) }}>{event.status}</span></div>
                <div style={{ color: '#a6adc8', marginTop: 4, lineHeight: 1.5 }}>{event.message}</div>
              </div>
            ))}
            {!events.length && <div style={{ color: '#a6adc8' }}>暂无事件。</div>}
          </div>
        </section>
      </main>

      {run.result && <section style={{ ...panel, marginTop: 18 }}><h2 style={sectionTitle}>最终交付</h2><pre style={{ whiteSpace: 'pre-wrap', color: '#cdd6f4', lineHeight: 1.6, margin: 0 }}>{run.result.result || JSON.stringify(run.result, null, 2)}</pre></section>}
    </div>
  );
}

function Metric({ label, value }) {
  return <div style={{ border: '1px solid #313244', borderRadius: 8, padding: 14, background: 'rgba(30,30,46,.65)' }}><div style={{ color: '#a6adc8', fontSize: '.8rem' }}>{label}</div><strong style={{ display: 'block', marginTop: 7, color: '#89b4fa', fontSize: '1.2rem' }}>{value}</strong></div>;
}

const panel = { border: '1px solid #313244', borderRadius: 10, padding: 18, background: 'rgba(24,24,37,.6)' };
const metricGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginBottom: 18 };
const sectionTitle = { margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: 8, fontSize: '1rem' };
const iconButton = { border: '1px solid #45475a', background: 'transparent', color: '#cdd6f4', width: 38, height: 38, borderRadius: 8, display: 'grid', placeItems: 'center', cursor: 'pointer' };
const primaryButton = { border: 0, background: '#89b4fa', color: '#11111b', minHeight: 38, padding: '0 13px', borderRadius: 8, display: 'inline-flex', gap: 7, alignItems: 'center', cursor: 'pointer', fontWeight: 700 };
const secondaryButton = { ...primaryButton, background: 'transparent', color: '#cdd6f4', border: '1px solid #45475a' };
const dangerButton = { ...primaryButton, background: '#f38ba8', color: '#11111b' };
