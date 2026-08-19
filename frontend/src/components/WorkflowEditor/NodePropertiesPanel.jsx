import { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  MenuItem,
  Paper,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { Trash2 } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore';

const OPERATION_OPTIONS = [
  'read_file',
  'write_file',
  'list_files',
  'scan_folder',
  'read_folder',
  'plan_folder_changes',
  'apply_folder_changes',
];

const selectMenuProps = {
  PaperProps: {
    className: 'workflow-inspector-menu',
  },
};

function fieldsToText(fields) {
  return Array.isArray(fields) ? fields.join('\n') : String(fields || '');
}

function textToFields(value) {
  return String(value || '')
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function NodePropertiesPanel() {
  const { nodes, edges, selectedNodeId, selectedEdgeId, updateNodeData, updateEdgeData, deleteNode, deleteEdge, validationIssues } = useWorkflowStore();
  const selectedNode = nodes.find((node) => node.id === selectedNodeId);
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId);
  const [tab, setTab] = useState('basic');
  const [form, setForm] = useState({});
  const [edgeForm, setEdgeForm] = useState({});

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!selectedNode) {
        setForm({});
        return;
      }

      const data = selectedNode.data || {};
      setForm({
        label: data.label || '', agentId: data.agentId || '', role: data.role || '',
        stage: data.stage || 'custom', enabled: data.enabled ?? true,
        description: data.description || '', instruction: data.instruction || '',
        systemPrompt: data.systemPrompt || '', inputFields: fieldsToText(data.inputFields),
        outputFields: fieldsToText(data.outputFields), condition: data.condition || '',
        codeOperation: data.codeAgentConfig?.operation || 'write_file',
        codeTargetPath: data.codeAgentConfig?.targetPath || 'output/code_agent_demo.txt',
        codeContent: data.codeAgentConfig?.content || '',
        codeAuditPath: data.codeAgentConfig?.auditLogPath || 'output/code_agent_audit.jsonl',
        codeDryRun: data.codeAgentConfig?.dryRun ?? true,
        approvalQuestion: data.humanApprovalConfig?.question || '是否批准继续执行后续节点？',
        approvalApproveLabel: data.humanApprovalConfig?.approveLabel || '批准继续',
        approvalRejectLabel: data.humanApprovalConfig?.rejectLabel || '拒绝停止',
        approvalRequired: data.humanApprovalConfig?.required ?? true,
        customRole: data.customAgentMeta?.role || data.role || '自定义智能体',
        customPromptRef: data.customAgentMeta?.promptRef || '',
        customVersion: data.customAgentMeta?.version || '1.0',
      });
      setTab('basic');
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectedNode]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!selectedEdge) {
        setEdgeForm({});
        return;
      }
      const data = selectedEdge.data || {};
      setEdgeForm({
        edgeType: data.edgeType || 'control', label: data.label || '', condition: data.condition || '',
        fromOutputField: data.fromOutputField || '', toInputField: data.toInputField || '',
        maxIterations: data.loopPolicy?.maxIterations || 0,
      });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectedEdge]);

  const nodeIssues = useMemo(
    () => validationIssues.filter((issue) => issue.nodeId === selectedNodeId),
    [selectedNodeId, validationIssues],
  );

  const inbound = useMemo(
    () => edges.filter((edge) => edge.target === selectedNodeId),
    [edges, selectedNodeId],
  );
  const outbound = useMemo(
    () => edges.filter((edge) => edge.source === selectedNodeId),
    [edges, selectedNodeId],
  );

  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const saveNode = () => {
    if (!selectedNode) return;

    const nodeType = selectedNode.data?.nodeType || 'agent';
    updateNodeData(selectedNode.id, {
      label: form.label?.trim() || selectedNode.data?.label,
      agentId: form.agentId?.trim() || selectedNode.data?.agentId,
      role: form.role?.trim(),
      stage: form.stage?.trim() || 'custom',
      enabled: form.enabled,
      description: form.description?.trim(),
      instruction: form.instruction?.trim(),
      systemPrompt: form.systemPrompt?.trim(),
      inputFields: textToFields(form.inputFields),
      outputFields: textToFields(form.outputFields),
      condition: form.condition?.trim(),
      codeAgentConfig:
        nodeType === 'code_agent'
          ? {
              operation: form.codeOperation,
              targetPath: form.codeTargetPath?.trim(),
              content: form.codeContent || '',
              auditLogPath: form.codeAuditPath?.trim() || 'output/code_agent_audit.jsonl',
              dryRun: Boolean(form.codeDryRun),
            }
          : selectedNode.data?.codeAgentConfig,
      humanApprovalConfig:
        nodeType === 'human_approval'
          ? {
              question: form.approvalQuestion?.trim(),
              approveLabel: form.approvalApproveLabel?.trim() || '批准继续',
              rejectLabel: form.approvalRejectLabel?.trim() || '拒绝停止',
              required: Boolean(form.approvalRequired),
            }
          : selectedNode.data?.humanApprovalConfig,
      customAgentMeta:
        nodeType === 'custom_agent'
          ? {
              role: form.customRole?.trim() || '自定义智能体',
              promptRef: form.customPromptRef?.trim(),
              version: form.customVersion?.trim() || '1.0',
            }
          : selectedNode.data?.customAgentMeta,
    });
  };

  const saveEdge = () => {
    if (!selectedEdge) return;
    updateEdgeData(selectedEdge.id, {
      edgeType: edgeForm.edgeType || 'control',
      label: edgeForm.label?.trim() || '',
      condition: edgeForm.condition?.trim() || '',
      fromOutputField: edgeForm.fromOutputField?.trim() || '',
      toInputField: edgeForm.toInputField?.trim() || '',
      loopPolicy: {
        maxIterations: Number(edgeForm.maxIterations || 0),
      },
    });
  };

  if (!selectedNode && selectedEdge) {
    const sourceNode = nodes.find((node) => node.id === selectedEdge.source);
    const targetNode = nodes.find((node) => node.id === selectedEdge.target);
    return (
      <Paper className="inspector-paper" square>
        <Box className="inspector-title">
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="overline" sx={{ color: 'var(--sys-color-primary)', lineHeight: 1 }}>
              连线属性
            </Typography>
            <Typography variant="h6" noWrap sx={{ color: 'var(--sys-color-on-surface)' }}>
              {sourceNode?.data?.label || selectedEdge.source} → {targetNode?.data?.label || selectedEdge.target}
            </Typography>
          </Box>
          <Chip label={edgeForm.edgeType || 'control'} size="small" variant="outlined" />
        </Box>

        <Box className="inspector-scroll-area">
          <Box className="properties-form">
            <TextField select label="连线类型" size="small" value={edgeForm.edgeType || 'control'} onChange={(event) => setEdgeForm((prev) => ({ ...prev, edgeType: event.target.value }))} SelectProps={{ MenuProps: selectMenuProps }}>
              <MenuItem value="control">control - 顺序执行</MenuItem>
              <MenuItem value="branch">branch - 条件分支</MenuItem>
              <MenuItem value="loop">loop - 循环重试</MenuItem>
              <MenuItem value="data">data - 字段映射</MenuItem>
            </TextField>
            <TextField label="显示标签" size="small" value={edgeForm.label || ''} onChange={(event) => setEdgeForm((prev) => ({ ...prev, label: event.target.value }))} placeholder="例如：成功分支 / 失败重试 / else" />
            <TextField label="条件表达式" size="small" value={edgeForm.condition || ''} onChange={(event) => setEdgeForm((prev) => ({ ...prev, condition: event.target.value }))} placeholder='success == true / status == "failed" / else' helperText="仅支持白名单字段与常量比较；else/default 作为兜底分支。" />
            <TextField label="来源输出字段" size="small" value={edgeForm.fromOutputField || ''} onChange={(event) => setEdgeForm((prev) => ({ ...prev, fromOutputField: event.target.value }))} placeholder="from output field" />
            <TextField label="目标输入字段" size="small" value={edgeForm.toInputField || ''} onChange={(event) => setEdgeForm((prev) => ({ ...prev, toInputField: event.target.value }))} placeholder="to input field" />
            {edgeForm.edgeType === 'loop' && (
              <TextField label="最大循环次数" type="number" size="small" value={edgeForm.maxIterations || 0} onChange={(event) => setEdgeForm((prev) => ({ ...prev, maxIterations: event.target.value }))} helperText="loop 连线必须配置大于 0 的上限，避免无限循环。" />
            )}
          </Box>
        </Box>

        <Box className="inspector-actions-bottom">
          <Button variant="outlined" color="error" startIcon={<Trash2 size={16} />} onClick={() => deleteEdge(selectedEdge.id)}>
            删除连线
          </Button>
          <Button variant="contained" onClick={saveEdge}>
            保存连线
          </Button>
        </Box>
      </Paper>
    );
  }

  if (!selectedNode) {
    return (
      <Paper className="inspector-paper" square>
        <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)', textAlign: 'center', mt: 4 }}>
          选择一个节点后，可以配置角色、输入输出、自定义提示词和审批规则。
        </Typography>
      </Paper>
    );
  }

  const nodeType = selectedNode.data?.nodeType || 'agent';

  return (
    <Paper className="inspector-paper" square>
      <Box className="inspector-title">
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="overline" sx={{ color: 'var(--sys-color-primary)', lineHeight: 1 }}>
            节点属性
          </Typography>
          <Typography variant="h6" noWrap sx={{ color: 'var(--sys-color-on-surface)' }}>
            {selectedNode.data?.label}
          </Typography>
        </Box>
        <Chip label={selectedNode.data?.agentId || 'agent'} size="small" variant="outlined" />
      </Box>

      <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto" className="node-tabs">
        <Tab label="基础" value="basic" />
        <Tab label="输入输出" value="io" />
        <Tab label="映射" value="mapping" />
        {nodeType === 'code_agent' && <Tab label="Code" value="code" />}
        {nodeType === 'human_approval' && <Tab label="审批" value="approval" />}
        {nodeType === 'custom_agent' && <Tab label="自定义" value="custom" />}
        <Tab label="检查" value="check" />
      </Tabs>

      <Box className="inspector-scroll-area">
        {tab === 'basic' && (
          <Box className="properties-form">
            <TextField label="节点显示名称" size="small" value={form.label || ''} onChange={(event) => setField('label', event.target.value)} />
            <TextField label="Agent Key" size="small" value={form.agentId || ''} onChange={(event) => setField('agentId', event.target.value)} disabled={nodeType !== 'custom_agent'} />
            <TextField label="角色定位" size="small" value={form.role || ''} onChange={(event) => setField('role', event.target.value)} placeholder="例如：只负责需求澄清的产品经理" />
            <TextField label="执行阶段" size="small" value={form.stage || ''} onChange={(event) => setField('stage', event.target.value)} placeholder="analysis / implementation / testing" />
            <FormControlLabel
              control={<Switch checked={Boolean(form.enabled)} onChange={(event) => setField('enabled', event.target.checked)} />}
              label={form.enabled ? '启用节点' : '禁用节点'}
            />
            <TextField label="节点说明" multiline minRows={3} size="small" value={form.description || ''} onChange={(event) => setField('description', event.target.value)} />
            <TextField label="额外指令" multiline minRows={4} size="small" value={form.instruction || ''} onChange={(event) => setField('instruction', event.target.value)} placeholder="例如：只输出验收标准，不写代码。" />
            <TextField label="系统提示词覆盖" multiline minRows={4} size="small" value={form.systemPrompt || ''} onChange={(event) => setField('systemPrompt', event.target.value)} placeholder="留空则使用 天韬（SkyT） 默认节点执行提示。" />
          </Box>
        )}

        {tab === 'io' && (
          <Box className="properties-form">
            <TextField label="输入字段" multiline minRows={5} size="small" value={form.inputFields || ''} onChange={(event) => setField('inputFields', event.target.value)} helperText="每行一个字段，也可以用逗号分隔。" />
            <TextField label="输出字段" multiline minRows={5} size="small" value={form.outputFields || ''} onChange={(event) => setField('outputFields', event.target.value)} helperText="这些字段会保存在模板 JSON 中，供后续运行器识别。" />
            {nodeType === 'condition' && (
              <TextField label="条件表达式" size="small" value={form.condition || ''} onChange={(event) => setField('condition', event.target.value)} placeholder="success == true" />
            )}
          </Box>
        )}

        {tab === 'mapping' && (
          <Box className="mapping-stack">
            <section>
              <Typography variant="subtitle2">上游输入</Typography>
              {inbound.length ? inbound.map((edge) => (
                <div className="mapping-row" key={edge.id}>
                  <span>{nodes.find((node) => node.id === edge.source)?.data?.label || edge.source}</span>
                  <b>到</b>
                  <span>{selectedNode.data?.label}</span>
                </div>
              )) : <p className="muted-text">暂无上游连线。</p>}
            </section>
            <Divider />
            <section>
              <Typography variant="subtitle2">下游输出</Typography>
              {outbound.length ? outbound.map((edge) => (
                <div className="mapping-row" key={edge.id}>
                  <span>{selectedNode.data?.label}</span>
                  <b>到</b>
                  <span>{nodes.find((node) => node.id === edge.target)?.data?.label || edge.target}</span>
                </div>
              )) : <p className="muted-text">暂无下游连线。</p>}
            </section>
          </Box>
        )}

        {tab === 'code' && (
          <Box className="properties-form">
            <TextField select label="operation" size="small" value={form.codeOperation || 'write_file'} onChange={(event) => setField('codeOperation', event.target.value)} SelectProps={{ MenuProps: selectMenuProps }}>
              {OPERATION_OPTIONS.map((option) => <MenuItem key={option} value={option}>{option}</MenuItem>)}
            </TextField>
            <TextField label="target_path" size="small" value={form.codeTargetPath || ''} onChange={(event) => setField('codeTargetPath', event.target.value)} />
            <TextField label="content" multiline minRows={5} size="small" value={form.codeContent || ''} onChange={(event) => setField('codeContent', event.target.value)} />
            <TextField label="audit_log_path" size="small" value={form.codeAuditPath || ''} onChange={(event) => setField('codeAuditPath', event.target.value)} />
            <FormControlLabel
              control={<Switch checked={Boolean(form.codeDryRun)} onChange={(event) => setField('codeDryRun', event.target.checked)} />}
              label={form.codeDryRun ? 'dry-run 预演' : '允许写入'}
            />
          </Box>
        )}

        {tab === 'approval' && (
          <Box className="properties-form">
            <TextField label="询问内容" multiline minRows={3} size="small" value={form.approvalQuestion || ''} onChange={(event) => setField('approvalQuestion', event.target.value)} />
            <TextField label="批准按钮文案" size="small" value={form.approvalApproveLabel || ''} onChange={(event) => setField('approvalApproveLabel', event.target.value)} />
            <TextField label="拒绝按钮文案" size="small" value={form.approvalRejectLabel || ''} onChange={(event) => setField('approvalRejectLabel', event.target.value)} />
            <FormControlLabel
              control={<Switch checked={Boolean(form.approvalRequired)} onChange={(event) => setField('approvalRequired', event.target.checked)} />}
              label={form.approvalRequired ? '必须确认' : '可跳过'}
            />
          </Box>
        )}

        {tab === 'custom' && (
          <Box className="properties-form">
            <TextField label="自定义角色" size="small" value={form.customRole || ''} onChange={(event) => setField('customRole', event.target.value)} />
            <TextField label="Prompt 模板引用" size="small" value={form.customPromptRef || ''} onChange={(event) => setField('customPromptRef', event.target.value)} placeholder="prompts/my_custom_agent.md" />
            <TextField label="版本" size="small" value={form.customVersion || ''} onChange={(event) => setField('customVersion', event.target.value)} />
          </Box>
        )}

        {tab === 'check' && (
          <Box className="mapping-stack">
            {nodeIssues.length ? nodeIssues.map((issue, index) => (
              <div className={`issue-card ${issue.severity}`} key={`${issue.title}-${index}`}>
                <strong>{issue.title}</strong>
                <span>{issue.message}</span>
              </div>
            )) : <p className="muted-text">当前节点暂无风险提醒。</p>}
          </Box>
        )}
      </Box>

      <Box className="inspector-actions-bottom">
        <Button variant="outlined" color="error" startIcon={<Trash2 size={16} />} onClick={() => deleteNode(selectedNode.id)}>
          删除节点
        </Button>
        <Button variant="contained" onClick={saveNode}>
          保存修改
        </Button>
      </Box>
    </Paper>
  );
}
