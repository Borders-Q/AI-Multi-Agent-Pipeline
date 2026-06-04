import React from 'react';
import { Trash2 } from 'lucide-react';
import BaseIconButton from './ui/BaseIconButton';
import { zh } from '../i18n/zh';

function formatSessionTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export default function SessionItem({ session, active, onSelect, onDelete }) {
  const title = session.title || zh.sidebar.emptySession;

  return (
    <div className={`session-item ${active ? 'active' : ''}`}>
      <button className="session-main" type="button" onClick={onSelect} aria-current={active ? 'page' : undefined}>
        <strong>{title}</strong>
        <span>{formatSessionTime(session.created_at)}</span>
      </button>
      <BaseIconButton
        className="session-delete"
        label={zh.sidebar.deleteSession}
        tooltip={zh.sidebar.deleteSession}
        tooltipSide="right"
        onClick={(event) => {
          event.stopPropagation();
          onDelete();
        }}
      >
        <Trash2 size={14} />
      </BaseIconButton>
    </div>
  );
}
