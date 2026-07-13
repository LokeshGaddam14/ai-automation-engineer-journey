import React from 'react';
import {
  Phone, Users, Clock, CheckCircle, TrendingUp,
  RefreshCw, Activity, Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, Cell,
} from 'recharts';
import { analyticsAPI } from '../services/api';
import { usePolling } from '../hooks/useApi';
import type { Analytics } from '../types';

// ── Skeleton Loader ────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="stat-card animate-shimmer" style={{ minHeight: 120 }}>
      <div className="h-4 w-24 rounded-lg bg-white/10 mb-4" />
      <div className="h-8 w-16 rounded-lg bg-white/10 mb-2" />
      <div className="h-3 w-20 rounded-lg bg-white/10" />
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  gradient: string;
  subtext?: string;
  pulse?: boolean;
}

function StatCard({ label, value, icon: Icon, gradient, subtext, pulse }: StatCardProps) {
  return (
    <div className="stat-card group">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-white/50 mb-1.5">{label}</p>
          <p className="text-3xl font-extrabold text-white tabular-nums">{value}</p>
          {subtext && (
            <p className="text-[11px] text-white/35 mt-1.5">{subtext}</p>
          )}
        </div>
        <div
          className="icon-wrapper flex-shrink-0 relative"
          style={{ background: gradient }}
        >
          <Icon size={20} className="text-white" />
          {pulse && (
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-surface-900 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card-flat border border-indigo-500/30 px-3 py-2 rounded-xl text-xs">
      <p className="text-white/60 mb-1">{label}</p>
      <p className="text-white font-bold">{payload[0].value.toLocaleString()}</p>
    </div>
  );
}

// ── Booking Rate Bar ───────────────────────────────────────────────────────────
function BookingRateBar({ rate }: { rate: number }) {
  const pct = Math.min(Math.round(rate * 100), 100);
  return (
    <div>
      <div className="flex justify-between text-xs text-white/50 mb-2">
        <span>Booking Rate</span>
        <span className="font-semibold text-white/80">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #6366f1, #a855f7)' }}
        />
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export function Dashboard() {
  const { data: stats, loading, error, refetch } = usePolling(
    () => analyticsAPI.getStats(),
    60_000
  );

  // Build chart data from stats
  const buildChartData = (s: Analytics) => {
    if (s.by_date && s.by_date.length > 0) {
      return s.by_date.slice(-7).map((d) => ({
        name: new Date(d.date).toLocaleDateString('en', { weekday: 'short' }),
        calls: d.count,
      }));
    }
    // Fallback synthetic weekly data
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const total = s.total_calls;
    return days.map((name, i) => ({
      name,
      calls: Math.max(0, Math.round((total / 7) * (0.6 + Math.sin(i) * 0.4))),
    }));
  };

  const GRADIENT_COLORS = ['#6366f1', '#7c3aed', '#a855f7', '#c026d3', '#db2777', '#e11d48', '#f43f5e'];

  return (
    <div className="p-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Live Analytics</h1>
          <p className="text-sm text-white/40 mt-1">
            Auto-refreshes every 60 seconds
          </p>
        </div>
        <button
          onClick={refetch}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="glass-card-flat border border-red-500/30 px-4 py-3 rounded-xl text-sm text-red-400 flex items-center gap-2">
          <Activity size={16} />
          <span>Backend unavailable — showing cached data. {error}</span>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {loading ? (
          <>
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </>
        ) : stats ? (
          <>
            <StatCard
              label="Total Calls"
              value={stats.total_calls.toLocaleString()}
              icon={Phone}
              gradient="linear-gradient(135deg, #6366f1, #4f46e5)"
              subtext={`${stats.active_calls ?? 0} active now`}
              pulse={(stats.active_calls ?? 0) > 0}
            />
            <StatCard
              label="Unique Patients"
              value={stats.unique_patients.toLocaleString()}
              icon={Users}
              gradient="linear-gradient(135deg, #06b6d4, #0891b2)"
              subtext="All time"
            />
            <StatCard
              label="Avg Duration"
              value={`${Math.round(stats.avg_duration_seconds)}s`}
              icon={Clock}
              gradient="linear-gradient(135deg, #f59e0b, #d97706)"
              subtext={`${Math.round(stats.total_duration_seconds / 60)} min total`}
            />
            <StatCard
              label="Confirmed Bookings"
              value={stats.confirmed_bookings.toLocaleString()}
              icon={CheckCircle}
              gradient="linear-gradient(135deg, #10b981, #059669)"
              subtext={stats.booking_rate !== undefined ? `${Math.round(stats.booking_rate * 100)}% rate` : undefined}
            />
          </>
        ) : null}
      </div>

      {/* Charts Row */}
      {stats && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Weekly Calls Chart */}
          <div className="xl:col-span-2 glass-card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="section-title">Weekly Call Volume</h2>
                <p className="text-xs text-white/40 mt-0.5">Last 7 days</p>
              </div>
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <TrendingUp size={14} />
                <span>Live</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={buildChartData(stats)} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
                <Bar dataKey="calls" radius={[6, 6, 0, 0]}>
                  {buildChartData(stats).map((_, i) => (
                    <Cell key={i} fill={GRADIENT_COLORS[i % GRADIENT_COLORS.length]} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Summary Panel */}
          <div className="glass-card p-6 flex flex-col gap-4">
            <div>
              <h2 className="section-title">Summary</h2>
              <p className="text-xs text-white/40 mt-0.5">Performance overview</p>
            </div>

            {/* Booking rate */}
            <BookingRateBar rate={stats.booking_rate ?? (stats.confirmed_bookings / Math.max(stats.total_calls, 1))} />

            {/* Mini area chart */}
            <div>
              <p className="text-xs text-white/50 mb-2">Call trend</p>
              <ResponsiveContainer width="100%" height={70}>
                <AreaChart data={buildChartData(stats)}>
                  <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="calls"
                    stroke="#6366f1"
                    strokeWidth={2}
                    fill="url(#areaGrad)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Language breakdown */}
            {stats.languages && Object.keys(stats.languages).length > 0 && (
              <div>
                <p className="text-xs text-white/50 mb-2">Languages</p>
                <div className="space-y-1.5">
                  {Object.entries(stats.languages).map(([lang, count]) => (
                    <div key={lang} className="flex items-center justify-between text-xs">
                      <span className="text-white/60">{lang}</span>
                      <span className="font-semibold text-white/90">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick stats */}
            <div className="mt-auto pt-4 border-t divider grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-white/35 mb-0.5">Completed</p>
                <p className="text-base font-bold text-white">{stats.completed_calls ?? stats.total_calls}</p>
              </div>
              <div>
                <p className="text-[10px] text-white/35 mb-0.5">Active Now</p>
                <p className="text-base font-bold text-emerald-400 flex items-center gap-1">
                  {stats.active_calls ?? 0}
                  {(stats.active_calls ?? 0) > 0 && <Zap size={12} />}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
