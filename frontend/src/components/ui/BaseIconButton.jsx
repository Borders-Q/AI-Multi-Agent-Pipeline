import React from 'react';
import AppTooltip from './AppTooltip';

export default function BaseIconButton({
  label,
  tooltip = label,
  children,
  className = '',
  active = false,
  disabled = false,
  type = 'button',
  tooltipSide = 'top',
  ...props
}) {
  return (
    <AppTooltip label={tooltip} side={tooltipSide} disabled={disabled}>
      <button
        {...props}
        type={type}
        aria-label={label}
        disabled={disabled}
        className={`icon-button base-icon-button ${active ? 'active' : ''} ${className}`}
      >
        {children}
      </button>
    </AppTooltip>
  );
}
