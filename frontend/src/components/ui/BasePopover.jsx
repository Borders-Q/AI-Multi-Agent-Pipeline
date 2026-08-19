import { useEffect, useRef } from 'react';

export default function BasePopover({
  open,
  onOpenChange,
  trigger,
  children,
  className = '',
  panelClassName = '',
  align = 'start'
}) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const handlePointerDown = (event) => {
      if (!ref.current?.contains(event.target)) onOpenChange(false);
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onOpenChange(false);
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onOpenChange]);

  return (
    <div className={`base-popover ${className}`} ref={ref}>
      {trigger({ open, toggle: () => onOpenChange(!open) })}
      {open && (
        <div className={`base-popover-panel align-${align} ${panelClassName}`} role="dialog">
          {children}
        </div>
      )}
    </div>
  );
}
