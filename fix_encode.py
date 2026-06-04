import codecs

replacements = {
    397: '        alert("无法连接到后端，请确认 server.py 正在运行。");',
    413: '        alert("无法连接到后端，请确认 server.py 正在运行。");',
    426: '        alert("无法连接到后端，请确认 server.py 正在运行。");',
    491: '      setMessages(prev => [...prev, { role: \'user\', content: \'🚀 [用户操作] 启动深度工作流下钻分析...\' }]);',
    543: '        if (text.includes(\'启动深度工作流下钻\')) {',
    545: '          const allUserMsgs = messages.filter(m => m.role === \'user\' && !m.content.includes(\'启动深度工作流下钻\'));',
    559: '          <p style={{ color: \'var(--sys-color-primary)\', fontWeight: \'500\' }}>🚀 架构计划已生成，请在右侧文档面板审查。</p>',
    663: '          <p style={{ marginBottom: \'32px\', color: \'var(--sys-color-on-surface-variant)\' }}>高度自治的多智能体指挥控制台。</p>',
    683: '                <p style={{ margin: 0, fontSize: \'0.85rem\' }}><span className={`badge badge-${activeProvider || \'unknown\'}`}>{activeProvider || \'未配置模型\'}</span></p>',
    719: '              <NavLink to="/skills" className={({ isActive }) => isActive ? "btn-primary active-link" : "btn-secondary"} style={{ width: \'100%\', display: \'flex\', alignItems: \'center\', justifyContent: isSidebarOpen ? \'flex-start\' : \'center\', gap: \'12px\', padding: \'12px\', marginTop: \'8px\', border: \'none\' }} title="技能大厅">',
    721: '                <span style={{ maxWidth: isSidebarOpen ? \'200px\' : \'0px\', opacity: isSidebarOpen ? 1 : 0, overflow: \'hidden\', whiteSpace: \'nowrap\', transition: \'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)\' }}>技能大厅 (Skills)</span>',
    734: '                    <p style={{ margin: 0 }}>当前暂无任务规划。</p>',
    764: '                    ➕ 新开对话',
    791: '                    🗑️ 清空当前对话',
    802: '                收起侧边栏 ◀',
    805: '              <button className="btn-secondary" onClick={() => setIsSidebarOpen(true)} style={{ padding: \'8px 12px\', display: \'flex\', justifyContent: \'center\' }} title="展开侧边栏">',
    806: '                ▶',
    873: '                  {isWorkflowEditorOpen ? \'退出编辑\' : \'配置当前工作流\'}',
    883: '                    // Chat view only — Skills moved to /skills route',
    889: '                            <span>⚠️ 无法连接到核心系统。请确认后端服务 (server.py) 正在运行。</span>',
    913: '                                <p>请在下方输入指令。您可以通过侧边栏管理任务流、监控节点或配置云端模型。</p>',
    947: '                                                    {node.state === \'done\' ? <span key="done">✅</span> : <span key="prog">🔄</span>} <span>{node.node}</span>',
    949: '                                                  {i < msg.workflow.length - 1 && <span style={{ color: \'rgba(255,255,255,0.3)\', fontSize: \'0.8rem\' }}>→</span>}',
    962: '                                      {msg.role === \'agent\' && msg.routed_by === \'GPU\' && !msg.content.includes("非常抱歉") && !msg.content.includes("对不起") && !msg.content.includes("拒绝") && (',
    965: '                                            <Sparkles size={14} /> 🚀 启动深度工作流下钻 (云端 API)',
    980: '                                            <Activity size={14} className="animate-pulse" /> &lt; 深度运算与工具调用协议激活 /&gt;',
    996: '                                          <Activity size={14} className="animate-pulse" /> 连接神经元网络...',
    1010: '                                      title="切换当值模型"',
    1013: '                                          ? [{ value: "", label: "未配置模型" }]',
    1023: '                                        { value: \'standard\', label: \'⚡ 标准极速流\' },',
    1025: '                                        { value: \'expert_review\', label: \'🧐 专家审查流\' },',
    1026: '                                        { value: \'creative_brainstorm\', label: \'💡 发散风暴流\' }',
    1034: '                                      placeholder="请输入您的指令（简单的交由本地，复杂的交由云端）..."',
    1091: '                执行流 (Execution)',
    1095: '                  title="收起工作流"',
    1106: '                    执行中...',
    1153: '                  <button className="btn-primary" onClick={approvePlan}>✅ 批准执行 (Approve)</button>',
    1165: '                  <Sparkles size={24} color="var(--sys-color-primary)" /> 导入自定义技能',
    1167: '                  在此粘贴您自己编写的 Python 工具脚本。必须包含执行函数和符合 OpenAI Tool Call 规范的 schema 字典。系统将动态编译并注入，无需重启。',
    1195: '                  🚀 编译并加载',
    1207: '                <Settings size={24} /> 模型与 API Key 管理',
    1213: '              {models?.length === 0 ? <span style={{ fontSize: \'0.9rem\', color: \'gray\', gridColumn: \'1 / -1\' }}>暂无模型，请在下方添加</span> : null}',
    1255: '                        title="点击重命名别名"',
    1257: '                          {m.alias || "未命名模型"}',
    1281: '                  系统将根据 API Key 的格式自动识别所属平台 (支持 OpenAI, Gemini, DeepSeek, Zhipu 等)。',
    1328: '              确定要清空当前会话的历史记录吗？此操作无法撤销。'
}

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'r', 'utf-8', errors='ignore') as f:
    lines = f.readlines()

for num, text in replacements.items():
    lines[num-1] = text + '\n'

with codecs.open('g:/Ai Multi Agent/frontend/src/App.jsx', 'w', 'utf-8') as f:
    f.writelines(lines)
print('Fixed all moji-bake lines!')
