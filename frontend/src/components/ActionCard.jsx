import React from 'react';

export default function ActionCard({ icon, label, description, active, loading, disabled, onClick }) {
  return (
    <button
      type="button"
      className={`action-card ${active ? 'active' : ''} ${loading ? 'loading' : ''}`}
      disabled={disabled || loading}
      onClick={onClick}
      aria-pressed={active}
    >
      <span className="action-card-icon">{icon}</span>
      <span className="action-card-copy">
        <strong>{label}</strong>
        <em>{description}</em>
      </span>
      {loading && <span className="action-card-spinner" />}
    </button>
  );
}
