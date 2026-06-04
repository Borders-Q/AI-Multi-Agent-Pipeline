import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { Blocks, Bot, Download, FileText, GitBranch, History, Play, RefreshCw, Search, Settings, Sparkles } from 'lucide-react';
import { useWorkflowStore } from '../store/workflowStore';

const API_BASE = `http://${window.location.hostname}:8000`;

const pageSx = {
  p: 4,
  height: '100%',
  overflowY: 'auto',
  bgcolor: 'var(--sys-color-background)',
  color: 'var(--sys-color-on-surface)',
  '& .MuiCard-root': {
    backgroundImage: 'none',
  },
  '& .MuiChip-root': {
    color: 'var(--sys-color-on-surface)',
    borderColor: 'var(--sys-color-surface-variant)',
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  '& .MuiChip-icon': {
    color: 'inherit',
  },
  '& .MuiOutlinedInput-root': {
    color: 'var(--sys-color-on-surface)',
    backgroundColor: 'var(--sys-color-surface)',
    borderRadius: '14px',
  },
  '& .MuiOutlinedInput-notchedOutline': {
    borderColor: 'var(--sys-color-surface-variant)',
  },
  '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline': {
    borderColor: 'var(--sys-color-primary)',
  },
  '& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline': {
    borderColor: 'var(--sys-color-primary)',
  },
  '& .MuiInputBase-input, & .MuiSelect-select': {
    color: 'var(--sys-color-on-surface)',
  },
  '& .MuiInputBase-input::placeholder, & textarea::placeholder': {
    color: 'var(--sys-color-on-surface-variant)',
    opacity: 1,
  },
  '& .MuiSvgIcon-root': {
    color: 'var(--sys-color-on-surface-variant)',
  },
  '& .MuiButton-outlined': {
    color: 'var(--sys-color-on-surface)',
    borderColor: 'var(--sys-color-surface-variant)',
  },
  '& .MuiButton-root': {
    textTransform: 'none',
  },
  '& .MuiAlert-root': {
    backgroundColor: 'rgba(83, 140, 255, 0.12)',
    color: 'var(--sys-color-on-surface)',
    border: '1px solid var(--sys-color-surface-variant)',
  },
};

const selectMenuProps = {
  PaperProps: {
    sx: {
      bgcolor: 'var(--sys-color-surface)',
      color: 'var(--sys-color-on-surface)',
      border: '1px solid var(--sys-color-surface-variant)',
      '& .MuiMenuItem-root': {
        color: 'var(--sys-color-on-surface)',
      },
      '& .MuiMenuItem-root.Mui-selected': {
        bgcolor: 'rgba(83, 140, 255, 0.18)',
      },
      '& .MuiMenuItem-root:hover': {
        bgcolor: 'rgba(255,255,255,0.08)',
      },
    },
  },
};

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function tagsFor(template) {
  return String(template.tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function chipColor(flag) {
  return flag ? 'success' : 'default';
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(response, fallback) {
  const header = response.headers.get('Content-Disposition') || '';
  const match = header.match(/filename="?([^"]+)"?/i);
  return match?.[1] || fallback;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result || '');
      resolve(value.includes(',') ? value.split(',').pop() : value);
    };
    reader.onerror = () => reject(reader.error || new Error('读取文件失败'));
    reader.readAsDataURL(file);
  });
}

export default function Workflows({ sessionId = 'default', onRunWorkflowTemplate, workspacePath = '', onBindWorkspace }) {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [requirement, setRequirement] = useState('');
  const [notice, setNotice] = useState('');
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importMode, setImportMode] = useState('trae');
  const [importFile, setImportFile] = useState(null);
  const [installedSkills, setInstalledSkills] = useState([]);
  const [selectedSkillName, setSelectedSkillName] = useState('');
  const [importing, setImporting] = useState(false);

  const loadWorkflow = useWorkflowStore((state) => state.loadWorkflow);
  const clearWorkflow = useWorkflowStore((state) => state.clearWorkflow);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/workflows/templates`);
      if (res.ok) {
        const data = await res.json();
        const nextTemplates = data.templates || [];
        setTemplates(nextTemplates);
        setSelectedTemplate((current) => current || nextTemplates[0] || null);
      }
    } catch (e) {
      console.error('Failed to load templates:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    if (selectedTemplate?.recommended_user_prompt) {
      setRequirement(selectedTemplate.recommended_user_prompt);
    }
  }, [selectedTemplate?.template_id]);

  const stageOptions = useMemo(() => {
    const stages = new Set();
    templates.forEach((template) => {
      if (template.stage) stages.add(template.stage);
    });
    return [...stages].sort();
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    const normKw = keyword.trim().toLowerCase();
    return templates.filter((template) => {
      if (stageFilter !== 'all' && template.stage !== stageFilter) return false;
      if (!normKw) return true;
      return `${template.template_id} ${template.title} ${template.description} ${template.tags} ${template.demo_scene}`.toLowerCase().includes(normKw);
    });
  }, [templates, keyword, stageFilter]);

  const fetchTemplate = async (templateId) => {
    const res = await fetch(`${API_BASE}/api/workflows/templates/${templateId}`);
    if (!res.ok) throw new Error('模板读取失败');
    const data = await res.json();
    return data.template;
  };

  const handleEditTemplate = async (templateId) => {
    try {
      const tmpl = await fetchTemplate(templateId);
      loadWorkflow(tmpl.workflow_json, {
        templateId: tmpl.template_id,
        title: tmpl.title,
        description: tmpl.description,
        stage: tmpl.stage,
        tags: tmpl.tags,
      });
      navigate('/workflows/editor');
    } catch (e) {
      setNotice(`加载模板失败：${e.message}`);
    }
  };

  const handleRunTemplate = async () => {
    if (!selectedTemplate) return;
    setRunning(true);
    setNotice('');
    try {
      const tmpl = await fetchTemplate(selectedTemplate.template_id);
      await fetch(`${API_BASE}/api/sessions/${sessionId}/workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_json: tmpl.workflow_json }),
      });
      const prompt = (requirement || selectedTemplate.recommended_user_prompt || selectedTemplate.demo_scene || selectedTemplate.title).trim();
      await onRunWorkflowTemplate?.(prompt, {
        templateId: selectedTemplate.template_id,
        templateName: selectedTemplate.title,
        requiresWorkspace: selectedTemplate.requires_workspace,
        artifactPolicy: selectedTemplate.artifact_policy,
        previewPolicy: selectedTemplate.preview_policy,
      });
    } catch (e) {
      setNotice(`运行模板失败：${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleCreateNew = () => {
    clearWorkflow();
    navigate('/workflows/editor');
  };

  const openImportDialog = async () => {
    setImportDialogOpen(true);
    if (!installedSkills.length) {
      try {
        const res = await fetch(`${API_BASE}/api/skills`);
        if (res.ok) {
          const data = await res.json();
          const nextSkills = data.skills || [];
          setInstalledSkills(nextSkills);
          setSelectedSkillName((current) => current || nextSkills[0]?.function?.name || '');
        }
      } catch (e) {
        console.error('Failed to load skills:', e);
      }
    }
  };

  const handleImportTraeSkill = async () => {
    if (!importFile) {
      setNotice('请先选择 Trec/SOLO Skill zip、SKILL.md 或 workflow.json 文件。');
      return;
    }
    setImporting(true);
    setNotice('');
    try {
      const contentBase64 = await readFileAsBase64(importFile);
      const res = await fetch(`${API_BASE}/api/workflows/import-trae-skill-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: importFile.name,
          content_base64: contentBase64,
          save: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      await loadTemplates();
      setNotice(`Trec/SOLO Skill 已导入为工作流模板：${data.template_id}${data.warnings?.length ? `；提示：${data.warnings.join('；')}` : ''}`);
      setImportDialogOpen(false);
      setImportFile(null);
    } catch (e) {
      setNotice(`导入 Trec/SOLO Skill 失败：${e.message}`);
    } finally {
      setImporting(false);
    }
  };

  const handleSystemSkillToTemplate = async () => {
    if (!selectedSkillName) {
      setNotice('请先选择一个已安装系统技能。');
      return;
    }
    setImporting(true);
    setNotice('');
    try {
      const res = await fetch(`${API_BASE}/api/workflows/skills/${encodeURIComponent(selectedSkillName)}/to-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      await loadTemplates();
      setNotice(`系统技能已转换为工作流模板：${data.template_id}`);
      setImportDialogOpen(false);
    } catch (e) {
      setNotice(`系统技能转模板失败：${e.message}`);
    } finally {
      setImporting(false);
    }
  };

  const handleExportTemplateSkill = async (mode) => {
    if (!selectedTemplate) return;
    setExporting(true);
    setNotice('');
    try {
      let targetWorkspace = workspacePath;
      if (mode === 'workspace' && !targetWorkspace) {
        targetWorkspace = await onBindWorkspace?.();
      }
      if (mode === 'workspace' && !targetWorkspace) {
        setNotice('导出到工作区前需要先绑定工作区。');
        return;
      }

      const res = await fetch(`${API_BASE}/api/workflows/templates/${selectedTemplate.template_id}/export-trae-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, workspace: targetWorkspace || null }),
      });

      if (mode === 'download') {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const blob = await res.blob();
        downloadBlob(blob, filenameFromDisposition(res, `${selectedTemplate.template_id || 'workflow-skill'}.zip`));
        setNotice('Trec/SOLO Skill 包已生成并开始下载。');
      } else {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        setNotice(`Trec/SOLO Skill 已保存到：${data.target_dir}`);
      }
      setExportDialogOpen(false);
    } catch (e) {
      setNotice(`导出 Trec/SOLO Skill 失败：${e.message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Box sx={pageSx}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="800" gutterBottom sx={{ color: 'var(--sys-color-on-surface)' }}>
            Workflow Templates
          </Typography>
          <Typography variant="body1" sx={{ color: 'var(--sys-color-on-surface-variant)', mb: 2, maxWidth: 860 }}>
            比赛演示型多智能体模板：从任务输入、节点协作、执行过程，到运行历史、深度回放和报告形成闭环。
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`模板数量: ${templates.length}`} color="primary" variant="outlined" />
            <Chip label="多 Agent 协作" color="success" variant="outlined" />
            <Chip label="History / Replay / Reports 闭环" variant="outlined" />
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button variant="outlined" startIcon={<RefreshCw size={18} />} onClick={loadTemplates} disabled={loading} sx={{ borderRadius: '20px' }}>
            刷新
          </Button>
          <Button variant="outlined" startIcon={<Download size={18} />} onClick={openImportDialog} sx={{ borderRadius: '20px', fontWeight: 'bold' }}>
            导入 Skill 为模板
          </Button>
          <Button variant="contained" color="primary" onClick={handleCreateNew} sx={{ borderRadius: '20px', fontWeight: 'bold' }}>
            + 创建新流
          </Button>
        </Box>
      </Box>

      <Divider sx={{ my: 3, borderColor: 'var(--sys-color-surface-variant)' }} />
      {notice && <Alert severity="warning" sx={{ mb: 2 }}>{notice}</Alert>}

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', lg: 'row' } }}>
        <Box sx={{ flex: 1.05, minWidth: { lg: '430px' } }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <Box sx={{ position: 'relative', flex: 1 }}>
              <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.55, zIndex: 1 }} />
              <TextField
                size="small"
                fullWidth
                placeholder="搜索模板名称 / 场景 / 标签..."
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                sx={{
                  bgcolor: 'var(--sys-color-surface)',
                  '& .MuiInputBase-input': {
                    pl: '34px',
                  },
                }}
              />
            </Box>
            <Select
              size="small"
              value={stageFilter}
              onChange={(event) => setStageFilter(event.target.value)}
              MenuProps={selectMenuProps}
              sx={{ minWidth: '150px', bgcolor: 'var(--sys-color-surface)' }}
            >
              <MenuItem value="all">所有阶段</MenuItem>
              {stageOptions.map((stage) => <MenuItem key={stage} value={stage}>{stage}</MenuItem>)}
            </Select>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
          ) : filteredTemplates.length === 0 ? (
            <Alert severity="info">暂无匹配的工作流模板</Alert>
          ) : (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2 }}>
              {filteredTemplates.map((template) => (
                <Card
                  key={template.template_id}
                  onClick={() => setSelectedTemplate(template)}
                  sx={{
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    border: '1px solid',
                    borderColor: selectedTemplate?.template_id === template.template_id ? 'primary.main' : 'var(--sys-color-surface-variant)',
                    boxShadow: selectedTemplate?.template_id === template.template_id ? 4 : 1,
                    bgcolor: 'var(--sys-color-surface)',
                    color: 'var(--sys-color-on-surface)',
                    borderRadius: '12px',
                  }}
                >
                  <CardContent sx={{ p: 2.2, display: 'grid', gap: 1.2, '&:last-child': { pb: 2.2 } }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                      <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.25 }}>
                        {template.title}
                      </Typography>
                      <Chip label={template.stage} size="small" color={template.stage === 'Published' ? 'success' : 'default'} />
                    </Box>
                    <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
                      {template.demo_scene || template.description}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip size="small" icon={<GitBranch size={13} />} label={`${template.node_count || 0} 节点`} variant="outlined" />
                      <Chip size="small" icon={<Bot size={13} />} label={template.whether_gpu_needed ? '需要 GPU' : 'GPU 可选'} color={chipColor(template.whether_gpu_needed)} variant="outlined" />
                      <Chip size="small" icon={<Sparkles size={13} />} label={template.whether_api_needed ? '需要 API' : 'API 可选'} color={chipColor(template.whether_api_needed)} variant="outlined" />
                      <Chip size="small" label={template.requires_workspace ? '需要工作区' : '工作区可选'} color={template.requires_workspace ? 'warning' : 'default'} variant="outlined" />
                      {template.estimated_complexity && <Chip size="small" label={`复杂度 ${template.estimated_complexity}`} variant="outlined" />}
                    </Box>
                    <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      推荐输入：{template.recommended_user_prompt || '选择后可在右侧填写演示需求'}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
                      {tagsFor(template).slice(0, 4).map((tag) => <Chip key={tag} label={tag} size="small" variant="outlined" />)}
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Box>

        <Box sx={{ flex: 1, minWidth: { lg: '430px' } }}>
          {selectedTemplate ? (
            <Card sx={{ bgcolor: 'var(--sys-color-surface)', p: 3, borderRadius: '16px', color: 'var(--sys-color-on-surface)' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, mb: 2 }}>
                <Box>
                  <Typography variant="overline" sx={{ color: 'var(--sys-color-primary)' }}>比赛演示模板</Typography>
                  <Typography variant="h5" fontWeight="bold">{selectedTemplate.title}</Typography>
                </Box>
                <Chip label={selectedTemplate.template_id} color="primary" variant="outlined" />
              </Box>

              <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)', mb: 2 }}>
                {selectedTemplate.competition_demo_value || selectedTemplate.description}
              </Typography>

              <Box sx={{ display: 'grid', gap: 1.2, mb: 2 }}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip icon={<Blocks size={14} />} label={`${selectedTemplate.node_count || 0} 个 Agent 节点`} variant="outlined" />
                  <Chip icon={<History size={14} />} label="可进入运行历史" variant="outlined" />
                  <Chip icon={<FileText size={14} />} label="可生成报告" variant="outlined" />
                  <Chip label={selectedTemplate.requires_workspace ? '运行前绑定工作区' : '默认不强制落盘'} color={selectedTemplate.requires_workspace ? 'warning' : 'default'} variant="outlined" />
                </Box>
                <Typography variant="subtitle2">推荐演示输入</Typography>
                <TextField
                  fullWidth
                  multiline
                  minRows={3}
                  value={requirement}
                  onChange={(event) => setRequirement(event.target.value)}
                  placeholder={selectedTemplate.recommended_user_prompt || '输入本次演示任务...'}
                />
              </Box>

              <Divider sx={{ my: 2, borderColor: 'var(--sys-color-surface-variant)' }} />

              <Typography variant="subtitle2" sx={{ mb: 1 }}>节点分工</Typography>
              <Box sx={{ display: 'grid', gap: 1.1, mb: 2 }}>
                {asList(selectedTemplate.node_list).map((node, index) => (
                  <Box key={`${node.name}-${index}`} sx={{ p: 1.2, border: '1px solid var(--sys-color-surface-variant)', borderRadius: '10px', bgcolor: 'rgba(255,255,255,0.02)' }}>
                    <Typography variant="body2" fontWeight="bold">{index + 1}. {node.name}</Typography>
                    <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>{node.responsibility || node.role}</Typography>
                  </Box>
                ))}
              </Box>

              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.4, mb: 2 }}>
                <Box>
                  <Typography variant="subtitle2">Replay 展示重点</Typography>
                  {asList(selectedTemplate.replay_highlights).map((item) => <Typography key={item} variant="caption" display="block">- {item}</Typography>)}
                </Box>
                <Box>
                  <Typography variant="subtitle2">Report 展示重点</Typography>
                  {asList(selectedTemplate.report_highlights).map((item) => <Typography key={item} variant="caption" display="block">- {item}</Typography>)}
                </Box>
              </Box>

              {selectedTemplate.risk_notes && (
                <Alert severity="info" sx={{ mb: 2 }}>{selectedTemplate.risk_notes}</Alert>
              )}

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={running ? <CircularProgress size={16} /> : <Play size={18} />}
                  fullWidth
                  disabled={running}
                  sx={{ py: 1.4, fontWeight: 'bold' }}
                  onClick={handleRunTemplate}
                >
                  运行此工作流
                </Button>
                <Button
                  variant="outlined"
                  color="primary"
                  startIcon={<Download size={18} />}
                  fullWidth
                  sx={{ py: 1.4, fontWeight: 'bold' }}
                  onClick={() => setExportDialogOpen(true)}
                >
                  导出 Trec/SOLO Skill
                </Button>
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<Settings size={18} />}
                  fullWidth
                  sx={{ py: 1.4, fontWeight: 'bold' }}
                  onClick={() => handleEditTemplate(selectedTemplate.template_id)}
                >
                  在编辑器中打开
                </Button>
              </Box>
            </Card>
          ) : (
            <Alert severity="info">请从左侧选择一个模板查看详情</Alert>
          )}
        </Box>
      </Box>

      <Dialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: 'var(--sys-color-surface)',
            color: 'var(--sys-color-on-surface)',
            border: '1px solid var(--sys-color-surface-variant)',
          },
        }}
      >
        <DialogTitle>导出为 Trec/SOLO Skill</DialogTitle>
        <DialogContent sx={{ display: 'grid', gap: 1.5, pt: 1, color: 'var(--sys-color-on-surface)' }}>
          <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
            将当前工作流模板转换为 Trec/SOLO 可识别的项目级 Skill，结构为 <code>.agents/skills/&lt;skill-name&gt;/SKILL.md</code>。
          </Typography>
          <Typography variant="body2">
            当前模板：{selectedTemplate?.title || '未选择模板'}
          </Typography>
          <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
            已绑定工作区：{workspacePath || '未绑定'}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)} disabled={exporting}>取消</Button>
          <Button onClick={() => handleExportTemplateSkill('workspace')} disabled={exporting} variant="outlined">
            保存到工作区
          </Button>
          <Button onClick={() => handleExportTemplateSkill('download')} disabled={exporting} variant="contained" startIcon={exporting ? <CircularProgress size={15} /> : <Download size={16} />}>
            下载 Skill 包
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: 'var(--sys-color-surface)',
            color: 'var(--sys-color-on-surface)',
            border: '1px solid var(--sys-color-surface-variant)',
          },
        }}
      >
        <DialogTitle>导入 Skill 为工作流模板</DialogTitle>
        <DialogContent sx={{ display: 'grid', gap: 2, pt: 1, color: 'var(--sys-color-on-surface)' }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant={importMode === 'trae' ? 'contained' : 'outlined'} onClick={() => setImportMode('trae')}>
              Trec/SOLO Skill 包
            </Button>
            <Button variant={importMode === 'system' ? 'contained' : 'outlined'} onClick={() => setImportMode('system')}>
              系统技能
            </Button>
          </Box>

          {importMode === 'trae' ? (
            <Box sx={{ display: 'grid', gap: 1.4 }}>
              <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
                支持上传工作流导出的 zip，也支持单独上传 <code>SKILL.md</code> 或 <code>workflow.json</code>。系统只解析文件，不执行 Skill 代码。
              </Typography>
              <Button variant="outlined" component="label">
                选择文件
                <input
                  hidden
                  type="file"
                  accept=".zip,.md,.json"
                  onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                />
              </Button>
              <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
                当前文件：{importFile?.name || '未选择'}
              </Typography>
            </Box>
          ) : (
            <Box sx={{ display: 'grid', gap: 1.4 }}>
              <Typography variant="body2" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
                将 Skills Store 中已注册的工具技能转换成“需求整理 → 技能调用 → 结果总结”的可编辑工作流模板。
              </Typography>
              <Select
                size="small"
                fullWidth
                value={selectedSkillName}
                onChange={(event) => setSelectedSkillName(event.target.value)}
                MenuProps={selectMenuProps}
              >
                {installedSkills.map((skill) => (
                  <MenuItem key={skill.function.name} value={skill.function.name}>
                    {skill.function.name}
                  </MenuItem>
                ))}
              </Select>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportDialogOpen(false)} disabled={importing}>取消</Button>
          <Button
            onClick={importMode === 'trae' ? handleImportTraeSkill : handleSystemSkillToTemplate}
            disabled={importing}
            variant="contained"
            startIcon={importing ? <CircularProgress size={15} /> : <Download size={16} />}
          >
            导入为模板
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
