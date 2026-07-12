/**
 * AEGIS — SMS Simulation Form
 * Allows demo users to inject simulated SMS messages into the pipeline.
 */

import { useState } from 'react';
import { Send } from 'lucide-react';
import { api } from '../services/api';

const PRESET_MESSAGES = [
  { label: '🔴 Critical Rescue', text: 'Help us! Water rising fast near Charminar, 4 people trapped on terrace including 2 children. Please send rescue boats!' },
  { label: '🟡 Medical Emergency', text: 'Old man collapsed near Mehdipatnam bus stop, not breathing properly. Need ambulance urgently.' },
  { label: '🔵 Food/Shelter Need', text: 'Our house in Kukatpally is completely flooded. Family of 5 with elderly. No food or water since morning. Need help.' },
  { label: '🟡 Flood Report', text: 'Major flooding near Musi River bridge area. Several families stuck on rooftops. Water level still rising.' },
  { label: '⚪ Vague Report', text: 'Need help, things are bad here' },
];

export default function SimulateForm() {
  const [message, setMessage] = useState('');
  const [phone, setPhone] = useState('+911234567890');
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!message.trim() || sending) return;

    setSending(true);
    setStatus(null);

    try {
      await api.simulateSms(message.trim(), phone);
      setStatus({ type: 'success', text: 'SMS sent to pipeline!' });
      setMessage('');
    } catch (err) {
      setStatus({ type: 'error', text: err.message });
    } finally {
      setSending(false);
      setTimeout(() => setStatus(null), 4000);
    }
  }

  function usePreset(text) {
    setMessage(text);
  }

  return (
    <div className="simulate-form">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">SMS Message</label>
          <textarea
            className="form-textarea"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type an emergency SMS..."
            rows={3}
          />
        </div>

        <div className="form-group">
          <label className="form-label">From Phone</label>
          <input
            className="form-input"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+911234567890"
          />
        </div>

        <button className="btn btn--primary" type="submit" disabled={sending || !message.trim()}>
          {sending ? <span className="spinner" /> : <Send size={14} />}
          {sending ? 'Sending...' : 'Send to Pipeline'}
        </button>
      </form>

      {status && (
        <div
          className="animate-in"
          style={{
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            fontWeight: 500,
            background: status.type === 'success' ? 'var(--color-success-bg)' : 'var(--color-critical-bg)',
            color: status.type === 'success' ? 'var(--color-success)' : 'var(--color-critical)',
            border: `1px solid ${status.type === 'success' ? 'var(--color-success-border)' : 'var(--color-critical-border)'}`,
          }}
        >
          {status.text}
        </div>
      )}

      <div style={{ marginTop: 4 }}>
        <span className="form-label">Quick Presets</span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
          {PRESET_MESSAGES.map((preset, i) => (
            <button
              key={i}
              className="btn btn--sm"
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                justifyContent: 'flex-start',
                fontSize: '11px',
                width: '100%',
                textAlign: 'left',
              }}
              type="button"
              onClick={() => usePreset(preset.text)}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
