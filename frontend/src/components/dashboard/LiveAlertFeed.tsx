import { AlertTriangle, Ban, Radio } from 'lucide-react';
import type { Alert } from '../../lib/api';

interface LiveAlertFeedProps {
    alerts: Alert[];
    connected: boolean;
}

function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
}

export function LiveAlertFeed({ alerts, connected }: LiveAlertFeedProps) {
    return (
        <div className="glass-card flex flex-col h-full animate-fade-in" style={{ animationDelay: '400ms' }}>
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-[var(--color-border)]">
                <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                        Live Feed
                    </h3>
                    {connected && (
                        <span className="flex items-center gap-1">
                            <Radio size={10} className="text-[var(--color-accent)] animate-pulse" />
                            <span className="text-xs text-[var(--color-accent)] font-medium">LIVE</span>
                        </span>
                    )}
                </div>
                <span className="text-xs text-[var(--color-text-muted)]">
                    {alerts.length} alerts
                </span>
            </div>

            {/* Alert list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2.5" style={{ maxHeight: '550px' }}>
                {alerts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-32 text-[var(--color-text-muted)]">
                        <Radio size={24} className="mb-2 opacity-30" />
                        <p className="text-xs">Waiting for violations...</p>
                    </div>
                ) : (
                    alerts.map((alert, index) => (
                        <div
                            key={`${alert.id}-${index}`}
                            className="flex items-start gap-3 p-3 rounded-[var(--radius-md)]
                bg-[var(--color-bg-secondary)] border border-[var(--color-border)]
                hover:border-[var(--color-border-light)] transition-all
                animate-slide-right"
                            style={{ animationDelay: `${index * 50}ms` }}
                        >
                            {/* Icon */}
                            <div
                                className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${alert.violation_type === 'ILLEGAL_PARKING'
                                    ? 'bg-[var(--color-warning-dim)]'
                                    : 'bg-[var(--color-danger-dim)]'
                                    }`}
                            >
                                {alert.violation_type === 'ILLEGAL_PARKING' ? (
                                    <AlertTriangle size={18} className="text-[var(--color-warning)]" />
                                ) : (
                                    <Ban size={18} className="text-[var(--color-danger)]" />
                                )}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between">
                                    <span
                                        className={`text-sm font-semibold ${alert.violation_type === 'ILLEGAL_PARKING'
                                            ? 'text-[var(--color-warning)]'
                                            : 'text-[var(--color-danger)]'
                                            }`}
                                    >
                                        {alert.violation_type === 'ILLEGAL_PARKING'
                                            ? 'Illegal Parking'
                                            : 'Wrong Way'}
                                    </span>
                                    <span className="text-xs text-[var(--color-text-muted)]">
                                        {timeAgo(alert.timestamp)}
                                    </span>
                                </div>
                                <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
                                    Object #{alert.object_id} • {(alert.confidence * 100).toFixed(0)}% confidence
                                    {alert.zone_id && ` • ${alert.zone_id}`}
                                </p>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
