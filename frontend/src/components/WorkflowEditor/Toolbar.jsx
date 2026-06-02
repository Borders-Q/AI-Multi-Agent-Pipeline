import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ArrowLeft, CheckCircle2, LayoutGrid, Save, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useWorkflowStore } from '../../store/workflowStore';

export default function Toolbar() {
  const darkTheme = createTheme({
    palette: {
      mode: 'dark',
      background: { paper: '#1e1e2e', default: '#11111b' },
      primary: { main: '#4da3ff' },
    },
  });

  const navigate = useNavigate();
  const {
    templateId,
    title,
    description,
    stage,
    tags,
    exportWorkflow,
    setMetadata,
    isDirty,
    setDirty,
    validateWorkflow,
    autoLayout,
    validationIssues,
  } = useWorkflowStore();

  const [saving, setSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastSeverity, setToastSeverity] = useState('success');
  const [openSettings, setOpenSettings] = useState(false);
  const [showExitConfirm, setShowExitConfirm] = useState(false);

  const [formTitle, setFormTitle] = useState(title);
  const [formDesc, setFormDesc] = useState(description);
  const [formTags, setFormTags] = useState(tags);
  const [formStage, setFormStage] = useState(stage);

  useEffect(() => {
    setFormTitle(title);
    setFormDesc(description);
    setFormTags(tags);
    setFormStage(stage);
  }, [title, description, tags, stage]);

  const showToast = (message, severity = 'success') => {
    setToastMessage(message);
    setToastSeverity(severity);
  };

  const handleSave = async () => {
    const issues = validateWorkflow();
    const hasErrors = issues.some((issue) => issue.severity === 'error');
    if (hasErrors) {
      showToast('工作流还有错误，请先处理红色检查项。', 'error');
      return;
    }

    setSaving(true);
    const json = exportWorkflow();
    const saveId = templateId || `tmpl_${Date.now()}`;

    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/workflows/templates/${saveId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formTitle || '未命名工作流',
          description: formDesc,
          stage: formStage || 'Draft',
          tags: formTags,
          author: 'Ai Multi Agent User',
          workflow_json: json,
        }),
      });
      if (!res.ok) throw new Error('保存失败');
      setMetadata({ templateId: saveId, title: formTitle || '未命名工作流', description: formDesc, stage: formStage || 'Draft', tags: formTags });
      setDirty(false);
      showToast('工作流模板已保存。');
    } catch (e) {
      showToast(`保存失败：${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const errorCount = validationIssues.filter((issue) => issue.severity === 'error').length;
  const warningCount = validationIssues.filter((issue) => issue.severity !== 'error').length;

  return (
    <Box className="workflow-toolbar">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0 }}>
        <IconButton onClick={() => (isDirty ? setShowExitConfirm(true) : navigate('/workflows'))} sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
          <ArrowLeft size={20} />
        </IconButton>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h6" fontWeight="bold" noWrap sx={{ color: 'var(--sys-color-on-surface)', lineHeight: 1.2 }}>
            {title}
          </Typography>
          <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)' }}>
            {templateId ? `ID: ${templateId}` : '未保存模板'} / {stage}
            {isDirty ? ' / 有未保存修改' : ''}
          </Typography>
        </Box>
      </Box>

      <Box className="toolbar-status">
        <span className={errorCount ? 'danger' : 'ok'}>
          {errorCount ? `${errorCount} 错误` : '无错误'}
        </span>
        <span>{warningCount} 提醒</span>
      </Box>

      <Box sx={{ display: 'flex', gap: 1.2, alignItems: 'center' }}>
        <Button variant="outlined" startIcon={<CheckCircle2 size={17} />} onClick={() => validateWorkflow()} sx={{ borderRadius: '18px' }}>
          检查
        </Button>
        <Button variant="outlined" startIcon={<LayoutGrid size={17} />} onClick={autoLayout} sx={{ borderRadius: '18px' }}>
          自动整理
        </Button>
        <Button variant="outlined" startIcon={<Settings size={17} />} onClick={() => setOpenSettings(true)} sx={{ borderRadius: '18px' }}>
          模板属性
        </Button>
        <Button variant="contained" startIcon={<Save size={17} />} onClick={handleSave} disabled={saving} sx={{ borderRadius: '18px', fontWeight: 'bold' }}>
          {saving ? '保存中...' : '保存模板'}
        </Button>
      </Box>

      <ThemeProvider theme={darkTheme}>
        <Dialog open={openSettings} onClose={() => setOpenSettings(false)} maxWidth="sm" fullWidth>
          <DialogTitle>模板属性</DialogTitle>
          <DialogContent sx={{ display: 'grid', gap: 2, pt: 2 }}>
            <TextField label="标题" fullWidth value={formTitle} onChange={(event) => setFormTitle(event.target.value)} />
            <TextField label="描述" fullWidth multiline rows={3} value={formDesc} onChange={(event) => setFormDesc(event.target.value)} />
            <TextField label="标签（逗号分隔）" fullWidth value={formTags} onChange={(event) => setFormTags(event.target.value)} />
            <TextField label="阶段" fullWidth value={formStage} onChange={(event) => setFormStage(event.target.value)} helperText="例如 Draft / Published / Demo" />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenSettings(false)}>取消</Button>
            <Button
              onClick={() => {
                setMetadata({ title: formTitle || '未命名工作流', description: formDesc, stage: formStage || 'Draft', tags: formTags });
                setOpenSettings(false);
                setDirty(true);
              }}
              variant="contained"
            >
              应用
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={showExitConfirm} onClose={() => setShowExitConfirm(false)} maxWidth="xs" fullWidth>
          <DialogTitle>确认离开编辑器？</DialogTitle>
          <DialogContent sx={{ pt: 2 }}>
            <Typography variant="body1">当前工作流有未保存修改，离开后这些修改不会写入模板库。</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowExitConfirm(false)} sx={{ fontWeight: 'bold' }}>继续编辑</Button>
            <Button onClick={() => navigate('/workflows')} variant="contained" color="error" sx={{ fontWeight: 'bold' }}>
              离开
            </Button>
          </DialogActions>
        </Dialog>
      </ThemeProvider>

      <Snackbar open={Boolean(toastMessage)} autoHideDuration={3000} onClose={() => setToastMessage('')} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <Alert onClose={() => setToastMessage('')} severity={toastSeverity} sx={{ width: '100%' }}>
          {toastMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
