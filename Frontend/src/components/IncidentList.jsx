/**
 * AEGIS — Incident List Component
 * Scrollable list of incidents in the sidebar with severity badges and status.
 */

import { MapPin, Clock, AlertTriangle } from 'lucide-react';

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function SeverityBadge({ severity }) {
  if (!severity) return null;
  return <span className={`badge badge--${severity}`}>{severity}</span>;
}

function StatusBadge({ status }) {
  const statusClass = {
    dispatched: 'success',
    needs_review: 'critical',
    resolved: 'info',
    matched: 'success',
    located: 'info',
    verified: 'info',
    triaged: 'medium',
    new: 'status',
  };
  return <span className={`badge badge--${statusClass[status] || 'status'}`}>{status?.replace('_', ' ')}</span>;
}

function NeedBadge({ needType }) {
  if (!needType) return null;
  const icons = { medical: '🏥', rescue: '🚤', food: '🍞', shelter: '🏠' };
  return <span className="badge badge--status">{icons[needType] || '📋'} {needType}</span>;
}

export default function IncidentList({ incidents, selectedId, onSelectIncident }) {
  if (incidents.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">📭</div>
        <div className="empty-state__text">No incidents yet.<br />Send a simulated SMS to start.</div>
      </div>
    );
  }

  // Sort by created_at descending (newest first)
  const sorted = [...incidents].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  return (
    <div>
      {sorted.map(incident => (
        <div
          key={incident.id}
          className={`card incident-card ${selectedId === incident.id ? 'card--active' : ''} ${incident._isNew ? 'incident-card--new' : ''}`}
          onClick={() => onSelectIncident(incident.id)}
        >
          <div className="incident-card__header">
            <span className="incident-card__id">#{incident.id?.substring(0, 8)}</span>
            <span className="incident-card__id">
              <Clock size={10} style={{ marginRight: 3 }} />
              {formatTime(incident.created_at)}
            </span>
          </div>

          <div className="incident-card__text">{incident.raw_text}</div>

          <div className="incident-card__meta">
            <SeverityBadge severity={incident.severity} />
            <NeedBadge needType={incident.need_type} />
            <StatusBadge status={incident.status} />
          </div>

          {incident.landmark_name && (
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <MapPin size={10} /> {incident.landmark_name}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
