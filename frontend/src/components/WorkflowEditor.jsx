import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './WorkflowEditor.css';

const initialNodes = [];
const initialEdges = [];

let id = 1;
const getId = () => `dndnode_${id++}`;

const ALL_AGENTS = [
  // Branch Agents
  { key: "branch_if", name: "If", role: "条件分支节点", description: "根据条件表达式选择 true / false 分支。", stage: "branch", enabled: true, color: '#fbbc04' },
  { key: "branch_and", name: "And", role: "并行汇合节点", description: "要求多个上游条件同时满足后继续执行。", stage: "branch", enabled: true, color: '#fbbc04' },
  { key: "branch_or", name: "Or", role: "任一条件节点", description: "任一上游条件满足即可继续执行。", stage: "branch", enabled: true, color: '#fbbc04' },
  { key: "human_approval", name: "Human Approval", role: "人工确认节点", description: "暂停工作流等待用户批准。", stage: "approval", enabled: true, color: '#a78bfa' },
  { key: "custom_agent", name: "Custom Agent", role: "自定义模板智能体", description: "仅保存到Workflow的可视化节点。", stage: "custom", enabled: true, color: '#94a3b8' },
  
  // Custom Ai Multi Agent agents
  { key: "ProductAgent", name: "产品经理节点", role: "需求分析专家", description: "负责需求分析和拆解", stage: "analysis", enabled: true, color: '#ffb347' },
  { key: "CoderAgent", name: "程序员节点", role: "编码执行者", description: "负责编写代码", stage: "implementation", enabled: true, color: '#00ff9d' },
  { key: "TesterAgent", name: "测试员节点", role: "质量门禁", description: "负责测试代码", stage: "testing", enabled: true, color: '#ff6b6b' },
  { key: "WebSearch", name: "搜索节点", role: "外部资料聚合", description: "负责全网搜索资料", stage: "execution", enabled: true, color: '#4facfe' },
  { key: "AiMultiAgentCore", name: "Ai Multi Agent 深思", role: "反思博弈引擎", description: "深度反思与博弈", stage: "analysis", enabled: true, color: '#b142ff' }
];

const STAGE_OPTIONS = [
  { label: "全部阶段", value: "all" },
  { label: "Analysis", value: "analysis" },
  { label: "Implementation", value: "implementation" },
  { label: "Testing", value: "testing" },
  { label: "Execution", value: "execution" },
  { label: "Branch / Repair", value: "branch" },
  { label: "Approval", value: "approval" },
  { label: "Custom", value: "custom" },
];

function WorkflowEditorContent({ sessionId }) {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [saving, setSaving] = useState(false);
  const [paletteCollapsed, setPaletteCollapsed] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [stageFilter, setStageFilter] = useState('all');

  useEffect(() => {
    if (!sessionId) return;
    
    fetch(`http://127.0.0.1:8000/api/sessions/${sessionId}/workflow`)
      .then(res => res.json())
      .then(data => {
        if (data.workflow_json) {
          try {
            const parsed = JSON.parse(data.workflow_json);
            setNodes(parsed.nodes || []);
            setEdges(parsed.edges || []);
          } catch(e) {
            console.error("Failed to parse workflow_json", e);
          }
        }
      })
      .catch(err => console.error("Error loading workflow:", err));
  }, [sessionId, setNodes, setEdges]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDragStart = (event, agent) => {
    event.dataTransfer.setData('application/reactflow', agent.key);
    event.dataTransfer.setData('application/reactflow-label', agent.name);
    event.dataTransfer.setData('application/reactflow-color', agent.color);
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      
      const type = event.dataTransfer.getData('application/reactflow');
      const label = event.dataTransfer.getData('application/reactflow-label');
      const color = event.dataTransfer.getData('application/reactflow-color') || '#8ab4f8';
      
      if (!type) return;
      
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      
      const newNode = {
        id: getId(),
        type: 'default',
        position,
        data: { label: label, name: label, agentKey: type },
        style: {
          padding: '12px 20px',
          borderRadius: '12px',
          border: `2px solid ${color}`,
          backgroundColor: '#17191f',
          color: '#f4f4f5',
          boxShadow: `0 4px 12px rgba(0,0,0,0.3)`
        }
      };
      
      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );
  
  const saveWorkflow = async () => {
    setSaving(true);
    const flow = reactFlowInstance.toObject();
    try {
      await fetch(`http://127.0.0.1:8000/api/sessions/${sessionId}/workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_json: JSON.stringify(flow) })
      });
    } catch (e) {
      console.error("Failed to save workflow", e);
    }
    setTimeout(() => setSaving(false), 500);
  };

  const filteredAgents = useMemo(() => {
    return ALL_AGENTS.filter(agent => {
      if (stageFilter !== 'all' && agent.stage !== stageFilter) return false;
      if (keyword) {
        const lowerKw = keyword.toLowerCase();
        return agent.name.toLowerCase().includes(lowerKw) || 
               agent.key.toLowerCase().includes(lowerKw) ||
               agent.description.toLowerCase().includes(lowerKw);
      }
      return true;
    });
  }, [keyword, stageFilter]);

  return (
    <div className="workflow-editor-page">
      <div className="editor-workspace" ref={reactFlowWrapper}>
        <aside className={`floating-palette ${paletteCollapsed ? 'collapsed' : ''}`}>
          <button className="palette-toggle" type="button" onClick={() => setPaletteCollapsed(!paletteCollapsed)}>
            <span>{paletteCollapsed ? "展开" : "收起"}</span>
          </button>

          {paletteCollapsed ? (
            <div className="palette-rail">
              <strong>Agents</strong>
              <span>{filteredAgents.length}</span>
            </div>
          ) : (
            <div className="palette-content">
              <div className="palette-head">
                <div>
                  <strong>Agent Palette</strong>
                  <span>拖入画布生成工作流节点</span>
                </div>
                <span style={{color: '#8ab4f8', border: '1px solid #8ab4f8', padding: '2px 6px', borderRadius: '4px', fontSize: '10px'}}>
                  {filteredAgents.length} nodes
                </span>
              </div>

              <div className="palette-filters">
                <input 
                  type="text" 
                  placeholder="搜索节点" 
                  value={keyword} 
                  onChange={e => setKeyword(e.target.value)} 
                />
                <select value={stageFilter} onChange={e => setStageFilter(e.target.value)}>
                  {STAGE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="palette-list">
                {filteredAgents.map(agent => (
                  <article
                    key={agent.key}
                    className={`palette-agent ${agent.stage}`}
                    draggable
                    onDragStart={(e) => onDragStart(e, agent)}
                    style={agent.color ? { borderColor: agent.color } : {}}
                  >
                    <div className="palette-agent-main">
                      <strong>{agent.name}</strong>
                      <span>{agent.stage} · {agent.key}</span>
                    </div>
                    <p>{agent.description}</p>
                  </article>
                ))}
              </div>
            </div>
          )}
        </aside>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
          colorMode="dark"
        >
          <Controls />
          <Background color="#555" gap={16} />
        </ReactFlow>
        
        <button className="save-button" onClick={saveWorkflow}>
          {saving ? '保存中...' : '保存工作流'}
        </button>
      </div>
    </div>
  );
}

export default function WorkflowEditor({ sessionId }) {
  return (
    <ReactFlowProvider>
      <WorkflowEditorContent sessionId={sessionId} />
    </ReactFlowProvider>
  );
}
