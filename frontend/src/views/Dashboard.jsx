import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';

const API_BASE = `http://${window.location.hostname}:8000`;

const AnimatedNumber = ({ value, suffix = '' }) => {
  // 移除复杂的 setInterval 动画，直接渲染传入的真实数值，避免 React 18 StrictMode 下的闭包陷阱和重渲染导致的数据闪烁归零问题
  return <span>{value}{suffix}</span>;
};

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [runs, setRuns] = useState([]);
  const [reports, setReports] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const navigate = useNavigate();

  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/telemetry?t=${Date.now()}`, { cache: 'no-store' });
      if (res.ok) {
        setTelemetry(await res.json());
      }
    } catch (e) {
      console.error("Telemetry fetch error:", e);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    let success = false;
    try {
      const [statsRes, runsRes, reportsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dashboard/stats`, { cache: 'no-store' }),
        fetch(`${API_BASE}/api/runs?limit=10`, { cache: 'no-store' }),
        fetch(`${API_BASE}/api/reports?limit=10`, { cache: 'no-store' }),
      ]);

      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        setStats(await statsRes.value.json());
        success = true;
      }
      if (runsRes.status === 'fulfilled' && runsRes.value.ok) {
        const data = await runsRes.value.json();
        setRuns(data.runs || []);
      }
      if (reportsRes.status === 'fulfilled' && reportsRes.value.ok) {
        const data = await reportsRes.value.json();
        setReports(data.reports || []);
      }
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
    return success;
  }, []);

  useEffect(() => {
    let timerAll;
    let timerTel;
    let isMounted = true;

    const pollAll = async () => {
      if (!isMounted) return;
      const success = await fetchAll();
      if (isMounted) timerAll = setTimeout(pollAll, success ? 30000 : 2000);
    };

    const pollTel = async () => {
      if (!isMounted) return;
      await fetchTelemetry();
      if (isMounted) timerTel = setTimeout(pollTel, 1000);
    };

    pollAll();
    pollTel();

    return () => {
      isMounted = false;
      clearTimeout(timerAll);
      clearTimeout(timerTel);
    };
  }, [fetchAll, fetchTelemetry]);

  const formatTime = (dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch { return dateStr; }
  };

  // ECharts options
  const successPieOption = stats ? {
    tooltip: { trigger: 'item', backgroundColor: '#1e1e2e', borderColor: '#313244', textStyle: { color: '#cdd6f4' } },
    legend: { show: false },
    series: [{
      type: 'pie', radius: ['50%', '75%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#1e1e2e', borderWidth: 3 },
      label: { show: true, position: 'center', formatter: () => `${stats.totalRuns || 0}\n总运行`, fontSize: 14, color: '#cdd6f4', lineHeight: 20 },
      emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
      data: [
        { value: stats.successRuns || 0, name: '成功', itemStyle: { color: '#a6e3a1' } },
        { value: stats.failedRuns || 0, name: '失败', itemStyle: { color: '#f38ba8' } }
      ]
    }]
  } : null;

  const agentEventsOption = stats ? {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: '#1e1e2e', borderColor: '#313244', textStyle: { color: '#cdd6f4' } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: [{
      type: 'category',
      data: (stats.eventsByAgent || []).map(e => e.agent || 'unknown'),
      axisTick: { alignWithLabel: true },
      axisLabel: { color: '#a6adc8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#313244' } }
    }],
    yAxis: [{
      type: 'value',
      axisLabel: { color: '#a6adc8' },
      splitLine: { lineStyle: { color: '#313244' } },
      axisLine: { show: false }
    }],
    series: [{
      name: '事件数',
      type: 'bar',
      barWidth: '50%',
      data: (stats.eventsByAgent || []).map(e => ({
        value: e.count || 0,
        itemStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#89b4fa' }, { offset: 1, color: '#74c7ec' }] },
          borderRadius: [4, 4, 0, 0]
        }
      }))
    }]
  } : null;

  if (loading && !stats) {
    return (
      <div style={{ padding: '48px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px' }}>
        <div style={{ width: 48, height: 48, border: '3px solid var(--sys-color-surface-variant)', borderTopColor: 'var(--sys-color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <p style={{ color: 'var(--sys-color-on-surface-variant)' }}>加载数据面板...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const cardStyle = {
    padding: '20px', borderRadius: '12px',
    background: 'linear-gradient(135deg, rgba(30, 30, 46, 0.8), rgba(49, 50, 68, 0.6))',
    border: '1px solid rgba(69, 71, 90, 0.5)',
    backdropFilter: 'blur(10px)',
  };

  const statCardStyle = (gradient) => ({
    ...cardStyle,
    background: gradient,
    display: 'flex', flexDirection: 'column', gap: '8px',
    minHeight: '128px',
    justifyContent: 'space-between',
    position: 'relative', overflow: 'hidden',
  });

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
            🌌 天韬（SkyT） 全景引擎面板
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--sys-color-on-surface-variant)' }}>
            以时间换空间，静水流深 —— 实时追踪引擎运转、深度推演与空间释放
            {lastUpdated && <span style={{ marginLeft: '12px', opacity: 0.6 }}>最后状态: {lastUpdated.toLocaleTimeString('zh-CN')}</span>}
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchAll} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px' }}>
          {loading ? <span key="load">刷新中...</span> : <span key="idle">🔄 刷新数据</span>}
        </button>
      </div>

      {/* Stat Cards Row */}
      <style>{`
        .dashboard-stat-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        @media (max-width: 1180px) {
          .dashboard-stat-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
        @media (max-width: 720px) {
          .dashboard-stat-grid {
            grid-template-columns: minmax(0, 1fr);
          }
        }
      `}</style>
      <div className="dashboard-stat-grid" style={{ display: 'grid', gap: '16px' }}>
        <div style={statCardStyle('linear-gradient(135deg, rgba(137, 180, 250, 0.15), rgba(116, 199, 236, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#89b4fa', textTransform: 'uppercase', letterSpacing: '1px' }}>天韬（SkyT）演进次数</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            <AnimatedNumber value={stats?.totalRuns || 0} />
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>工作流总执行量</span>
        </div>

        <div style={statCardStyle('linear-gradient(135deg, rgba(166, 227, 161, 0.15), rgba(148, 226, 213, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#a6e3a1', textTransform: 'uppercase', letterSpacing: '1px' }}>成功运行</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            <AnimatedNumber value={stats?.successRuns || 0} />
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>
            成功率 {Number(stats?.totalRuns) > 0 ? Math.round((Number(stats?.successRuns) / Number(stats?.totalRuns)) * 100) : 0}%
          </span>
        </div>

        <div style={statCardStyle('linear-gradient(135deg, rgba(243, 139, 168, 0.15), rgba(235, 160, 172, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#f38ba8', textTransform: 'uppercase', letterSpacing: '1px' }}>失败运行</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            <AnimatedNumber value={stats?.failedRuns || 0} />
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>需要关注</span>
        </div>

        <div style={statCardStyle('linear-gradient(135deg, rgba(116, 199, 236, 0.15), rgba(137, 220, 235, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#74c7ec', textTransform: 'uppercase', letterSpacing: '1px' }}>报告生成数</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            <AnimatedNumber value={stats?.totalReports || 0} />
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>累计生成报告</span>
        </div>

        <div style={statCardStyle('linear-gradient(135deg, rgba(250, 179, 135, 0.15), rgba(249, 226, 175, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#fab387', textTransform: 'uppercase', letterSpacing: '1px' }}>质量评分</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            {stats?.averageQualityScore || 0}<span style={{ fontSize: '1rem', opacity: 0.6 }}>/10</span>
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>平均质量</span>
        </div>

        <div style={statCardStyle('linear-gradient(135deg, rgba(203, 166, 247, 0.15), rgba(180, 190, 254, 0.08))')}>
          <span style={{ fontSize: '0.8rem', color: '#cba6f7', textTransform: 'uppercase', letterSpacing: '1px' }}>天韬蒸镀系统</span>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#cdd6f4' }}>
            <AnimatedNumber value={stats?.spaceSavedKb || 0} suffix=" KB" />
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a6adc8' }}>压缩冗余 留存精华</span>
        </div>
      </div>

      {/* System Telemetry Bar */}
      {telemetry && !telemetry.error && (
        <div style={{ ...cardStyle, display: 'flex', gap: '32px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#89b4fa' }}>💻 天韬引擎（SkyT Core）状态</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#a6adc8' }}>CPU</span>
            <div style={{ width: 120, height: 8, borderRadius: 4, background: '#313244', overflow: 'hidden' }}>
              <div style={{ width: `${telemetry.cpu_usage}%`, height: '100%', borderRadius: 4, background: telemetry.cpu_usage > 80 ? '#f38ba8' : '#a6e3a1', transition: 'width 0.5s' }} />
            </div>
            <span style={{ fontSize: '0.8rem', color: '#cdd6f4', fontFamily: 'monospace' }}>{Number(telemetry.cpu_usage).toFixed(1)}%</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#a6adc8' }}>RAM</span>
            <div style={{ width: 120, height: 8, borderRadius: 4, background: '#313244', overflow: 'hidden' }}>
              <div style={{ width: `${telemetry.ram_usage}%`, height: '100%', borderRadius: 4, background: telemetry.ram_usage > 80 ? '#fab387' : '#89b4fa', transition: 'width 0.5s' }} />
            </div>
            <span style={{ fontSize: '0.8rem', color: '#cdd6f4', fontFamily: 'monospace' }}>{Number(telemetry.ram_used).toFixed(2)}/{Number(telemetry.ram_total).toFixed(2)} GB</span>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button className="btn-primary" onClick={() => navigate('/')} style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '6px' }}>💬 新建对话</button>
        <button className="btn-secondary" onClick={() => navigate('/history')} style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '6px' }}>📋 运行历史</button>
        <button className="btn-secondary" onClick={() => navigate('/reports')} style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '6px' }}>📝 报告中心</button>
        <button className="btn-secondary" onClick={() => navigate('/skills')} style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '6px' }}>🧰 技能大厅</button>
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '20px' }}>
        {/* Pie Chart */}
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 8px', fontSize: '0.95rem', color: '#cdd6f4' }}>🎯 运行成功率</h3>
          {successPieOption ? (
            <ReactECharts 
              option={successPieOption} 
              style={{ height: '260px' }} 
              theme="dark" 
              onEvents={{
                click: (e) => {
                  if (e.name === '失败') navigate('/history', { state: { filterStatus: 'FAILED' } });
                  else if (e.name === '成功') navigate('/history', { state: { filterStatus: 'SUCCESS' } });
                }
              }}
            />
          ) : (
            <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a6adc8' }}>暂无数据</div>
          )}
        </div>

        {/* Bar Chart */}
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 8px', fontSize: '0.95rem', color: '#cdd6f4' }}>📊 Agent 事件分布</h3>
          {agentEventsOption && (stats?.eventsByAgent || []).length > 0 ? (
            <ReactECharts option={agentEventsOption} style={{ height: '260px' }} theme="dark" />
          ) : (
            <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a6adc8' }}>暂无事件数据</div>
          )}
        </div>
      </div>

      {/* Recent Runs + Recent Reports */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '20px' }}>
        {/* Recent Runs */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#cdd6f4' }}>🚀 最近运行</h3>
            <button onClick={() => navigate('/history')} style={{ background: 'none', border: 'none', color: '#89b4fa', cursor: 'pointer', fontSize: '0.8rem' }}>查看全部 →</button>
          </div>
          {runs.length === 0 ? (
            <p style={{ color: '#a6adc8', fontSize: '0.85rem', textAlign: 'center', padding: '20px' }}>暂无运行记录</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {runs.slice(0, 5).map((run, idx) => (
                <div key={idx}
                  onClick={() => navigate(`/replay/${run.run_id}`)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 12px', borderRadius: '8px', cursor: 'pointer',
                    background: 'rgba(49, 50, 68, 0.4)', border: '1px solid rgba(69, 71, 90, 0.3)',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(69, 71, 90, 0.6)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(49, 50, 68, 0.4)'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                      backgroundColor: run.success ? '#a6e3a1' : '#f38ba8'
                    }} />
                    <span style={{ fontSize: '0.85rem', color: '#cdd6f4', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {run.requirement || run.run_id}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: '#a6adc8', flexShrink: 0, marginLeft: '8px' }}>
                    {formatTime(run.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Reports */}
        <div style={cardStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#cdd6f4' }}>📝 最近报告</h3>
            <button onClick={() => navigate('/reports')} style={{ background: 'none', border: 'none', color: '#89b4fa', cursor: 'pointer', fontSize: '0.8rem' }}>查看全部 →</button>
          </div>
          {reports.length === 0 ? (
            <p style={{ color: '#a6adc8', fontSize: '0.85rem', textAlign: 'center', padding: '20px' }}>暂无报告</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {reports.slice(0, 5).map((report, idx) => (
                <div key={idx}
                  onClick={() => navigate('/reports')}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 12px', borderRadius: '8px', cursor: 'pointer',
                    background: 'rgba(49, 50, 68, 0.4)', border: '1px solid rgba(69, 71, 90, 0.3)',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(69, 71, 90, 0.6)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(49, 50, 68, 0.4)'}
                >
                  <span style={{ fontSize: '0.85rem', color: '#cdd6f4', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    📄 {report.title}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#a6adc8', flexShrink: 0, marginLeft: '8px' }}>
                    {formatTime(report.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
