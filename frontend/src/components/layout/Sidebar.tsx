import {
    LayoutDashboard,
    ShieldAlert,
    Activity,
    Settings,
    Camera,
    ChevronLeft,
} from 'lucide-react';
import { useState } from 'react';

const NAV_ITEMS = [
    { icon: LayoutDashboard, label: 'Dashboard', active: true },
    { icon: ShieldAlert, label: 'Violations', active: false },
    { icon: Activity, label: 'Analytics', active: false },
    { icon: Camera, label: 'Cameras', active: false },
    { icon: Settings, label: 'Settings', active: false },
];

export function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <aside
            className={`
        h-screen sticky top-0 flex flex-col
        border-r border-[var(--color-border)]
        bg-[var(--color-bg-secondary)]
        transition-all duration-300 ease-in-out
        ${collapsed ? 'w-20' : 'w-[260px]'}
      `}
        >
            {/* Logo */}
            <div className="flex items-center gap-4 px-5 h-24 border-b border-[var(--color-border)]">
                <div className="w-14 h-14 rounded-xl bg-[var(--color-accent)] flex items-center justify-center flex-shrink-0">
                    <ShieldAlert size={30} className="text-black" />
                </div>
                {!collapsed && (
                    <span className="text-2xl font-bold tracking-tight text-[var(--color-text-primary)] whitespace-nowrap">
                        TrafficGuard
                    </span>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 space-y-1">
                {NAV_ITEMS.map(({ icon: Icon, label, active }) => (
                    <button
                        key={label}
                        className={`
              w-full flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)]
              text-base font-medium transition-all duration-200
              ${active
                                ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]'
                                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-card)] hover:text-[var(--color-text-primary)]'
                            }
            `}
                    >
                        <Icon size={22} className="flex-shrink-0" />
                        {!collapsed && <span>{label}</span>}
                    </button>
                ))}
            </nav>

            {/* Collapse toggle */}
            <div className="p-3 border-t border-[var(--color-border)]">
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="w-full flex items-center justify-center p-2 rounded-[var(--radius-md)]
            text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]
            hover:bg-[var(--color-bg-card)] transition-colors"
                >
                    <ChevronLeft
                        size={18}
                        className={`transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
                    />
                </button>
            </div>
        </aside>
    );
}
