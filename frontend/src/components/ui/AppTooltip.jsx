export default function AppTooltip({ label, children, side = 'top', disabled = false }) {
  if (!label) return children;

  return (
    <span className={`app-tooltip app-tooltip-${side} ${disabled ? 'disabled' : ''}`}>
      {children}
      {!disabled && (
        <span className="app-tooltip-bubble" role="tooltip">
          {label}
        </span>
      )}
    </span>
  );
}
