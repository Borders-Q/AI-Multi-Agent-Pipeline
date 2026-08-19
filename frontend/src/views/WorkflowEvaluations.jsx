import { useEffect, useState } from 'react';
import { Activity, ArrowLeft, RefreshCw, Target } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API_BASE = '';

export default function WorkflowEvaluations() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/workflows/evaluations`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || '评测数据读取失败');
      setData(payload);
      setError('');
    } catch (reason) {
      setError(reason.message);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const metrics = data?.metrics || {};
  return (
    <div style={{ padding: 28, height: '100%', overflowY: 'auto', color: '#cdd6f4', background: 'var(--sys-color-background)' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <div>
          <button type="button" onClick={() => navigate('/workflows')} style={backButton}><ArrowLeft size={16} />返回工作流</button>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '16px 0 8px' }}><Target size={24} color="#89b4fa" />工作流评测</h1>
          <div style={{ color: '#a6adc8' }}>固定任务集 + 真实运行记录，用成功率、门禁、成本和人工接管评估工作流版本。</div>
        </div>
        <button type="button" onClick={() => void load()} title="刷新评测" style={iconButton}><RefreshCw size={16} /></button>
      </header>
      {error && <div style={{ color: '#f38ba8', marginBottom: 16 }}>{error}</div>}
      <section style={metricGrid}>
        <Metric label="基准任务" value={data?.benchmark?.case_count ?? '-'} />
        <Metric label="已运行" value={metrics.run_count ?? 0} />
        <Metric label="运行成功率" value={`${Math.round(Number(metrics.success_rate || 0) * 100)}%`} />
        <Metric label="门禁通过率" value={`${Math.round(Number(metrics.quality_gate_rate || 0) * 100)}%`} />
        <Metric label="平均模型调用" value={metrics.average_model_calls ?? 0} />
        <Metric label="人工接管" value={metrics.manual_takeover_rate != null ? `${Math.round(metrics.manual_takeover_rate * 100)}%` : '-'} />
      </section>
      <section style={panel}>
        <h2 style={sectionTitle}><Activity size={18} />基准任务</h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {(data?.benchmark?.cases || []).map((item) => (
            <article key={item.id} style={row}>
              <div><strong>{item.title}</strong><div style={{ color: '#a6adc8', marginTop: 5 }}>{item.category} · 必需门禁：{(item.required_gates || []).join('、')}</div></div>
              <span style={{ color: '#89b4fa' }}>{item.id}</span>
            </article>
          ))}
        </div>
      </section>
      <section style={{ ...panel, marginTop: 18 }}>
        <h2 style={sectionTitle}>最近运行</h2>
        {!data?.recent_runs?.length && <div style={{ color: '#a6adc8' }}>暂无运行记录。完成一次持久化工作流后，这里会展示真实指标。</div>}
        {(data?.recent_runs || []).map((run) => <div key={run.run_id} style={row}><span>{run.run_id}</span><span style={{ color: run.status === 'succeeded' ? '#a6e3a1' : '#f9e2af' }}>{run.status}</span></div>)}
      </section>
    </div>
  );
}

function Metric({ label, value }) {
  return <div style={metric}><div style={{ color: '#a6adc8', fontSize: '.8rem' }}>{label}</div><strong style={{ display: 'block', marginTop: 7, color: '#89b4fa', fontSize: '1.2rem' }}>{value}</strong></div>;
}

const panel = { border: '1px solid #313244', borderRadius: 8, padding: 18, background: 'rgba(24,24,37,.6)' };
const metricGrid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 18 };
const metric = { ...panel, padding: 14 };
const row = { display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', borderBottom: '1px solid #313244', padding: '10px 0' };
const sectionTitle = { margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: 8, fontSize: '1rem' };
const iconButton = { border: '1px solid #45475a', background: 'transparent', color: '#cdd6f4', width: 38, height: 38, borderRadius: 8, display: 'grid', placeItems: 'center', cursor: 'pointer' };
const backButton = { border: 0, background: 'transparent', color: '#a6adc8', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer', padding: 0 };
