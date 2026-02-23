import { ChevronLeft, ChevronRight, SlidersHorizontal } from 'lucide-react';
import type { Alert } from '../../lib/api';

interface ViolationsTableProps {
    alerts: Alert[];
    page: number;
    totalPages: number;
    total: number;
    loading: boolean;
    filter?: string;
    onPageChange: (page: number) => void;
    onFilterChange: (filter: string | undefined) => void;
}

function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString('en-IN', {
        timeZone: 'Asia/Kolkata',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export function ViolationsTable({
    alerts,
    page,
    totalPages,
    total,
    loading,
    filter,
    onPageChange,
    onFilterChange,
}: ViolationsTableProps) {
    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '300ms' }}>
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-[var(--color-border)]">
                <div>
                    <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                        Recent Violations
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
                        {total} total records
                    </p>
                </div>

                {/* Filter */}
                <div className="flex items-center gap-2">
                    <SlidersHorizontal size={16} className="text-[var(--color-text-muted)]" />
                    <select
                        value={filter || ''}
                        onChange={(e) => onFilterChange(e.target.value || undefined)}
                        className="h-9 px-3 rounded-[var(--radius-sm)] bg-[var(--color-bg-input)]
              border border-[var(--color-border)] text-sm text-[var(--color-text-primary)]
              focus:outline-none focus:border-[var(--color-accent)] transition-colors
              cursor-pointer"
                    >
                        <option value="">All Types</option>
                        <option value="ILLEGAL_PARKING">Illegal Parking</option>
                        <option value="WRONG_WAY">Wrong Way</option>
                    </select>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-base">
                    <thead>
                        <tr className="border-b border-[var(--color-border)]">
                            {['ID', 'Type', 'Confidence', 'Object', 'Zone', 'Time'].map((h) => (
                                <th
                                    key={h}
                                    className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]"
                                >
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading && alerts.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-5 py-12 text-center text-sm text-[var(--color-text-muted)]">
                                    Loading...
                                </td>
                            </tr>
                        ) : alerts.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-5 py-12 text-center text-sm text-[var(--color-text-muted)]">
                                    No violations found
                                </td>
                            </tr>
                        ) : (
                            alerts.map((alert) => (
                                <tr
                                    key={alert.id}
                                    className="border-b border-[var(--color-border)] last:border-b-0
                    hover:bg-[var(--color-bg-card-hover)] transition-colors cursor-pointer"
                                >
                                    <td className="px-5 py-4 text-sm text-[var(--color-text-muted)] tabular-nums">
                                        #{alert.id}
                                    </td>
                                    <td className="px-5 py-3">
                                        <span
                                            className={`badge ${alert.violation_type === 'ILLEGAL_PARKING'
                                                ? 'badge-parking'
                                                : 'badge-wrongway'
                                                }`}
                                        >
                                            {alert.violation_type === 'ILLEGAL_PARKING' ? 'Parking' : 'Wrong Way'}
                                        </span>
                                    </td>
                                    <td className="px-5 py-4 text-sm tabular-nums">
                                        <div className="flex items-center gap-2">
                                            <div className="w-16 h-2 rounded-full bg-[var(--color-bg-input)] overflow-hidden">
                                                <div
                                                    className="h-full rounded-full bg-[var(--color-accent)]"
                                                    style={{ width: `${alert.confidence * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-[var(--color-text-secondary)]">
                                                {(alert.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-5 py-4 text-sm text-[var(--color-text-secondary)] tabular-nums">
                                        #{alert.object_id}
                                    </td>
                                    <td className="px-5 py-4 text-sm text-[var(--color-text-secondary)]">
                                        {alert.zone_id || '—'}
                                    </td>
                                    <td className="px-5 py-4 text-sm text-[var(--color-text-muted)] tabular-nums">
                                        {formatDate(alert.timestamp)}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-5 py-4 border-t border-[var(--color-border)]">
                <span className="text-sm text-[var(--color-text-muted)]">
                    Page {page} of {totalPages}
                </span>
                <div className="flex items-center gap-1">
                    <button
                        disabled={page <= 1}
                        onClick={() => onPageChange(page - 1)}
                        className="p-2 rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-card)]
              disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        <ChevronLeft size={18} className="text-[var(--color-text-secondary)]" />
                    </button>
                    <button
                        disabled={page >= totalPages}
                        onClick={() => onPageChange(page + 1)}
                        className="p-2 rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-card)]
              disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        <ChevronRight size={18} className="text-[var(--color-text-secondary)]" />
                    </button>
                </div>
            </div>
        </div>
    );
}
