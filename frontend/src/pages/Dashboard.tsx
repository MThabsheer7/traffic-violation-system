import { useEffect } from 'react';
import { ShieldAlert, ParkingCircle, ArrowLeftRight, Clock } from 'lucide-react';
import { Sidebar } from '../components/layout/Sidebar';
import { Topbar } from '../components/layout/Topbar';
import { StatCard } from '../components/dashboard/StatCard';
import { ViolationsChart } from '../components/dashboard/ViolationsChart';
import { ViolationsTable } from '../components/dashboard/ViolationsTable';
import { LiveAlertFeed } from '../components/dashboard/LiveAlertFeed';
import { useAlerts, useStats } from '../hooks/useAlerts';
import { useWebSocket } from '../hooks/useWebSocket';

export function Dashboard() {
    const { stats, refetch: refetchStats } = useStats();
    const { alerts, total, totalPages, page, setPage, filter, setFilter, loading, refetch: refetchAlerts } = useAlerts();
    const { alerts: liveAlerts, connected, lastAlert } = useWebSocket();

    // When a new WebSocket alert arrives, immediately refresh stats + table
    useEffect(() => {
        if (lastAlert) {
            refetchStats();
            refetchAlerts();
        }
    }, [lastAlert]);


    return (
        <div className="flex min-h-screen">
            <Sidebar />

            <div className="flex-1 flex flex-col min-w-0">
                <Topbar connected={connected} alertCount={liveAlerts.length} />

                <main className="flex-1 p-8">
                    <div className="flex gap-6">
                        {/* Main Content */}
                        <div className="flex-1 min-w-0 space-y-6">
                            {/* KPI Cards */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                                <StatCard
                                    title="Total Violations"
                                    value={stats?.total_violations ?? 0}
                                    icon={ShieldAlert}
                                    trend={stats?.recent_trend}
                                    delay={0}
                                />
                                <StatCard
                                    title="Today's Violations"
                                    value={stats?.violations_today ?? 0}
                                    icon={Clock}
                                    subtitle="Since midnight UTC"
                                    delay={50}
                                />
                                <StatCard
                                    title="Illegal Parking"
                                    value={stats?.by_type?.ILLEGAL_PARKING ?? 0}
                                    icon={ParkingCircle}
                                    accentColor="var(--color-warning)"
                                    delay={100}
                                />
                                <StatCard
                                    title="Wrong Way"
                                    value={stats?.by_type?.WRONG_WAY ?? 0}
                                    icon={ArrowLeftRight}
                                    accentColor="var(--color-danger)"
                                    delay={150}
                                />
                            </div>

                            {/* Chart */}
                            <ViolationsChart data={stats?.hourly_distribution ?? []} />

                            {/* Table */}
                            <ViolationsTable
                                alerts={alerts}
                                page={page}
                                totalPages={totalPages}
                                total={total}
                                loading={loading}
                                filter={filter}
                                onPageChange={setPage}
                                onFilterChange={setFilter}
                            />
                        </div>

                        {/* Right Panel — Live Feed */}
                        <div className="hidden xl:block w-[380px] flex-shrink-0">
                            <LiveAlertFeed alerts={liveAlerts} connected={connected} />
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
