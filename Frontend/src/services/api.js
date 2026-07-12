/**
 * AEGIS — API Service
 * Centralized REST API calls to the FastAPI backend.
 */

const API_BASE = 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Incidents
  getIncidents: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/incidents${query ? `?${query}` : ''}`);
  },
  getIncident: (id) => request(`/api/incidents/${id}`),

  // Resources
  getResources: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/resources${query ? `?${query}` : ''}`);
  },

  // Dispatches
  getDispatches: () => request('/api/dispatches'),

  // SitReps
  getSitreps: () => request('/api/sitreps'),
  getLatestSitrep: () => request('/api/sitreps/latest'),

  // Agent Logs
  getAgentLogs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/api/agent-logs${query ? `?${query}` : ''}`);
  },

  // Simulate SMS
  simulateSms: (body, fromPhone = '+911234567890') =>
    request('/api/simulate/sms', {
      method: 'POST',
      body: JSON.stringify({ body, from_phone: fromPhone }),
    }),

  // Dashboard Actions
  ackDispatch: (dispatchId) =>
    request(`/api/actions/ack-dispatch/${dispatchId}`, { method: 'POST' }),
  resolveIncident: (incidentId) =>
    request(`/api/actions/resolve-incident/${incidentId}`, { method: 'POST' }),

  // Health
  getStatus: () => request('/api/status'),
};
