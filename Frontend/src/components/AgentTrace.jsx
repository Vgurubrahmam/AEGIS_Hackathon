/**
 * AEGIS — Agent Trace Panel
 * Shows step-by-step agent decisions for the selected incident.
 */

import { Shield, CheckCircle, XCircle, MapPin, Package, Send, FileText, Clock, Zap } from 'lucide-react';

const agentIcons = {
  triage: Shield,
  verification: CheckCircle,
  geolocation: MapPin,
  resource_matching: Package,
  dispatch: Send,
  sitrep: FileText,
};

const agentLabels = {
  triage: 'Triage Agent',
  verification: 'Verification Agent',
  geolocation: 'Geolocation Agent',
  resource_matching: 'Resource Matching',
  dispatch: 'Dispatch Agent',
  sitrep: 'SitRep Agent',
};

function formatTime(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function AgentTrace({ logs, selectedIncidentId }) {
  // Filter to selected incident if any
  const filteredLogs = selectedIncidentId
    ? logs.filter(l => l.incident_id === selectedIncidentId)
    : logs;

  // Sort by created_at ascending (chronological)
  const sorted = [...filteredLogs].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

  if (sorted.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon"><Zap size={36} /></div>
        <div className="empty-state__text">
          {selectedIncidentId
            ? 'No agent logs for this incident yet.'
            : 'Agent trace will appear here as incidents are processed.'}
        </div>
      </div>
    );
  }

  return (
    <div>
      {selectedIncidentId && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, fontFamily: 'var(--font-mono)' }}>
          Incident #{selectedIncidentId.substring(0, 8)}
        </div>
      )}

      {sorted.map((log) => {
        const Icon = agentIcons[log.agent_name] || Shield;
        const isSuccess = log.step_status === 'success';

        return (
          <div key={log.id} className="trace-item animate-in">
            <div className={`trace-item__icon trace-item__icon--${log.agent_name}`}>
              <Icon size={16} />
            </div>

            <div className="trace-item__body">
              <div className="trace-item__header">
                <span className="trace-item__agent">
                  {agentLabels[log.agent_name] || log.agent_name}
                  {isSuccess
                    ? <CheckCircle size={12} style={{ marginLeft: 6, color: 'var(--color-success)' }} />
                    : <XCircle size={12} style={{ marginLeft: 6, color: 'var(--color-critical)' }} />
                  }
                </span>
                <span className="trace-item__time">{formatTime(log.created_at)}</span>
              </div>

              <div className="trace-item__reasoning">
                {log.output_summary || 'Processing...'}
              </div>

              {log.duration_ms && (
                <div className="trace-item__duration">
                  <Clock size={10} style={{ marginRight: 3 }} />
                  {log.duration_ms}ms
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
