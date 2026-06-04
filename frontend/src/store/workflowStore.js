import { create } from 'zustand';
import { addEdge, applyEdgeChanges, applyNodeChanges, MarkerType } from '@xyflow/react';

const DEFAULT_NODE_COLOR = '#4da3ff';

const BUILTIN_AGENT_META = {
  AiMultiAgentCore: {
    name: 'Ai Multi Agent 深思节点',
    description: '负责复杂问题拆解、架构推理、反思校验与最终决策。',
    color: '#b142ff',
    icon: 'brain',
    stage: 'analysis',
    inputFields: ['requirement', 'context'],
    outputFields: ['reasoning_result', 'decision'],
  },
  NPU: {
    name: 'NPU 高速节点',
    description: '处理轻量结构化任务、意图命中、系统状态读取等快速动作。',
    color: '#1a73e8',
    icon: 'zap',
    stage: 'execution',
    inputFields: ['input'],
    outputFields: ['npu_result'],
  },
  GPU: {
    name: 'GPU 本地生成节点',
    description: '使用本地模型进行生成、改写、拟人化表达和快速草稿输出。',
    color: '#0f9d58',
    icon: 'sparkles',
    stage: 'generation',
    inputFields: ['prompt'],
    outputFields: ['gpu_response'],
  },
  WebSearch: {
    name: '联网搜索节点',
    description: '负责搜索资料、核验事实、整理引用信息。',
    color: '#4facfe',
    icon: 'search',
    stage: 'research',
    inputFields: ['query'],
    outputFields: ['search_result', 'sources'],
  },
  ProductAgent: {
    name: '产品经理节点',
    description: '负责需求分析、用户故事、范围控制和任务拆解。',
    color: '#ffb347',
    icon: 'user',
    stage: 'analysis',
    inputFields: ['requirement'],
    outputFields: ['product_plan', 'acceptance_criteria'],
  },
  CoderAgent: {
    name: '程序员节点',
    description: '负责实现方案、代码编写、重构和工程落地。',
    color: '#00c781',
    icon: 'code',
    stage: 'implementation',
    inputFields: ['product_plan', 'technical_context'],
    outputFields: ['code_result', 'file_changes'],
  },
  TesterAgent: {
    name: '测试员节点',
    description: '负责测试计划、用例设计、运行验证和缺陷反馈。',
    color: '#ff6b6b',
    icon: 'shield',
    stage: 'testing',
    inputFields: ['code_result', 'acceptance_criteria'],
    outputFields: ['test_result', 'quality_notes'],
  },
};

const SPECIAL_AGENTS = [
  {
    agent_id: 'branch_if',
    name: '条件判断节点',
    description: '根据条件表达式选择 true / false 分支。',
    color: '#fbbc04',
    icon: 'split',
    stage: 'branch',
    nodeType: 'condition',
    inputFields: ['condition', 'input'],
    outputFields: ['true_path', 'false_path'],
  },
  {
    agent_id: 'branch_and',
    name: '并行汇合节点',
    description: '多个上游条件同时满足后继续执行。',
    color: '#f59e0b',
    icon: 'merge',
    stage: 'branch',
    nodeType: 'condition',
    inputFields: ['left', 'right'],
    outputFields: ['and_result'],
  },
  {
    agent_id: 'branch_or',
    name: '任一条件节点',
    description: '任意上游条件满足即可继续执行。',
    color: '#f97316',
    icon: 'split',
    stage: 'branch',
    nodeType: 'condition',
    inputFields: ['left', 'right'],
    outputFields: ['or_result'],
  },
  {
    agent_id: 'human_approval',
    name: '人工审批节点',
    description: '暂停工作流，等待用户批准、拒绝或补充说明。',
    color: '#a78bfa',
    icon: 'shield',
    stage: 'approval',
    nodeType: 'human_approval',
    inputFields: ['approval_context'],
    outputFields: ['approval_result', 'human_comment'],
  },
  {
    agent_id: 'code_agent',
    name: 'CodeAgent 文件节点',
    description: '读写文件、扫描目录、生成审计记录，适合代码工程任务。',
    color: '#60a5fa',
    icon: 'code',
    stage: 'code_ops',
    nodeType: 'code_agent',
    inputFields: ['target_path', 'content', 'instruction'],
    outputFields: ['diff', 'audit_path', 'file_result'],
  },
  {
    agent_id: 'tool_skill',
    name: '系统 Skill 调用节点',
    description: '把 Skills Store 中已注册的工具技能放入工作流中执行。',
    color: '#60a5fa',
    icon: 'wrench',
    stage: 'execution',
    nodeType: 'tool_skill',
    inputFields: ['tool_context'],
    outputFields: ['tool_result', 'success', 'status'],
  },
  {
    agent_id: 'join_and',
    name: 'AND 汇合节点',
    description: '等待多个必要上游分支都完成后再继续执行。',
    color: '#f59e0b',
    icon: 'merge',
    stage: 'branch',
    nodeType: 'join_and',
    inputFields: ['left', 'right'],
    outputFields: ['join_result', 'success'],
  },
  {
    agent_id: 'join_or',
    name: 'OR 汇合节点',
    description: '任一上游分支完成即可继续执行，适合多方案兜底。',
    color: '#fb923c',
    icon: 'merge',
    stage: 'branch',
    nodeType: 'join_or',
    inputFields: ['option_a', 'option_b'],
    outputFields: ['join_result', 'success'],
  },
  {
    agent_id: 'loop_controller',
    name: '循环重试节点',
    description: '配合 loop 连线和 maxIterations 控制失败重试。',
    color: '#f97316',
    icon: 'split',
    stage: 'branch',
    nodeType: 'loop_controller',
    inputFields: ['retry_context'],
    outputFields: ['retry_count', 'success'],
  },
  {
    agent_id: 'custom_agent',
    name: '自定义 Agent 节点',
    description: '可在节点属性中定义角色、任务边界和专属提示词。',
    color: '#94a3b8',
    icon: 'sparkles',
    stage: 'custom',
    nodeType: 'custom_agent',
    inputFields: ['input'],
    outputFields: ['custom_result'],
  },
];

const STAGE_LABELS = {
  all: '全部阶段',
  analysis: '分析',
  research: '检索',
  generation: '生成',
  implementation: '实现',
  testing: '测试',
  execution: '执行',
  branch: '分支',
  approval: '审批',
  code_ops: '文件',
  custom: '自定义',
};

const STAGE_ORDER = {
  analysis: 0,
  research: 1,
  generation: 2,
  implementation: 3,
  testing: 4,
  execution: 5,
  branch: 6,
  approval: 7,
  code_ops: 8,
  custom: 9,
};

let id = 1;
export const createNodeId = (prefix = 'node') => `${prefix}_${Date.now()}_${id++}`;

function defaultFieldsForAgent(agentId = '') {
  const known = BUILTIN_AGENT_META[agentId];
  if (known) {
    return {
      inputs: known.inputFields,
      outputs: known.outputFields,
    };
  }

  const special = SPECIAL_AGENTS.find((agent) => agent.agent_id === agentId);
  if (special) {
    return {
      inputs: special.inputFields,
      outputs: special.outputFields,
    };
  }

  const normalized = String(agentId || 'agent').toLowerCase();
  return {
    inputs: ['input'],
    outputs: [`${normalized}_result`],
  };
}

function normalizeAgent(raw) {
  const agentId = raw.agent_id || raw.key || raw.agentId || 'custom_agent';
  const builtIn = BUILTIN_AGENT_META[agentId] || {};
  const inputs = raw.inputFields || raw.input_fields || builtIn.inputFields;
  const outputs = raw.outputFields || raw.output_fields || builtIn.outputFields;

  return {
    ...raw,
    agent_id: agentId,
    name: builtIn.name || raw.name || agentId,
    description: builtIn.description || raw.description || '',
    color: builtIn.color || raw.color || DEFAULT_NODE_COLOR,
    icon: builtIn.icon || raw.icon || 'user',
    stage: builtIn.stage || raw.stage || 'custom',
    nodeType: raw.nodeType || (agentId === 'code_agent' ? 'code_agent' : agentId === 'human_approval' ? 'human_approval' : agentId === 'tool_skill' || agentId.startsWith('skill:') ? 'tool_skill' : agentId === 'join_and' ? 'join_and' : agentId === 'join_or' ? 'join_or' : agentId === 'loop_controller' ? 'loop_controller' : agentId.startsWith('branch_') ? 'condition' : agentId === 'custom_agent' ? 'custom_agent' : 'agent'),
    inputFields: inputs || defaultFieldsForAgent(agentId).inputs,
    outputFields: outputs || defaultFieldsForAgent(agentId).outputs,
    enabled: raw.enabled ?? true,
  };
}

function createNodeFromAgent(agent, position) {
  const normalized = normalizeAgent(agent);
  const fields = defaultFieldsForAgent(normalized.agent_id);
  const inputFields = normalized.inputFields?.length ? normalized.inputFields : fields.inputs;
  const outputFields = normalized.outputFields?.length ? normalized.outputFields : fields.outputs;

  return {
    id: createNodeId(normalized.agent_id),
    type: 'customAgent',
    position,
    data: {
      label: normalized.name,
      agentId: normalized.agent_id,
      nodeType: normalized.nodeType,
      color: normalized.color,
      icon: normalized.icon,
      stage: normalized.stage,
      enabled: normalized.enabled,
      description: normalized.description,
      role: normalized.role || '',
      instruction: '',
      systemPrompt: '',
      inputFields,
      outputFields,
      condition: normalized.nodeType === 'condition' ? 'success == true' : '',
      codeAgentConfig: normalized.nodeType === 'code_agent'
        ? {
            operation: 'write_file',
            targetPath: 'output/code_agent_demo.txt',
            content: '',
            auditLogPath: 'output/code_agent_audit.jsonl',
            dryRun: true,
          }
        : undefined,
      humanApprovalConfig: normalized.nodeType === 'human_approval'
        ? {
            question: '是否批准继续执行后续节点？',
            approveLabel: '批准继续',
            rejectLabel: '拒绝停止',
            required: true,
          }
        : undefined,
      toolSkillConfig: normalized.nodeType === 'tool_skill'
        ? {
            name: normalized.agent_id.startsWith('skill:') ? normalized.agent_id.slice(6) : '',
            description: normalized.description || '',
            parameters: normalized.parameters || { type: 'object', properties: {} },
          }
        : undefined,
      loopPolicy: normalized.nodeType === 'loop_controller'
        ? { maxIterations: 3, exitCondition: 'success == true' }
        : undefined,
      customAgentMeta: normalized.nodeType === 'custom_agent'
        ? {
            role: '自定义智能体',
            version: '1.0',
            promptRef: '',
          }
        : undefined,
    },
  };
}

function normalizeWorkflowNode(node) {
  if (node.type === 'customAgent' && node.data) {
    return node;
  }

  const data = node.data || {};
  const agentId = data.agentId || data.agent_id || data.agentKey || data.label || 'custom_agent';
  const agent = normalizeAgent({
    agent_id: agentId,
    name: data.label || data.name || agentId,
    description: data.description,
    color: data.color,
    icon: data.icon,
    stage: data.stage,
  });

  return {
    ...node,
    type: 'customAgent',
    data: {
      ...createNodeFromAgent(agent, node.position || { x: 0, y: 0 }).data,
      ...data,
      label: data.label || data.name || agent.name,
      agentId,
    },
  };
}

function edgeDefaults(edge) {
  const data = {
    edgeType: 'control',
    condition: '',
    label: '',
    fromOutputField: '',
    toInputField: '',
    loopPolicy: { maxIterations: 0 },
    ...(edge.data || {}),
  };
  return {
    type: 'smoothstep',
    markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
    style: { strokeWidth: 2 },
    ...edge,
    label: edge.label || data.label || '',
    data,
  };
}

function splitFields(value) {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  return String(value || '')
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

const CONDITION_RE = /^[A-Za-z_][A-Za-z0-9_]*\s*(==|!=|>=|<=|>|<)\s*('[^']*'|"[^"]*"|true|false|null|none|-?\d+(\.\d+)?)$/i;
const CONDITION_FIELDS = new Set(['success', 'test_success', 'approved', 'retry_count', 'max_retry_count', 'quality_score', 'coverage_percent', 'error_log', 'status', 'has_code_blocks']);

function validateConditionExpression(condition) {
  const normalized = String(condition || '').trim();
  if (!normalized || ['always', 'default', 'else'].includes(normalized.toLowerCase())) return '';
  const match = normalized.match(CONDITION_RE);
  if (!match) return '条件只支持白名单字段与常量比较，例如 success == true';
  const field = normalized.split(/\s+/)[0];
  if (!CONDITION_FIELDS.has(field)) return `条件字段不在白名单内：${field}`;
  return '';
}

function validateWorkflow(nodes, edges) {
  const issues = [];
  const nodeIds = new Set(nodes.map((node) => node.id));

  if (!nodes.length) {
    return [{ severity: 'error', title: '没有节点', message: '请先从左侧节点库拖入至少一个 Agent 节点。' }];
  }

  edges.forEach((edge) => {
    const edgeData = edge.data || {};
    const edgeType = edgeData.edgeType || 'control';
    const conditionError = validateConditionExpression(edgeData.condition);
    if (conditionError) {
      issues.push({ severity: 'error', title: '条件表达式不安全', message: conditionError, nodeId: edge.source });
    }
    if (edgeType === 'loop' && Number(edgeData.loopPolicy?.maxIterations || 0) <= 0) {
      issues.push({ severity: 'error', title: '循环缺少上限', message: 'loop 连线必须配置 maxIterations，避免无限循环。', nodeId: edge.source });
    }
    if (!nodeIds.has(edge.source)) {
      issues.push({ severity: 'error', title: '连线起点不存在', message: `连线 ${edge.id} 的起点节点不存在。` });
    }
    if (!nodeIds.has(edge.target)) {
      issues.push({ severity: 'error', title: '连线终点不存在', message: `连线 ${edge.id} 的终点节点不存在。` });
    }
    if (edge.source === edge.target) {
      issues.push({ severity: 'error', title: '节点自连接', message: '节点不能连接到自己。', nodeId: edge.source });
    }
  });

  if (nodes.length > 1) {
    const incoming = new Set(edges.map((edge) => edge.target));
    const outgoing = new Set(edges.map((edge) => edge.source));
    nodes.forEach((node) => {
      if (!incoming.has(node.id) && !outgoing.has(node.id)) {
        issues.push({ severity: 'warning', title: '孤立节点', message: `${node.data?.label || node.id} 还没有连接到工作流。`, nodeId: node.id });
      }
    });
  }

  nodes.forEach((node) => {
    const data = node.data || {};
    const inputFields = splitFields(data.inputFields);
    const outputFields = splitFields(data.outputFields);

    if (!data.label?.trim()) {
      issues.push({ severity: 'error', title: '缺少节点名称', message: '节点显示名称不能为空。', nodeId: node.id });
    }
    if (!inputFields.length) {
      issues.push({ severity: 'warning', title: '缺少输入字段', message: `${data.label || node.id} 没有配置输入字段。`, nodeId: node.id });
    }
    if (!outputFields.length) {
      issues.push({ severity: 'warning', title: '缺少输出字段', message: `${data.label || node.id} 没有配置输出字段。`, nodeId: node.id });
    }
    if (data.nodeType === 'condition' && data.condition && !/^[\w.]+\s*(==|!=|>=|<=|>|<)\s*('[^']*'|"[^"]*"|true|false|null|-?\d+(\.\d+)?)$/i.test(data.condition.trim())) {
      issues.push({ severity: 'error', title: '条件表达式不安全', message: '条件节点只支持字段与常量的简单比较，例如 success == true。', nodeId: node.id });
    }
    if (data.nodeType === 'human_approval' && !data.humanApprovalConfig?.question?.trim()) {
      issues.push({ severity: 'warning', title: '审批问题为空', message: '人工审批节点建议配置清晰的问题文案。', nodeId: node.id });
    }
    if (data.nodeType === 'code_agent' && !data.codeAgentConfig?.targetPath?.trim()) {
      issues.push({ severity: 'error', title: 'CodeAgent 缺少路径', message: 'CodeAgent 文件节点必须配置目标路径。', nodeId: node.id });
    }
    if (data.nodeType === 'custom_agent' && !data.role?.trim() && !data.customAgentMeta?.role?.trim()) {
      issues.push({ severity: 'warning', title: '自定义 Agent 缺少角色', message: '建议为自定义 Agent 指定角色和任务边界。', nodeId: node.id });
    }
  });

  return issues;
}

function autoLayout(nodes) {
  const rows = new Map();
  return nodes.map((node, index) => {
    const stage = node.data?.stage || 'custom';
    const lane = STAGE_ORDER[stage] ?? index;
    const row = rows.get(lane) || 0;
    rows.set(lane, row + 1);
    return {
      ...node,
      position: {
        x: 320 + lane * 280,
        y: 120 + row * 190,
      },
    };
  });
}

export const useWorkflowStore = create((set, get) => ({
  templateId: null,
  title: '新工作流（未命名）',
  description: '',
  stage: 'Draft',
  tags: '',
  author: 'Ai Multi Agent User',

  nodes: [],
  edges: [],
  selectedNodeId: null,
  selectedEdgeId: null,
  isDirty: false,
  agents: SPECIAL_AGENTS.map(normalizeAgent),
  validationIssues: [],

  stageLabels: STAGE_LABELS,

  setMetadata: (meta) => set((state) => ({ ...state, ...meta })),
  setDirty: (dirty) => set({ isDirty: dirty }),

  onNodesChange: (changes) => {
    const hasDirtyChange = changes.some((change) => change.type !== 'select' && change.type !== 'dimensions');
    const nodes = applyNodeChanges(changes, get().nodes);
    set({
      nodes,
      validationIssues: validateWorkflow(nodes, get().edges),
      ...(hasDirtyChange && { isDirty: true }),
    });
  },
  onEdgesChange: (changes) => {
    const hasDirtyChange = changes.some((change) => change.type !== 'select');
    const edges = applyEdgeChanges(changes, get().edges);
    set({
      edges,
      validationIssues: validateWorkflow(get().nodes, edges),
      ...(hasDirtyChange && { isDirty: true }),
    });
  },
  onConnect: (connection) => {
    const edges = addEdge(edgeDefaults(connection), get().edges);
    set({
      edges,
      selectedEdgeId: null,
      validationIssues: validateWorkflow(get().nodes, edges),
      isDirty: true,
    });
  },

  addNode: (nodeOrAgent, position) => {
    const node = position ? createNodeFromAgent(nodeOrAgent, position) : normalizeWorkflowNode(nodeOrAgent);
    const nodes = [...get().nodes, node];
    set({
      nodes,
      selectedNodeId: node.id,
      selectedEdgeId: null,
      validationIssues: validateWorkflow(nodes, get().edges),
      isDirty: true,
    });
  },
  deleteNode: (nodeId) => {
    const nodes = get().nodes.filter((node) => node.id !== nodeId);
    const edges = get().edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId);
    set({
      nodes,
      edges,
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
      validationIssues: validateWorkflow(nodes, edges),
      isDirty: true,
    });
  },
  updateNodeData: (nodeId, dataPatch) => {
    const nodes = get().nodes.map((node) => {
      if (node.id !== nodeId) return node;
      return { ...node, data: { ...node.data, ...dataPatch } };
    });
    set({
      nodes,
      validationIssues: validateWorkflow(nodes, get().edges),
      isDirty: true,
    });
  },
  updateEdgeData: (edgeId, dataPatch) => {
    const edges = get().edges.map((edge) => {
      if (edge.id !== edgeId) return edge;
      return edgeDefaults({ ...edge, label: dataPatch.label || '', data: { ...(edge.data || {}), ...dataPatch } });
    });
    set({
      edges,
      validationIssues: validateWorkflow(get().nodes, edges),
      isDirty: true,
    });
  },
  deleteEdge: (edgeId) => {
    const edges = get().edges.filter((edge) => edge.id !== edgeId);
    set({
      edges,
      selectedEdgeId: get().selectedEdgeId === edgeId ? null : get().selectedEdgeId,
      validationIssues: validateWorkflow(get().nodes, edges),
      isDirty: true,
    });
  },
  setSelectedNodeId: (id) => set({ selectedNodeId: id, selectedEdgeId: null }),
  setSelectedEdgeId: (id) => set({ selectedEdgeId: id, selectedNodeId: null }),

  setAgents: (agents) => {
    const normalized = agents.map(normalizeAgent);
    const byId = new Map([...normalized, ...SPECIAL_AGENTS.map(normalizeAgent)].map((agent) => [agent.agent_id, agent]));
    set({ agents: [...byId.values()] });
  },

  validateWorkflow: () => {
    const issues = validateWorkflow(get().nodes, get().edges);
    set({ validationIssues: issues });
    return issues;
  },
  autoLayout: () => {
    const nodes = autoLayout(get().nodes);
    set({
      nodes,
      validationIssues: validateWorkflow(nodes, get().edges),
      isDirty: true,
    });
  },

  loadWorkflow: (workflowJson, meta = {}) => {
    try {
      const data = typeof workflowJson === 'string' ? JSON.parse(workflowJson) : workflowJson;
      const nodes = (data.nodes || []).map(normalizeWorkflowNode);
      const edges = (data.edges || []).map(edgeDefaults);
      set({
        nodes,
        edges,
        selectedNodeId: null,
        selectedEdgeId: null,
        validationIssues: validateWorkflow(nodes, edges),
        isDirty: false,
        ...meta,
      });
    } catch (e) {
      console.error('Failed to parse workflow JSON', e);
    }
  },
  clearWorkflow: () => {
    set({
      templateId: null,
      title: '新工作流（未命名）',
      description: '',
      stage: 'Draft',
      tags: '',
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      validationIssues: [],
      isDirty: false,
    });
  },

  exportWorkflow: () => {
    const { nodes, edges } = get();
    return JSON.stringify({ nodes, edges }, null, 2);
  },
}));
