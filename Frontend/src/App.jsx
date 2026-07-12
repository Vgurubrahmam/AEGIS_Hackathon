/**
 * AEGIS — Main Dashboard Application
 * Three-column layout: Sidebar (incidents + simulate) | Map | Right Panel (trace + sitrep)
 * Real-time WebSocket updates after every pipeline step.
 */

import { useState, useEffect, useCallback } from 'react';
import { Shield, Wifi, WifiOff, Activity, Radio, Layers, Zap, FileText, Package } from 'lucide-react';
import { api } from './services/api';
import { useWebSocket } from './hooks/useWebSocket';
import IncidentMap from './components/IncidentMap';
import IncidentList from './components/IncidentList';
import SimulateForm from './components/SimulateForm';
import AgentTrace from './components/AgentTrace';
import SitRepPanel from './components/SitRepPanel';
import ResourceList from './components/ResourceList';

export default function App() {
  // ── State ───────────────────────────────────────────────
  const [incidents, setIncidents] = useState([]);
  const [resources, setResources] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  const [sitrep, setSitrep] = useState(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [rightTab, setRightTab] = useState('trace');
  const [eventCount, setEventCount] = useState(0);

  // ── Initial Data Load ───────────────────────────────────
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [inc, res, logs] = await Promise.all([
          api.getIncidents(),
          api.getResources(),
          api.getAgentLogs(),
        ]);
        setIncidents(inc);
        setResources(res);
        setAgentLogs(logs);

        // Try loading latest sitrep
        try {
          const sr = await api.getLatestSitrep();
          setSitrep(sr);
        } catch { /* No sitrep yet */ }
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    }
    loadInitialData();
  }, []);

  // ── WebSocket Event Handler ─────────────────────────────
  const handleWsEvent = useCallback((event) => {
    setEventCount(c => c + 1);

    switch (event.event_type) {
      case 'incident_created': {
        const newInc = {
          id: event.incident_id,
          raw_text: event.data?.raw_text || '',
          sender_phone: event.data?.sender_phone || '',
          status: 'new',
          severity: null,
          need_type: null,
          confidence_score: null,
          landmark_name: null,
          latitude: null,
          longitude: null,
          created_at: event.timestamp,
          updated_at: event.timestamp,
          _isNew: true,
        };
        setIncidents(prev => [newInc, ...prev.filter(i => i.id !== event.incident_id)]);
        setSelectedIncidentId(event.incident_id);
        setRightTab('trace');
        break;
      }

      case 'incident_updated': {
        setIncidents(prev => prev.map(i =>
          i.id === event.incident_id
            ? { ...i, ...event.data, updated_at: event.timestamp, _isNew: false }
            : i
        ));
        break;
      }

      case 'agent_step': {
        const newLog = {
          id: `ws-${Date.now()}-${Math.random()}`,
          incident_id: event.incident_id,
          agent_name: event.agent_name,
          step_status: event.step_status,
          output_summary: event.data?.reasoning || '',
          duration_ms: event.data?.duration_ms || null,
          created_at: event.timestamp,
        };
        setAgentLogs(prev => [newLog, ...prev]);

        // If resource matching succeeded, refresh resources
        if (event.agent_name === 'resource_matching' && event.step_status === 'success') {
          api.getResources().then(setResources).catch(() => {});
        }
        break;
      }

      case 'dispatch_created': {
        // Refresh resources to show reservation
        api.getResources().then(setResources).catch(() => {});
        break;
      }

      case 'sitrep_updated': {
        const newSitrep = {
          id: event.data?.sitrep_id || '',
          summary_text: event.data?.summary_text || '',
          incident_count: event.data?.incident_count || 0,
          critical_count: event.data?.critical_count || 0,
          dispatched_count: event.data?.dispatched_count || 0,
          needs_review_count: event.data?.needs_review_count || 0,
          created_at: event.timestamp,
        };
        setSitrep(newSitrep);
        break;
      }

      case 'dispatch_ack': {
        api.getResources().then(setResources).catch(() => {});
        break;
      }

      case 'incident_resolved': {
        setIncidents(prev => prev.map(i =>
          i.id === event.incident_id ? { ...i, status: 'resolved' } : i
        ));
        api.getResources().then(setResources).catch(() => {});
        break;
      }

      default:
        console.log('[WS] Unknown event:', event.event_type);
    }
  }, []);

  const { connected } = useWebSocket(handleWsEvent);

  // ── Computed Stats ──────────────────────────────────────
  const activeIncidents = incidents.filter(i => i.status !== 'resolved');
  const stats = {
    total: activeIncidents.length,
    critical: activeIncidents.filter(i => i.severity === 'critical').length,
    dispatched: activeIncidents.filter(i => i.status === 'dispatched').length,
    needsReview: activeIncidents.filter(i => i.status === 'needs_review').length,
  };

  // ── Render ──────────────────────────────────────────────
  return (
    <div className="app-layout">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo">
            <Shield size={18} />
          </div>
          <div>
            <div className="app-header__title">AEGIS</div>
            <div className="app-header__subtitle">AI-Enhanced Governance & Intelligence System</div>
          </div>
        </div>

        <div className="app-header__status">
          <div className="status-indicator">
            <div className={`status-dot ${connected ? 'status-dot--online' : 'status-dot--offline'}`} />
            {connected ? 'Live' : 'Disconnected'}
          </div>

          <div className="status-indicator">
            <Activity size={12} />
            {eventCount} events
          </div>

          <div className="stats-grid" style={{ display: 'flex', gap: 12, margin: 0 }}>
            <div className="status-indicator">
              <span style={{ color: 'var(--color-critical)' }}>●</span>
              {stats.critical} critical
            </div>
            <div className="status-indicator">
              <span style={{ color: 'var(--color-success)' }}>●</span>
              {stats.dispatched} dispatched
            </div>
            <div className="status-indicator">
              <span style={{ color: 'var(--color-warning)' }}>●</span>
              {stats.needsReview} review
            </div>
          </div>
        </div>
      </header>

      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar__section">
          <div className="sidebar__title">
            <Radio size={12} />
            Simulate SMS
          </div>
          <SimulateForm />
        </div>

        <div className="sidebar__section">
          <div className="sidebar__title">
            <Layers size={12} />
            Resources ({resources.filter(r => r.status === 'available').length}/{resources.length} available)
          </div>
          <div style={{ maxHeight: '100px', overflowY: 'auto', paddingRight: '4px' }}>
            <ResourceList resources={resources} />
          </div>
        </div>

        <div className="sidebar__section">
          <div className="sidebar__title">
            <Activity size={12} />
            Incidents ({activeIncidents.length})
          </div>
          <div style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '4px' }}>
            <IncidentList
              incidents={activeIncidents}
              selectedId={selectedIncidentId}
              onSelectIncident={setSelectedIncidentId}
            />
          </div>
        </div>
      </aside>

      {/* ── Main: Map ───────────────────────────────────── */}
      <main className="main-content">
        <IncidentMap
          incidents={activeIncidents}
          selectedId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />
      </main>

      {/* ── Right Panel ─────────────────────────────────── */}
      <aside className="right-panel">
        <div className="panel-tabs">
          <button
            className={`panel-tab ${rightTab === 'trace' ? 'panel-tab--active' : ''}`}
            onClick={() => setRightTab('trace')}
          >
            <Zap size={12} style={{ marginRight: 4 }} />
            Agent Trace
          </button>
          <button
            className={`panel-tab ${rightTab === 'sitrep' ? 'panel-tab--active' : ''}`}
            onClick={() => setRightTab('sitrep')}
          >
            <FileText size={12} style={{ marginRight: 4 }} />
            SitRep
          </button>
        </div>

        <div className="panel-content">
          {rightTab === 'trace' && (
            <AgentTrace
              logs={agentLogs}
              selectedIncidentId={selectedIncidentId}
            />
          )}
          {rightTab === 'sitrep' && (
            <SitRepPanel sitrep={sitrep} />
          )}
        </div>
      </aside>
    </div>
  );
}
