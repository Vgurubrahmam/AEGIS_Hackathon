/**
 * AEGIS — SitRep Panel
 * Displays the latest AI-generated situation report.
 */

import { FileText } from 'lucide-react';

function formatTimestamp(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

/** Very simple markdown-to-HTML: headings, bold, bullets */
function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/### (.*)/g, '<h3>$1</h3>')
    .replace(/## (.*)/g, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.*)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

export default function SitRepPanel({ sitrep }) {
  if (!sitrep) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon"><FileText size={36} /></div>
        <div className="empty-state__text">No situation report generated yet.<br />Process an incident to generate one.</div>
      </div>
    );
  }

  return (
    <div>
      <div className="sitrep-timestamp">
        Last updated: {formatTimestamp(sitrep.created_at)}
      </div>

      <div className="stats-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-card__value stat-card__value--info">{sitrep.incident_count}</div>
          <div className="stat-card__label">Active</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value stat-card__value--critical">{sitrep.critical_count}</div>
          <div className="stat-card__label">Critical</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value stat-card__value--success">{sitrep.dispatched_count}</div>
          <div className="stat-card__label">Dispatched</div>
        </div>
        <div className="stat-card">
          <div className="stat-card__value stat-card__value--warning">{sitrep.needs_review_count}</div>
          <div className="stat-card__label">Needs Review</div>
        </div>
      </div>

      <div
        className="sitrep-content"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(sitrep.summary_text) }}
      />
    </div>
  );
}
