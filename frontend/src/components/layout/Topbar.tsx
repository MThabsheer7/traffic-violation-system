import { Bell, Search, Wifi, WifiOff } from 'lucide-react';

interface TopbarProps {
    connected: boolean;
    alertCount: number;
}

export function Topbar({ connected, alertCount }: TopbarProps) {
    return (
        <header className="h-20 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] flex items-center justify-between px-8 sticky top-0 z-10">
            {/* Left — Title */}
            <div>
                <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
                    Dashboard
                </h1>
                <p className="text-sm text-[var(--color-text-muted)]">
                    Real-time traffic violation monitoring
                </p>
            </div>

            {/* Right — Actions */}
            <div className="flex items-center gap-4">
                {/* Search */}
                <div className="relative hidden md:block">
                    <Search
                        size={18}
                        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
                    />
                    <input
                        type="text"
                        placeholder="Search violations..."
                        className="w-80 h-11 pl-10 pr-4 rounded-[var(--radius-lg)]
              bg-[var(--color-bg-input)] border border-[var(--color-border)]
              text-base text-[var(--color-text-primary)]
              placeholder:text-[var(--color-text-muted)]
              focus:outline-none focus:border-[var(--color-accent)]
              transition-colors"
                    />
                </div>

                {/* WebSocket status */}
                <div
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium
            ${connected
                            ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]'
                            : 'bg-[var(--color-danger-dim)] text-[var(--color-danger)]'
                        }`}
                >
                    {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
                    {connected ? 'Live' : 'Offline'}
                </div>

                {/* Notifications */}
                <button className="relative p-2 rounded-[var(--radius-md)] hover:bg-[var(--color-bg-card)] transition-colors">
                    <Bell size={20} className="text-[var(--color-text-secondary)]" />
                    {alertCount > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 w-4.5 h-4.5 rounded-full bg-[var(--color-danger)] text-[10px] text-white font-bold flex items-center justify-center">
                            {alertCount > 9 ? '9+' : alertCount}
                        </span>
                    )}
                </button>
            </div>
        </header>
    );
}
