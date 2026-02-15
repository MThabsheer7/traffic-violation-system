import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    CartesianGrid,
} from 'recharts';
import type { HourlyDataPoint } from '../../lib/api';

interface ViolationsChartProps {
    data: HourlyDataPoint[];
}

function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="glass-card p-3 !border-[var(--color-border-light)] text-sm">
            <p className="font-semibold text-[var(--color-text-primary)] mb-1.5">{label}</p>
            <div className="space-y-1">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-warning)]" />
                    <span className="text-[var(--color-text-secondary)]">Parking:</span>
                    <span className="font-semibold text-[var(--color-text-primary)]">{payload[0]?.value ?? 0}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-danger)]" />
                    <span className="text-[var(--color-text-secondary)]">Wrong Way:</span>
                    <span className="font-semibold text-[var(--color-text-primary)]">{payload[1]?.value ?? 0}</span>
                </div>
            </div>
        </div>
    );
}

export function ViolationsChart({ data }: ViolationsChartProps) {
    return (
        <div className="glass-card p-6 animate-fade-in" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center justify-between mb-5">
                <div>
                    <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                        Violations per Hour
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)] mt-0.5">Last 24 hours</p>
                </div>
                <div className="flex items-center gap-4 text-xs text-[var(--color-text-secondary)]">
                    <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[var(--color-warning)]" />
                        Illegal Parking
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[var(--color-danger)]" />
                        Wrong Way
                    </span>
                </div>
            </div>

            <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="gradParking" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="var(--color-warning)" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="var(--color-warning)" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="gradWrongWay" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="var(--color-danger)" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="var(--color-danger)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
                        <XAxis
                            dataKey="hour"
                            tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
                            tickLine={false}
                            axisLine={false}
                            interval="preserveStartEnd"
                        />
                        <YAxis
                            tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
                            tickLine={false}
                            axisLine={false}
                            allowDecimals={false}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="illegal_parking"
                            stroke="var(--color-warning)"
                            strokeWidth={2}
                            fill="url(#gradParking)"
                        />
                        <Area
                            type="monotone"
                            dataKey="wrong_way"
                            stroke="var(--color-danger)"
                            strokeWidth={2}
                            fill="url(#gradWrongWay)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
