/**
 * AEGIS — WebSocket Hook
 * Connects to the backend WebSocket for live pipeline updates.
 * Auto-reconnects on disconnect.
 */

import { useEffect, useRef, useCallback, useState } from 'react';

const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 25000;

export function useWebSocket(onEvent) {
  const wsRef = useRef(null);
  const pingRef = useRef(null);
  const reconnectRef = useRef(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[WS] Connected to AEGIS backend');

        // Start ping/pong keepalive
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        if (event.data === 'pong') return; // Keepalive response

        try {
          const data = JSON.parse(event.data);
          onEvent(data);
        } catch (e) {
          console.warn('[WS] Failed to parse message:', event.data);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(pingRef.current);
        console.log('[WS] Disconnected. Reconnecting...');
        reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        ws.close();
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, [onEvent]);

  useEffect(() => {
    connect();

    return () => {
      clearInterval(pingRef.current);
      clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { connected };
}
