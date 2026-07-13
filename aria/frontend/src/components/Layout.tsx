import React from 'react';
import {
  LayoutDashboard,
  Phone,
  CalendarDays,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  Activity,
  Wifi,
  WifiOff,
  CheckCircle,
  AlertCircle,
  Info,
  X,
  Radio,
  BarChart3,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useStore } from '../store/useStore';
import type { Page } from '../types';

// ── Navigation Items ───────────────────────────────────────────────────────────
const navItems: { id: Page; label: string; icon: LucideIcon }[] = [
  { id: 'dashboard',  label: 'Dashboard',   icon: LayoutDashboard },
  { id: 'calls',      label: 'Calls',       icon: Phone },
  { id: 'live-calls', label: 'Live Calls',  icon: Radio },
  { id: 'bookings',   label: 'Bookings',    icon: CalendarDays },
  { id: 'patients',   label: 'Patients',    icon: Users },
  { id: 'reports',    label: 'Reports',     icon: BarChart3 },
  { id: 'settings',   label: 'Settings',    icon: Settings },
];

// ── Toast Notification ─────────────────────────────────────────────────────────
function Toast() {
  const { toast, clearToast } = useStore();
  if (!toast) return null;

  const icons = {
    success: <CheckCircle size={16} className="text-emerald-400" />,
    error:   <AlertCircle size={16} className="text-red-400" />,
    info:    <Info size={16} className="text-indigo-400" />,
  };

  const borders = {
    success: 'border-emerald-500/30',
    error:   'border-red-500/30',
    info:    'border-indigo-500/30',
  };

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl glass-card-flat border ${borders[toast.type]} animate-fade-in shadow-glass`}
    >
      {icons[toast.type]}
      <span className="text-sm text-white/90 font-medium">{toast.message}</span>
      <button onClick={clearToast} className="ml-2 text-white/40 hover:text-white/80 transition-colors">
        <X size={14} />
      </button>
    </div>
  );
}

// ── Layout Component ───────────────────────────────────────────────────────────
interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { currentPage, setCurrentPage, sidebarCollapsed, toggleSidebar, wsConnected } = useStore();

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside
        className={`
          flex flex-col flex-shrink-0 h-full transition-all duration-300 ease-in-out
          ${sidebarCollapsed ? 'w-[72px]' : 'w-64'}
        `}
        style={{
          background: 'rgba(10, 15, 30, 0.95)',
          borderRight: '1px solid rgba(99, 102, 241, 0.1)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)' }}
            >
              <Activity size={18} className="text-white" />
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0 animate-fade-in">
                <p className="font-bold text-white text-sm leading-tight truncate">Aria Dashboard</p>
                <p className="text-[10px] text-white/40 truncate">Dental Receptionist AI</p>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setCurrentPage(id)}
              title={sidebarCollapsed ? label : undefined}
              className={`nav-item w-full ${currentPage === id ? 'active' : ''} ${sidebarCollapsed ? 'justify-center px-0' : ''}`}
            >
              <Icon size={18} className="flex-shrink-0" />
              {!sidebarCollapsed && <span className="truncate animate-fade-in">{label}</span>}
            </button>
          ))}
        </nav>

        {/* Footer: WS status + collapse */}
        <div className="p-3 border-t space-y-2" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
          {/* WebSocket status */}
          <div className={`flex items-center gap-2 px-3 py-2 rounded-xl ${sidebarCollapsed ? 'justify-center' : ''}`}>
            {wsConnected ? (
              <>
                <Wifi size={14} className="text-emerald-400 flex-shrink-0" />
                {!sidebarCollapsed && <span className="text-[11px] text-emerald-400 font-medium">Live Connected</span>}
              </>
            ) : (
              <>
                <WifiOff size={14} className="text-white/30 flex-shrink-0" />
                {!sidebarCollapsed && <span className="text-[11px] text-white/30">Offline</span>}
              </>
            )}
          </div>

          {/* Collapse toggle */}
          <button
            onClick={toggleSidebar}
            className="btn-secondary w-full justify-center py-2"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span className="text-xs">Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* ── Main Content ──────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header
          className="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b"
          style={{
            background: 'rgba(10,15,30,0.6)',
            borderColor: 'rgba(99,102,241,0.1)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div>
            <h1 className="text-sm font-semibold text-white/80 capitalize">
              {navItems.find((n) => n.id === currentPage)?.label ?? 'Dashboard'}
            </h1>
            <p className="text-[11px] text-white/30">Naveen Advanced Dental Clinic</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass-card-flat border border-indigo-500/20 text-xs text-white/50">
              <span className="status-dot online" />
              <span>API v1.0.0</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto">
          <div className="animate-fade-in h-full">
            {children}
          </div>
        </div>
      </main>

      {/* Toast notification */}
      <Toast />
    </div>
  );
}
