import { useState, useEffect } from 'react';
import { Activity, Sparkles, Search, X, GitBranch } from 'lucide-react';
import Editor from '@monaco-editor/react';

const API_BASE = '';

const SKILL_CATEGORIES = {
  all: { label: '全部技能', icon: '🔧' },
  filesystem: { label: '文件操作', icon: '📁' },
  network: { label: '网络与搜索', icon: '🌐' },
  visualization: { label: '数据可视化', icon: '📊' },
  system: { label: '系统操作', icon: '💻' },
  analysis: { label: '代码分析', icon: '🔍' },
  custom: { label: '自定义技能', icon: '⚡' },
};

const SKILL_CATEGORY_MAP = {
  write_file: 'filesystem',
  read_file: 'filesystem',
  run_command: 'system',
  web_search: 'network',
  http_requester: 'network',
  data_visualizer: 'visualization',
  math_sandbox: 'analysis',
  mindmap_generator: 'visualization',
  code_analyzer: 'analysis',
  file_tree_viewer: 'filesystem',
  project_scaffolder: 'system',
  git_operator: 'system',
  database_query: 'analysis',
  generate_report: 'visualization',
  manage_todo: 'system',
  dispatch_subagent: 'system',
};

function SkillsStore({ skills, enabledSkills, setEnabledSkills, onImportSkill }) {
  const [skillTab, setSkillTab] = useState('local');
  const [marketSkills, setMarketSkills] = useState([]);
  const [marketError, setMarketError] = useState('');
  const [installingSkill, setInstallingSkill] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
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
  const [convertingSkill, setConvertingSkill] = useState('');

  const fetchMarketSkills = async () => {
    setMarketError('');
    try {
      const res = await fetch(`${API_BASE}/api/skills/market`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setMarketSkills(data.market_skills || []);
    } catch (e) {
      console.log("Failed to fetch market skills:", e);
      setMarketError(`云端应用市场同步失败：${e.message}`);
    }
  };

  useEffect(() => {
    if (skillTab === 'market' && marketSkills.length === 0) {
      const timer = window.setTimeout(() => fetchMarketSkills(), 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [skillTab, marketSkills.length]);

  const handleDownloadSkill = async (skillId) => {
    setInstallingSkill(skillId);
    try {
      const res = await fetch(`${API_BASE}/api/skills/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skillId })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        const credentialNote = data.skill?.credential_required && data.skill?.credential_note
          ? `\n\n提示：${data.skill.credential_note}`
          : '';
        alert(`${data.message || "已从云端拉取技能！"}${credentialNote}`);
        if (onImportSkill) await onImportSkill();
        await fetchMarketSkills();
        setSkillTab('local');
      } else {
        alert(`安装失败: ${data.detail || `HTTP ${res.status}`}`);
      }
    } catch (e) {
      alert(`安装失败: ${e.message}`);
    } finally {
      setInstallingSkill('');
    }
  };

  const handleImportSkill = async () => {
    setImportError('');
    try {
      const res = await fetch(`${API_BASE}/api/skills/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: importCode })
      });
      if (res.ok) {
        alert("自定义技能注入成功！");
        setIsImportModalOpen(false);
        if (onImportSkill) onImportSkill();
      } else {
        const err = await res.json();
        setImportError(err.detail);
      }
    } catch (e) {
      setImportError(`网络错误: ${e.message}`);
    }
  };

  const handleConvertSkillToTemplate = async (skillName) => {
    setConvertingSkill(skillName);
    try {
      const res = await fetch(`${API_BASE}/api/workflows/skills/${encodeURIComponent(skillName)}/to-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      alert(`已转换为工作流模板：${data.template?.title || data.template_id}\n可以在 Workflow Templates 页面打开和继续编排。`);
    } catch (e) {
      alert(`转换失败：${e.message}`);
    } finally {
      setConvertingSkill('');
    }
  };

  const getCategory = (name) => SKILL_CATEGORY_MAP[name] || 'custom';

  const filteredSkills = skills.filter(skill => {
    const name = skill.function.name;
    const desc = skill.function.description || '';
    const matchesSearch = !searchQuery ||
      name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      desc.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = activeCategory === 'all' || getCategory(name) === activeCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '32px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
        <div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
            <Activity size={28} color="var(--sys-color-primary)" /> 技能大厅 (Skills Store)
          </h2>
          <p style={{ color: 'var(--sys-color-on-surface-variant)', marginTop: '8px' }}>
            管理 Agent 的核心能力模块。开启的技能将在深度工作流中被动态调用。
          </p>
        </div>
        <button
          className="btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          onClick={() => setIsImportModalOpen(true)}
        >
          <Sparkles size={16} /> ➕ 导入自定义技能
        </button>
      </div>

      {/* Main Tabs */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--sys-color-surface-variant)', paddingBottom: '8px' }}>
        <button
          onClick={() => setSkillTab('local')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem', fontWeight: 'bold', color: skillTab === 'local' ? 'var(--sys-color-primary)' : 'var(--sys-color-on-surface-variant)', borderBottom: skillTab === 'local' ? '2px solid var(--sys-color-primary)' : 'none', padding: '8px' }}
        >
          已安装技能 ({skills.length})
        </button>
        <button
          onClick={() => setSkillTab('market')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem', fontWeight: 'bold', color: skillTab === 'market' ? 'var(--sys-color-primary)' : 'var(--sys-color-on-surface-variant)', borderBottom: skillTab === 'market' ? '2px solid var(--sys-color-primary)' : 'none', padding: '8px' }}
        >
          🌐 云端应用市场
        </button>
      </div>

      {skillTab === 'local' ? (
        <>
          {/* Search + Category Filter */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ position: 'relative', flex: '1 1 300px' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--sys-color-on-surface-variant)' }} />
              <input
                type="text"
                className="input-elegant"
                placeholder="搜索技能名称或描述..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%', paddingLeft: '36px' }}
              />
            </div>
          </div>

          {/* Category Chips */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
            {Object.entries(SKILL_CATEGORIES).map(([key, { label, icon }]) => (
              <button
                key={key}
                onClick={() => setActiveCategory(key)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  border: activeCategory === key ? '2px solid var(--sys-color-primary)' : '1px solid var(--sys-color-surface-variant)',
                  background: activeCategory === key ? 'var(--sys-color-primary-container)' : 'transparent',
                  color: activeCategory === key ? 'var(--sys-color-on-primary-container)' : 'var(--sys-color-on-surface-variant)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: activeCategory === key ? 'bold' : 'normal',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {icon} {label}
              </button>
            ))}
          </div>

          {/* Skills Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            {filteredSkills.map((skill) => {
              const isEnabled = enabledSkills.includes(skill.function.name);
              const category = getCategory(skill.function.name);
              const catInfo = SKILL_CATEGORIES[category] || SKILL_CATEGORIES.custom;
              return (
                <div key={skill.function.name} className="card glass" style={{
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  border: isEnabled ? '1px solid var(--sys-color-primary)' : '1px solid var(--sys-color-surface-variant)',
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden'
                }}>
                  {/* Enabled glow */}
                  {isEnabled && (
                    <div style={{
                      position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
                      background: 'linear-gradient(90deg, var(--sys-color-primary), #00ff9d)',
                    }} />
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '1.4rem' }}>{catInfo.icon}</span>
                      <div>
                        <h3 style={{ margin: 0, color: 'var(--sys-color-primary)', fontSize: '0.95rem' }}>
                          {skill.function.name}
                        </h3>
                        <span style={{
                          fontSize: '0.7rem',
                          color: 'var(--sys-color-on-surface-variant)',
                          backgroundColor: 'var(--sys-color-surface-variant)',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          marginTop: '2px',
                          display: 'inline-block'
                        }}>
                          {catInfo.label}
                        </span>
                      </div>
                    </div>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={isEnabled}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEnabledSkills(prev => [...prev, skill.function.name]);
                          } else {
                            setEnabledSkills(prev => prev.filter(name => name !== skill.function.name));
                          }
                        }}
                        style={{ width: '18px', height: '18px', accentColor: 'var(--sys-color-primary)' }}
                      />
                    </label>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--sys-color-on-surface-variant)', flex: 1, lineHeight: 1.5 }}>
                    {skill.function.description}
                  </p>
                  {/* Params preview */}
                  {skill.function.parameters?.properties && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--sys-color-on-surface-variant)', fontFamily: 'monospace', opacity: 0.7 }}>
                      参数: {Object.keys(skill.function.parameters.properties).join(', ')}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => handleConvertSkillToTemplate(skill.function.name)}
                    disabled={convertingSkill === skill.function.name}
                    style={{
                      marginTop: '4px',
                      padding: '8px 10px',
                      borderRadius: '10px',
                      border: '1px solid var(--sys-color-surface-variant)',
                      background: 'rgba(83, 140, 255, 0.1)',
                      color: 'var(--sys-color-on-surface)',
                      cursor: convertingSkill === skill.function.name ? 'wait' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      fontWeight: 700
                    }}
                  >
                    <GitBranch size={15} />
                    {convertingSkill === skill.function.name ? '正在转换...' : '转为工作流模板'}
                  </button>
                </div>
              );
            })}
            {filteredSkills.length === 0 && (
              <p style={{ color: 'var(--sys-color-on-surface-variant)', gridColumn: '1 / -1', textAlign: 'center', padding: '40px' }}>
                {searchQuery || activeCategory !== 'all' ? '未找到匹配的技能。' : '暂无可用技能。'}
              </p>
            )}
          </div>
        </>
      ) : (
        <div>
          <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input
              type="text"
              className="input-elegant"
              placeholder="🔍 搜索海量应用市场 (如 'Database', 'Notion')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ flex: 1 }}
            />
          </div>
          {marketError && (
            <div style={{
              marginBottom: '18px',
              padding: '12px 14px',
              borderRadius: '12px',
              border: '1px solid rgba(255, 120, 120, 0.35)',
              background: 'rgba(255, 80, 80, 0.08)',
              color: 'var(--sys-color-on-surface)'
            }}>
              {marketError}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
            {marketSkills
              .filter(skill => {
                const query = searchQuery.toLowerCase();
                return (skill.name || '').toLowerCase().includes(query)
                  || (skill.description || '').toLowerCase().includes(query)
                  || (skill.category || '').toLowerCase().includes(query);
              })
              .map((skill) => {
                const isInstalling = installingSkill === skill.id;
                const isInstalled = Boolean(skill.installed);
                return (
                <div key={skill.id} className="card glass" style={{
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  border: isInstalled ? '1px solid rgba(110, 231, 183, 0.45)' : '1px dashed var(--sys-color-surface-variant)',
                  boxShadow: isInstalled ? 'inset 0 0 0 1px rgba(110, 231, 183, 0.12)' : 'none'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                    <div style={{ fontSize: '2rem', lineHeight: 1 }}>{skill.icon}</div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <h3 style={{ margin: 0, color: 'var(--sys-color-on-surface)', wordBreak: 'break-word' }}>{skill.name}</h3>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--sys-color-primary)', backgroundColor: 'var(--sys-color-primary-container)', padding: '2px 6px', borderRadius: '6px', display: 'inline-block' }}>
                          {skill.source_label || '官方认证'}
                        </span>
                        {skill.category && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--sys-color-on-surface-variant)', backgroundColor: 'var(--sys-color-surface-variant)', padding: '2px 6px', borderRadius: '6px', display: 'inline-block' }}>
                            {skill.category}
                          </span>
                        )}
                        {skill.requires_network && (
                          <span style={{ fontSize: '0.7rem', color: '#7dd3fc', backgroundColor: 'rgba(56, 189, 248, 0.14)', padding: '2px 6px', borderRadius: '6px', display: 'inline-block' }}>
                            需联网
                          </span>
                        )}
                        {skill.credential_required && (
                          <span title={skill.credential_note || ''} style={{ fontSize: '0.7rem', color: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.14)', padding: '2px 6px', borderRadius: '6px', display: 'inline-block' }}>
                            需密钥
                          </span>
                        )}
                        {isInstalled && (
                          <span style={{ fontSize: '0.7rem', color: '#86efac', backgroundColor: 'rgba(34, 197, 94, 0.14)', padding: '2px 6px', borderRadius: '6px', display: 'inline-block' }}>
                            已拉取
                          </span>
                        )}
                      </div>
                      {skill.function_name && (
                        <div style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--sys-color-on-surface-variant)', fontFamily: 'monospace', opacity: 0.78 }}>
                          {skill.function_name}
                        </div>
                      )}
                    </div>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--sys-color-on-surface-variant)', flex: 1 }}>
                    {skill.description}
                  </p>
                  {skill.credential_note && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--sys-color-on-surface-variant)', lineHeight: 1.45, opacity: 0.86 }}>
                      {skill.credential_note}
                    </div>
                  )}
                  <button
                    onClick={() => handleDownloadSkill(skill.id)}
                    disabled={isInstalling || isInstalled}
                    className="btn-primary"
                    style={{
                      padding: '8px',
                      fontSize: '0.9rem',
                      display: 'flex',
                      justifyContent: 'center',
                      gap: '8px',
                      opacity: isInstalled ? 0.72 : 1,
                      cursor: isInstalling ? 'wait' : isInstalled ? 'default' : 'pointer'
                    }}
                  >
                    {isInstalled ? '已拉取' : isInstalling ? '正在从云端拉取...' : '📥 从云端拉取'}
                  </button>
                </div>
              )})}
            {marketSkills.length === 0 && (
              <p style={{ color: 'var(--sys-color-on-surface-variant)' }}>云端应用市场正在同步...</p>
            )}
          </div>
        </div>
      )}

      {/* Import Modal */}
      {isImportModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content animate-fade-in" style={{ maxWidth: '800px', width: '90%' }}>
            <button className="modal-close" onClick={() => setIsImportModalOpen(false)}><X size={24} /></button>
            <h2 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={24} color="var(--sys-color-primary)" /> 导入自定义技能
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--sys-color-on-surface-variant)', marginBottom: '24px' }}>
              粘贴 Python 工具脚本。必须包含执行函数和 <code>SCHEMA</code> 字典。系统将动态编译注入。
            </p>
            {importError && (
              <div style={{ padding: '12px', backgroundColor: 'rgba(255,0,0,0.1)', color: 'var(--sys-color-error)', borderRadius: '8px', marginBottom: '16px', fontSize: '0.9rem' }}>
                {importError}
              </div>
            )}
            <div style={{ height: '350px', width: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid #313244' }}>
              <Editor
                height="100%"
                defaultLanguage="python"
                theme="vs-dark"
                value={importCode}
                onChange={(value) => setImportCode(value || '')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  wordWrap: 'on',
                  scrollBeyondLastLine: false,
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
              <button className="btn-primary" style={{ backgroundColor: 'var(--sys-color-surface-variant)', color: 'var(--sys-color-on-surface)' }} onClick={() => setIsImportModalOpen(false)}>取消</button>
              <button className="btn-primary" onClick={handleImportSkill}>🚀 编译并加载</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SkillsStore;
