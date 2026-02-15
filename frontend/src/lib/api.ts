/**
 * Typed API client for the Traffic Violation System backend.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

// ── Types ──────────────────────────────────────────────────────────────────

export interface Alert {
    id: number;
    violation_type: 'ILLEGAL_PARKING' | 'WRONG_WAY';
    confidence: number;
    object_id: number;
    snapshot_path: string | null;
    zone_id: string | null;
    metadata: Record<string, unknown> | null;
    timestamp: string;
}

export interface AlertListResponse {
    alerts: Alert[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface HourlyDataPoint {
    hour: string;
    count: number;
    illegal_parking: number;
    wrong_way: number;
}

export interface Stats {
    total_violations: number;
    violations_today: number;
    by_type: Record<string, number>;
    hourly_distribution: HourlyDataPoint[];
    recent_trend: number;
}

// ── Fetch helpers ──────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`);
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
}

// ── API Functions ──────────────────────────────────────────────────────────

export async function fetchAlerts(
    page = 1,
    pageSize = 20,
    violationType?: string,
): Promise<AlertListResponse> {
    let url = `/api/alerts?page=${page}&page_size=${pageSize}`;
    if (violationType) url += `&violation_type=${violationType}`;
    return get<AlertListResponse>(url);
}

export async function fetchAlert(id: number): Promise<Alert> {
    return get<Alert>(`/api/alerts/${id}`);
}

export async function fetchStats(): Promise<Stats> {
    return get<Stats>(`/api/stats`);
}

export async function fetchHealth(): Promise<{ status: string }> {
    return get<{ status: string }>(`/health`);
}
