import { useEffect, useState, useCallback } from 'react';
import { fetchAlerts, fetchStats } from '../lib/api';
import type { AlertListResponse, Stats } from '../lib/api';

/**
 * Hook for fetching and managing alert data from the API.
 */
export function useAlerts(autoRefreshMs = 30000) {
    const [data, setData] = useState<AlertListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [filter, setFilter] = useState<string | undefined>();

    const load = useCallback(async () => {
        try {
            setLoading(true);
            const result = await fetchAlerts(page, 20, filter);
            setData(result);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
        } finally {
            setLoading(false);
        }
    }, [page, filter]);

    useEffect(() => {
        load();
        const interval = setInterval(load, autoRefreshMs);
        return () => clearInterval(interval);
    }, [load, autoRefreshMs]);

    return {
        alerts: data?.alerts ?? [],
        total: data?.total ?? 0,
        totalPages: data?.total_pages ?? 1,
        page,
        setPage,
        filter,
        setFilter,
        loading,
        error,
        refetch: load,
    };
}

/**
 * Hook for fetching dashboard statistics.
 */
export function useStats(autoRefreshMs = 15000) {
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        try {
            const result = await fetchStats();
            setStats(result);
        } catch {
            // Silently fail — stats are non-critical
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
        const interval = setInterval(load, autoRefreshMs);
        return () => clearInterval(interval);
    }, [load, autoRefreshMs]);

    return { stats, loading, refetch: load };
}
