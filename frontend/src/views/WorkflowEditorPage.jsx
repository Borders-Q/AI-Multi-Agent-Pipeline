import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Box } from '@mui/material';
import { Search, SlidersHorizontal } from 'lucide-react';
import { useWorkflowStore } from '../store/workflowStore';
import Toolbar from '../components/WorkflowEditor/Toolbar';
import NodePropertiesPanel from '../components/WorkflowEditor/NodePropertiesPanel';
import CustomAgentNode from '../components/WorkflowEditor/CustomAgentNode';
import '../components/WorkflowEditor.css';

const nodeTypes = {
  customAgent: CustomAgentNode,
};

function stageClass(agent) {
  if (agent.nodeType === 'condition') return 'branch';
  if (agent.nodeType === 'human_approval') return 'approval';
  if (agent.nodeType === 'code_agent') return 'code';
  if (agent.nodeType === 'custom_agent') return 'custom';
  return '';
}

function EditorCanvas() {
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition } = useReactFlow();
  const {
    nodes,
    edges,
    agents,
    stageLabels,
    validationIssues,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    setSelectedNodeId,
    setSelectedEdgeId,
  } = useWorkflowStore();

  const [paletteCollapsed, setPaletteCollapsed] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [stageFilter, setStageFilter] = useState('all');

  const stageOptions = useMemo(() => {
    const stages = new Set(agents.map((agent) => agent.stage || 'custom'));
    return ['all', ...Array.from(stages)];
  }, [agents]);

  const filteredAgents = useMemo(() => {
    const lowerKeyword = keyword.trim().toLowerCase();
    return agents.filter((agent) => {
      if (stageFilter !== 'all' && agent.stage !== stageFilter) return false;
      if (!lowerKeyword) return true;
      return `${agent.name} ${agent.agent_id} ${agent.description} ${agent.stage}`.toLowerCase().includes(lowerKeyword);
    });
  }, [agents, keyword, stageFilter]);

  const issueSummary = useMemo(() => {
    const errors = validationIssues.filter((issue) => issue.severity === 'error').length;
    const warnings = validationIssues.filter((issue) => issue.severity !== 'error').length;
    return { errors, warnings };
  }, [validationIssues]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const raw = event.dataTransfer.getData('application/reactflow');
      if (!raw) return;

      const agentData = JSON.parse(raw);
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      addNode(agentData, position);
    },
    [screenToFlowPosition, addNode],
  );

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes, edges: selectedEdges }) => {
      if (selectedNodes.length === 1) {
        setSelectedNodeId(selectedNodes[0].id);
        return;
      }
      if (selectedEdges.length === 1) {
        setSelectedEdgeId(selectedEdges[0].id);
        return;
      }
      setSelectedNodeId(null);
    },
    [setSelectedEdgeId, setSelectedNodeId],
  );

  return (
    <Box className="workflow-editor-shell">
      <aside className={`floating-palette ${paletteCollapsed ? 'collapsed' : ''}`}>
        <button className="palette-toggle" type="button" onClick={() => setPaletteCollapsed(!paletteCollapsed)}>
          <SlidersHorizontal size={14} />
          <span>{paletteCollapsed ? '展开' : '收起'}</span>
        </button>

        {paletteCollapsed ? (
          <div className="palette-rail">
            <strong>节点库</strong>
            <span>{filteredAgents.length}</span>
          </div>
        ) : (
          <div className="palette-content">
            <div className="palette-head">
              <div>
                <strong>Agent 节点库</strong>
                <span>拖入画布，编排 Ai Multi Agent 工作流</span>
              </div>
              <span className="palette-count">{filteredAgents.length} 个</span>
            </div>

            <div className="palette-filters">
              <label className="palette-search">
                <Search size={14} />
                <input
                  type="text"
                  placeholder="搜索节点"
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                />
              </label>
              <select value={stageFilter} onChange={(event) => setStageFilter(event.target.value)}>
                {stageOptions.map((stage) => (
                  <option key={stage} value={stage}>
                    {stageLabels[stage] || stage}
                  </option>
                ))}
              </select>
            </div>

            <div className="palette-list">
              {filteredAgents.map((agent) => (
                <article
                  key={agent.agent_id}
                  className={`palette-agent ${stageClass(agent)}`}
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.setData('application/reactflow', JSON.stringify(agent));
                    event.dataTransfer.effectAllowed = 'copy';
                  }}
                  style={agent.color ? { borderColor: `${agent.color}88` } : undefined}
                >
                  <div className="palette-agent-main">
                    <strong>{agent.name}</strong>
                    <span>{stageLabels[agent.stage] || agent.stage} / {agent.agent_id}</span>
                  </div>
                  <em>{agent.enabled ? '启用' : '禁用'}</em>
                  <p>{agent.description || '暂无说明'}</p>
                </article>
              ))}
            </div>
          </div>
        )}
      </aside>

      <Box ref={reactFlowWrapper} sx={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onSelectionChange={onSelectionChange}
          nodeTypes={nodeTypes}
          fitView
          colorMode="dark"
        >
          <Controls />
          <Background color="#334155" gap={18} />
        </ReactFlow>

        {(issueSummary.errors > 0 || issueSummary.warnings > 0) && (
          <div className="validation-float">
            <strong>流程检查</strong>
            <span>{issueSummary.errors} 个错误 / {issueSummary.warnings} 个提醒</span>
          </div>
        )}
      </Box>

      <NodePropertiesPanel />
    </Box>
  );
}

export default function WorkflowEditorPage() {
  const { setAgents, validateWorkflow } = useWorkflowStore();

  useEffect(() => {
    fetch(`http://${window.location.hostname}:8000/api/agents`)
      .then((res) => res.json())
      .then((data) => {
        if (data.agents) setAgents(data.agents);
      })
      .catch(() => {
        setAgents([]);
      });
  }, [setAgents]);

  useEffect(() => {
    validateWorkflow();
  }, [validateWorkflow]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', bgcolor: 'var(--sys-color-background)' }}>
      <Toolbar />
      <Box sx={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <ReactFlowProvider>
          <EditorCanvas />
        </ReactFlowProvider>
      </Box>
    </Box>
  );
}
