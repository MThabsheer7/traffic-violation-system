import { useEffect, useRef, useState, useCallback } from 'react';
import type { Alert } from '../lib/api';

/**
 * Custom hook for WebSocket connection to live alert feed.
 * Auto-reconnects with exponential backoff.
 */
export function useWebSocket(maxAlerts = 50) {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [connected, setConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const retryRef = useRef(0);
    const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

    const connect = useCallback(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/ws/alerts`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            retryRef.current = 0;
        };

        ws.onmessage = (event) => {
            try {
                const alert: Alert = JSON.parse(event.data);
                setAlerts((prev) => [alert, ...prev].slice(0, maxAlerts));
            } catch {
                // Ignore malformed messages
            }
        };

        ws.onclose = () => {
            setConnected(false);
            // Exponential backoff: 1s, 2s, 4s, 8s... max 30s
            const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
            retryRef.current += 1;
            timerRef.current = setTimeout(connect, delay);
        };

        ws.onerror = () => {
            ws.close();
        };
    }, [maxAlerts]);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(timerRef.current);
            wsRef.current?.close();
        };
    }, [connect]);

    return { alerts, connected, lastAlert: alerts[0] ?? null };
}
