/**
 * AEGIS — Incident Map Component
 * Leaflet map showing incident locations with severity-colored markers.
 */

import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useEffect } from 'react';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default marker icon path issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const HYDERABAD_CENTER = [17.385, 78.4867];

const severityColors = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
};

function createMarkerIcon(severity) {
  const color = severityColors[severity] || '#6366f1';
  return L.divIcon({
    className: '',
    html: `<div class="custom-marker custom-marker--${severity}" style="width:28px;height:28px;background:${color};">
      <span style="font-size:11px;">⚠</span>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

function FitBounds({ incidents }) {
  const map = useMap();
  useEffect(() => {
    if (incidents.length > 0) {
      const points = incidents
        .filter(i => i.latitude && i.longitude)
        .map(i => [i.latitude, i.longitude]);
      if (points.length > 0) {
        const bounds = L.latLngBounds(points);
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
      }
    }
  }, [incidents.length]);
  return null;
}

export default function IncidentMap({ incidents, selectedId, onSelectIncident }) {
  const geoIncidents = incidents.filter(i => i.latitude && i.longitude);

  const stats = {
    total: incidents.length,
    critical: incidents.filter(i => i.severity === 'critical').length,
    dispatched: incidents.filter(i => i.status === 'dispatched').length,
  };

  return (
    <div className="map-container">
      <div className="map-overlay">
        <div className="map-stat">
          <span style={{ color: 'var(--color-info)' }}>📍</span>
          {stats.total} Incidents
        </div>
        {stats.critical > 0 && (
          <div className="map-stat">
            <span style={{ color: 'var(--color-critical)' }}>🔴</span>
            {stats.critical} Critical
          </div>
        )}
        {stats.dispatched > 0 && (
          <div className="map-stat">
            <span style={{ color: 'var(--color-success)' }}>✅</span>
            {stats.dispatched} Dispatched
          </div>
        )}
      </div>

      <MapContainer
        center={HYDERABAD_CENTER}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds incidents={geoIncidents} />

        {geoIncidents.map(incident => (
          <Marker
            key={incident.id}
            position={[incident.latitude, incident.longitude]}
            icon={createMarkerIcon(incident.severity)}
            eventHandlers={{
              click: () => onSelectIncident(incident.id),
            }}
          >
            <Popup>
              <div className="popup-title">
                {incident.severity?.toUpperCase()} — {incident.need_type?.toUpperCase()}
              </div>
              <div className="popup-meta">
                📍 {incident.landmark_name || 'Unknown'}<br />
                📝 {incident.raw_text?.substring(0, 100)}...
                <br />
                <span style={{ color: 'var(--text-muted)' }}>
                  Status: {incident.status} | Confidence: {incident.confidence_score?.toFixed(2) || '—'}
                </span>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
