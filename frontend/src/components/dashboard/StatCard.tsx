import { TrendingUp, TrendingDown, Minus, type LucideIcon } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: number | string;
    icon: LucideIcon;
    trend?: number;
    subtitle?: string;
    accentColor?: string;
    delay?: number;
}

export function StatCard({
    title,
    value,
    icon: Icon,
    trend,
    subtitle,
    accentColor = 'var(--color-accent)',
    delay = 0,
}: StatCardProps) {
    const TrendIcon = trend && trend > 0 ? TrendingUp : trend && trend < 0 ? TrendingDown : Minus;
    const trendColor = trend && trend > 0 ? 'text-[var(--color-danger)]' : trend && trend < 0 ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]';

    return (
        <div
            className="glass-card p-6 animate-fade-in"
            style={{ animationDelay: `${delay}ms` }}
        >
            <div className="flex items-start justify-between mb-5">
                <div
                    className="w-12 h-12 rounded-[var(--radius-md)] flex items-center justify-center"
                    style={{ backgroundColor: `color-mix(in srgb, ${accentColor} 12%, transparent)` }}
                >
                    <Icon size={24} style={{ color: accentColor }} />
                </div>
                {trend !== undefined && (
                    <div className={`flex items-center gap-1.5 text-sm font-semibold ${trendColor}`}>
                        <TrendIcon size={16} />
                        <span>{Math.abs(trend).toFixed(1)}%</span>
                    </div>
                )}
            </div>

            <div className="text-3xl font-bold text-[var(--color-text-primary)] tabular-nums">
                {typeof value === 'number' ? value.toLocaleString() : value}
            </div>

            <div className="mt-1.5 text-sm text-[var(--color-text-secondary)]">
                {title}
            </div>

            {subtitle && (
                <div className="mt-2 text-xs text-[var(--color-text-muted)]">
                    {subtitle}
                </div>
            )}
        </div>
    );
}
