import { Handle, Position } from '@xyflow/react';
import { Box, Typography } from '@mui/material';
import {
  Brain,
  Code,
  GitBranch,
  Merge,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  User,
  Wrench,
  Zap,
} from 'lucide-react';

const ICONS = {
  brain: Brain,
  zap: Zap,
  sparkles: Sparkles,
  search: Search,
  user: User,
  code: Code,
  shield: Shield,
  split: GitBranch,
  merge: Merge,
  wrench: Wrench,
  refresh: RefreshCw,
};

const NODE_TYPE_LABELS = {
  agent: 'Agent',
  condition: '条件',
  human_approval: '审批',
  code_agent: '文件',
  custom_agent: '自定义',
  tool_skill: 'Skill',
  join_and: 'AND',
  join_or: 'OR',
  loop_controller: 'Loop',
};

export default function CustomAgentNode({ data, selected }) {
  const color = data.color || '#4da3ff';
  const IconComponent = ICONS[data.icon] || User;
  const typeLabel = NODE_TYPE_LABELS[data.nodeType] || 'Agent';

  return (
    <Box
      sx={{
        bgcolor: 'var(--sys-color-surface)',
        borderRadius: '10px',
        border: '2px solid',
        borderColor: selected ? color : 'rgba(255,255,255,0.08)',
        boxShadow: selected ? `0 0 0 4px ${color}33, 0 16px 30px rgba(0,0,0,0.28)` : '0 10px 24px rgba(0,0,0,0.24)',
        transition: 'all 0.2s ease',
        minWidth: 210,
        overflow: 'hidden',
        opacity: data.enabled === false ? 0.55 : 1,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color, width: 10, height: 10 }} />

      <Box
        sx={{
          bgcolor: `${color}22`,
          p: 1.4,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '8px',
            bgcolor: color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            flex: '0 0 auto',
          }}
        >
          <IconComponent size={15} />
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="subtitle2" fontWeight="bold" noWrap sx={{ color: 'var(--sys-color-on-surface)' }}>
            {data.label}
          </Typography>
          <Typography variant="caption" noWrap sx={{ display: 'block', color: 'var(--sys-color-on-surface-variant)' }}>
            {typeLabel} / {data.stage || 'custom'}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ p: 1.4, display: 'grid', gap: 0.8 }}>
        <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface-variant)', fontFamily: 'monospace' }}>
          {data.agentId}
        </Typography>
        {(data.role || data.customAgentMeta?.role) && (
          <Typography variant="caption" sx={{ color: 'var(--sys-color-on-surface)', lineHeight: 1.35 }}>
            {data.role || data.customAgentMeta?.role}
          </Typography>
        )}
        {data.instruction && (
          <Typography
            variant="caption"
            sx={{
              color: 'var(--sys-color-on-surface-variant)',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              lineHeight: 1.35,
            }}
          >
            {data.instruction}
          </Typography>
        )}
      </Box>

      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 10, height: 10 }} />
    </Box>
  );
}
