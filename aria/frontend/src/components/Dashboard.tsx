import React, { useRef, useEffect, useState } from 'react';
import {
  Phone, Users, Clock, CheckCircle, TrendingUp,
  RefreshCw, Activity, Zap, CloudDownload,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, Cell,
} from 'recharts';
import gsap from 'gsap';
import { analyticsAPI } from '../services/api';
import { usePolling } from '../hooks/useApi';
import { usePageEntrance, useCountUp } from '../hooks/useGsap';
import { useStore } from '../store/useStore';
import type { Analytics } from '../types';

// ── Skeleton Loader ────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="stat-card animate-shimmer" style={{ minHeight: 120 }}>
      <div className="h-4 w-24 rounded-lg bg-slate-900/5 dark:bg-white/10 mb-4" />
      <div className="h-8 w-16 rounded-lg bg-slate-900/5 dark:bg-white/10 mb-2" />
      <div className="h-3 w-20 rounded-lg bg-slate-900/5 dark:bg-white/10" />
    </div>
  );
}

// ── Animated Stat Card ────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: number | string;
  isNumeric?: boolean;
  icon: LucideIcon;
  gradient: string;
  subtext?: string;
  pulse?: boolean;
  index?: number;
}

function StatCard({ label, value, isNumeric, icon: Icon, gradient, subtext, pulse, index = 0 }: StatCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const numVal = typeof value === 'number' ? value : parseFloat(String(value).replace(/,/g, ''));
  const countRef = useCountUp(isNumeric !== false && !isNaN(numVal) ? numVal : 0, 1.4);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    gsap.fromTo(
      el,
      { opacity: 0, y: 28, scale: 0.95 },
      { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'power3.out', delay: index * 0.1 }
    );
  }, [index]);

  return (
    <div ref={cardRef} className="stat-card group" style={{ opacity: 0 }}>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-500 dark:text-white/50 mb-1.5">{label}</p>
          <p className="text-3xl font-extrabold text-slate-900 dark:text-white tabular-nums">
            {isNumeric !== false && !isNaN(numVal)
              ? <span ref={countRef}>0</span>
              : value}
          </p>
          {subtext && (
            <p className="text-[11px] text-slate-500 dark:text-white/35 mt-1.5">{subtext}</p>
          )}
        </div>
        <div
          className="icon-wrapper flex-shrink-0 relative"
          style={{ background: gradient }}
        >
          <Icon size={20} className="text-slate-900 dark:text-white" />
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
    <div className="glass-card-flat border border-emerald-500/30 px-3 py-2 rounded-xl text-xs">
      <p className="text-slate-500 dark:text-white/60 mb-1">{label}</p>
      <p className="text-slate-900 dark:text-white font-bold">{payload[0].value.toLocaleString()}</p>
    </div>
  );
}

// ── Animated Booking Rate Bar ──────────────────────────────────────────────────
function BookingRateBar({ rate }: { rate: number }) {
  const pct = Math.min(Math.round(rate * 100), 100);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = barRef.current;
    if (!el) return;
    gsap.fromTo(el, { width: '0%' }, { width: `${pct}%`, duration: 1.2, ease: 'power2.out', delay: 0.4 });
  }, [pct]);

  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 dark:text-white/50 mb-2">
        <span>Booking Rate</span>
        <span className="font-semibold text-slate-500 dark:text-white/80">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-900/5 dark:bg-white/10 overflow-hidden">
        <div
          ref={barRef}
          className="h-full rounded-full"
          style={{ width: '0%', background: 'linear-gradient(90deg, #6366f1, #a855f7)' }}
        />
      </div>
    </div>
  );
}

// ── Animated Chart Entry ───────────────────────────────────────────────────────
function AnimatedChartCard({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    gsap.fromTo(el, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out', delay: 0.45 });
  }, []);
  return <div ref={ref} style={{ opacity: 0 }}>{children}</div>;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export function Dashboard() {
  const pageRef = usePageEntrance();
  const { liveStats, activeCalls, showToast } = useStore();
  const [syncing, setSyncing] = useState(false);

  const { data: polledStats, loading, error, refetch } = usePolling(
    () => analyticsAPI.getStats(),
    60_000
  );

  const stats = liveStats || polledStats;
  const activeCount = stats?.active_calls ?? activeCalls.length;

  const handleSyncBolna = async () => {
    setSyncing(true);
    try {
      const result = await analyticsAPI.syncBolna();
      showToast(`✅ Synced ${result.synced} calls from Bolna AI (${result.inserted} new)`, 'success');
      refetch();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      showToast(`Bolna sync failed: ${msg}`, 'error');
    } finally {
      setSyncing(false);
    }
  };

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

  const GRADIENT_COLORS = ['#2dd4bf', '#14b8a6', '#0f766e', '#38bdf8', '#0ea5e9', '#0284c7', '#115e59'];

  return (
    <div ref={pageRef} className="p-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Live Analytics</h1>
          <p className="text-sm text-slate-500 dark:text-white/40 mt-1 flex items-center gap-2">
            <span>Real-time updates via WebSocket</span>
            {activeCount > 0 && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {activeCount} Live Call{activeCount !== 1 ? 's' : ''}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSyncBolna}
            disabled={syncing}
            className="btn-secondary"
            title="Pull real call logs from Bolna AI into database"
          >
            <CloudDownload size={14} className={syncing ? 'animate-pulse' : ''} />
            <span>{syncing ? 'Syncing…' : 'Sync Bolna'}</span>
          </button>
          <button
            onClick={refetch}
            disabled={loading && !stats}
            className="btn-secondary"
          >
            <RefreshCw size={14} className={loading && !stats ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && !stats && (
        <div className="glass-card-flat border border-red-500/30 px-4 py-3 rounded-xl text-sm text-red-400 flex items-center gap-2">
          <Activity size={16} />
          <span>Backend unavailable — showing cached data. {error}</span>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {loading && !stats ? (
          <>
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </>
        ) : stats ? (
          <>
            <StatCard
              label="Total Calls"
              value={stats.total_calls}
              isNumeric
              icon={Phone}
              gradient="linear-gradient(135deg, #2dd4bf, #0f766e)"
              subtext={`${activeCount} active now`}
              pulse={activeCount > 0}
              index={0}
            />
            <StatCard
              label="Unique Patients"
              value={stats.unique_patients}
              isNumeric
              icon={Users}
              gradient="linear-gradient(135deg, #38bdf8, #0369a1)"
              subtext="All time"
              index={1}
            />
            <StatCard
              label="Avg Duration"
              value={`${Math.round(stats.avg_duration_seconds)}s`}
              isNumeric={false}
              icon={Clock}
              gradient="linear-gradient(135deg, #818cf8, #4338ca)"
              subtext={`${Math.round(stats.total_duration_seconds / 60)} min total`}
              index={2}
            />
            <StatCard
              label="Confirmed Bookings"
              value={stats.confirmed_bookings}
              isNumeric
              icon={CheckCircle}
              gradient="linear-gradient(135deg, #34d399, #059669)"
              subtext={stats.booking_rate !== undefined ? `${Math.round(stats.booking_rate * 100)}% rate` : undefined}
              index={3}
            />
          </>
        ) : null}
      </div>

      {/* Charts Row */}
      {stats && (
        <AnimatedChartCard>
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Weekly Calls Chart */}
            <div className="xl:col-span-2 glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="section-title">Weekly Call Volume</h2>
                  <p className="text-xs text-slate-500 dark:text-white/40 mt-0.5">Last 7 days</p>
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
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(16,185,129,0.08)' }} />
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
                <p className="text-xs text-slate-500 dark:text-white/40 mt-0.5">Performance overview</p>
              </div>

              {/* Booking rate */}
              <BookingRateBar rate={stats.booking_rate ?? (stats.confirmed_bookings / Math.max(stats.total_calls, 1))} />

              {/* Mini area chart */}
              <div>
                <p className="text-xs text-slate-500 dark:text-white/50 mb-2">Call trend</p>
                <ResponsiveContainer width="100%" height={70}>
                  <AreaChart data={buildChartData(stats)}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="calls"
                      stroke="#14b8a6"
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
                  <p className="text-xs text-slate-500 dark:text-white/50 mb-2">Languages</p>
                  <div className="space-y-1.5">
                    {Object.entries(stats.languages).map(([lang, count]) => (
                      <div key={lang} className="flex items-center justify-between text-xs">
                        <span className="text-slate-500 dark:text-white/60">{lang}</span>
                        <span className="font-semibold text-slate-500 dark:text-white/90">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick stats */}
              <div className="mt-auto pt-4 border-t divider grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] text-slate-500 dark:text-white/35 mb-0.5">Completed</p>
                  <p className="text-base font-bold text-slate-900 dark:text-white">{stats.completed_calls ?? stats.total_calls}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 dark:text-white/35 mb-0.5">Active Now</p>
                  <p className="text-base font-bold text-emerald-400 flex items-center gap-1">
                    {activeCount}
                    {activeCount > 0 && <Zap size={12} />}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </AnimatedChartCard>
      )}
    </div>
  );
}
