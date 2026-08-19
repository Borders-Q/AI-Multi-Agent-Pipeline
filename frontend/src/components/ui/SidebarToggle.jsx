import { ChevronLeft, ChevronRight } from 'lucide-react';
import BaseIconButton from './BaseIconButton';
import { zh } from '../../i18n/zh';

export default function SidebarToggle({ open, onToggle }) {
  return (
    <div className="sidebar-toggle-wrap">
      <BaseIconButton
        className="sidebar-toggle"
        label={open ? zh.sidebar.collapse : zh.sidebar.expand}
        tooltip={open ? zh.sidebar.collapse : zh.sidebar.expand}
        tooltipSide="right"
        onClick={onToggle}
      >
        {open ? <ChevronLeft size={17} /> : <ChevronRight size={17} />}
      </BaseIconButton>
    </div>
  );
}
