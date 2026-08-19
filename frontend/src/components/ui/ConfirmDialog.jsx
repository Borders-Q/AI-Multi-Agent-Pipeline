import { AlertTriangle, X } from 'lucide-react';
import BaseIconButton from './BaseIconButton';

export default function ConfirmDialog({
  open,
  heading,
  description,
  confirmLabel = '确认',
  cancelLabel = '取消',
  danger = false,
  onConfirm,
  onCancel
}) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <div className="codex-modal small confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div className="modal-title">
          <span className={`confirm-icon ${danger ? 'danger' : ''}`}><AlertTriangle size={18} /></span>
          <strong id="confirm-title">{heading}</strong>
          <BaseIconButton label="关闭" tooltip="关闭" onClick={onCancel}><X size={18} /></BaseIconButton>
        </div>
        {description && <p className="confirm-description">{description}</p>}
        <div className="modal-actions">
          <button className="codex-button subtle" type="button" onClick={onCancel}>{cancelLabel}</button>
          <button className={`codex-button ${danger ? 'danger' : 'primary'}`} type="button" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
