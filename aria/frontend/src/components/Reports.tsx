import React, { useState, useMemo } from 'react';
import {
  Download, FileText, Table2, RefreshCw, Filter,
  TrendingUp, Clock, Phone, CheckCircle, Users, BarChart3,
} from 'lucide-react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { analyticsAPI } from '../services/api';
import { useApi } from '../hooks/useApi';
import { exportCallsToCSV, exportCallsToPDF } from '../utils/export';
import { useStore } from '../store/useStore';
import type { Call, Analytics } from '../types';

// ── Colour Palette ─────────────────────────────────────────────────────────────
const COLORS = ['#6366f1', '#a855f7', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmtDuration(s: number) {
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card-flat border border-indigo-500/30 px-3 py-2 rounded-xl text-xs">
      <p className="text-white/60 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-white font-bold">{p.name}: {p.value.toLocaleString()}</p>
      ))}
    </div>
  );
}

// ── Metric Card ────────────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, icon: Icon, color }: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-white/50 mb-1">{label}</p>
          <p className="text-2xl font-extrabold text-white">{value}</p>
          {sub && <p className="text-[11px] text-white/35 mt-1">{sub}</p>}
        </div>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: color }}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
    </div>
  );
}

// ── Reports Component ──────────────────────────────────────────────────────────
export function Reports() {
  const { showToast } = useStore();

  // Filters
  const [dateRange, setDateRange] = useState<'24h' | '7d' | '30d' | 'all'>('7d');
  const [statusFilter, setStatusFilter] = useState<'all' | 'confirmed' | 'pending' | 'cancelled'>('all');

  const { data: stats, loading: statsLoading, refetch: refetchStats } = useApi(
    () => analyticsAPI.getStats(),
    []
  );

  const { data: searchResult, loading: callsLoading, refetch: refetchCalls } = useApi(
    () => analyticsAPI.search('', 200),
    []
  );

  const allCalls: Call[] = searchResult?.results ?? [];

  // Filter calls
  const filteredCalls = useMemo(() => {
    const now = Date.now();
    const cutoffs: Record<string, number> = {
      '24h': now - 86_400_000,
      '7d':  now - 7 * 86_400_000,
      '30d': now - 30 * 86_400_000,
      'all': 0,
    };
    const cut = cutoffs[dateRange] ?? 0;

    return allCalls.filter((c) => {
      const ts = c.started_at ? new Date(c.started_at).getTime() : 0;
      if (ts < cut) return false;
      if (statusFilter !== 'all' && c.booking_status !== statusFilter) return false;
      return true;
    });
  }, [allCalls, dateRange, statusFilter]);

  // Derived metrics
  const totalDuration = filteredCalls.reduce((sum, c) => sum + (c.duration_seconds ?? 0), 0);
  const confirmed     = filteredCalls.filter((c) => c.booking_status === 'confirmed').length;
  const conversionRate = filteredCalls.length > 0 ? (confirmed / filteredCalls.length) * 100 : 0;
  const uniquePhones  = new Set(filteredCalls.map((c) => c.patient_phone)).size;

  // Status distribution for pie chart
  const statusDist = useMemo(() => {
    const groups: Record<string, number> = {};
    filteredCalls.forEach((c) => {
      const k = c.booking_status ?? 'none';
      groups[k] = (groups[k] ?? 0) + 1;
    });
    return Object.entries(groups).map(([name, value]) => ({ name, value }));
  }, [filteredCalls]);

  // Daily call volume for bar chart
  const dailyVolume = useMemo(() => {
    if (!stats?.by_date || stats.by_date.length === 0) return [];
    const slice = dateRange === '24h' ? 1 : dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 60;
    return stats.by_date.slice(-slice).map((d) => ({
      date: new Date(d.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      calls: d.count,
    }));
  }, [stats, dateRange]);

  // Duration histogram buckets
  const durationBuckets = useMemo(() => {
    const buckets = [
      { name: '< 30s', min: 0,   max: 30  },
      { name: '30–60s', min: 30,  max: 60  },
      { name: '1–3m',  min: 60,  max: 180 },
      { name: '3–5m',  min: 180, max: 300 },
      { name: '> 5m',  min: 300, max: Infinity },
    ];
    return buckets.map((b) => ({
      name: b.name,
      calls: filteredCalls.filter((c) => {
        const d = c.duration_seconds ?? 0;
        return d >= b.min && d < b.max;
      }).length,
    }));
  }, [filteredCalls]);

  const handleRefresh = () => { refetchStats(); refetchCalls(); };

  const handleExportCSV = () => {
    if (filteredCalls.length === 0) { showToast('No data to export', 'error'); return; }
    exportCallsToCSV(filteredCalls, `aria-calls-${dateRange}.csv`);
    showToast('CSV exported successfully', 'success');
  };

  const handleExportPDF = () => {
    if (filteredCalls.length === 0) { showToast('No data to export', 'error'); return; }
    exportCallsToPDF(filteredCalls, `Aria Call Report — ${dateRange}`);
    showToast('PDF exported successfully', 'success');
  };

  const loading = statsLoading || callsLoading;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <BarChart3 size={20} className="text-indigo-400" />
            Reports & Export
          </h1>
          <p className="text-sm text-white/40 mt-1">
            {filteredCalls.length} records · {dateRange} window
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={handleRefresh} disabled={loading} className="btn-secondary">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={handleExportCSV} className="btn-secondary">
            <Table2 size={14} /> CSV
          </button>
          <button onClick={handleExportPDF} className="btn-primary">
            <Download size={14} /> PDF Report
          </button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Date range */}
        <div className="flex items-center gap-1 glass-card-flat border border-white/10 rounded-xl p-1">
          <Filter size={12} className="text-white/30 ml-2" />
          {(['24h', '7d', '30d', 'all'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setDateRange(r)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                dateRange === r ? 'bg-indigo-500 text-white' : 'text-white/50 hover:text-white'
              }`}
            >
              {r === 'all' ? 'All time' : r}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1 glass-card-flat border border-white/10 rounded-xl p-1">
          {(['all', 'confirmed', 'pending', 'cancelled'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                statusFilter === s ? 'bg-indigo-500 text-white' : 'text-white/50 hover:text-white'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard label="Filtered Calls"  value={filteredCalls.length}        sub="in selected range"  icon={Phone}        color="linear-gradient(135deg,#6366f1,#4f46e5)" />
        <MetricCard label="Unique Patients" value={uniquePhones}                sub="distinct phones"    icon={Users}        color="linear-gradient(135deg,#06b6d4,#0891b2)" />
        <MetricCard label="Avg Duration"    value={fmtDuration(Math.round(totalDuration / Math.max(filteredCalls.length, 1)))} sub="per call"  icon={Clock}        color="linear-gradient(135deg,#f59e0b,#d97706)" />
        <MetricCard label="Conversion Rate" value={`${conversionRate.toFixed(1)}%`} sub={`${confirmed} confirmed`} icon={CheckCircle} color="linear-gradient(135deg,#10b981,#059669)" />
      </div>

      {/* Conversion progress bar */}
      <div className="glass-card p-5">
        <div className="flex justify-between text-xs text-white/50 mb-3">
          <span className="font-semibold text-white/70">Booking Conversion Rate</span>
          <span className="font-bold text-white">{conversionRate.toFixed(1)}%</span>
        </div>
        <div className="h-3 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{ width: `${conversionRate}%`, background: 'linear-gradient(90deg, #6366f1, #a855f7, #10b981)' }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-white/25 mt-2">
          <span>{confirmed} confirmed</span>
          <span>{filteredCalls.length - confirmed} not booked</span>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Daily volume */}
        {dailyVolume.length > 0 && (
          <div className="xl:col-span-2 glass-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="section-title">Daily Call Volume</h2>
                <p className="text-xs text-white/40 mt-0.5">Last {dateRange}</p>
              </div>
              <TrendingUp size={14} className="text-emerald-400" />
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dailyVolume} barSize={20}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(99,102,241,0.1)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
                <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
                  {dailyVolume.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Status distribution pie */}
        {statusDist.length > 0 && (
          <div className="glass-card p-5">
            <h2 className="section-title mb-4">Status Distribution</h2>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={statusDist} dataKey="value" cx="50%" cy="50%" outerRadius={65} innerRadius={35}>
                  {statusDist.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-2 mt-3">
              {statusDist.map((d, i) => (
                <div key={i} className="flex items-center gap-1.5 text-[11px]">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="text-white/60 capitalize">{d.name}</span>
                  <span className="text-white/90 font-bold">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Duration histogram */}
      <div className="glass-card p-5">
        <h2 className="section-title mb-4">Call Duration Histogram</h2>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={durationBuckets} barSize={40}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(99,102,241,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
            <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
              {durationBuckets.map((_, i) => (
                <Cell key={i} fill="#6366f1" fillOpacity={0.7 + i * 0.06} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Export controls */}
      <div className="glass-card p-5">
        <h2 className="section-title mb-4">Export Data</h2>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleExportCSV} className="btn-secondary flex-1 justify-center py-3">
            <Table2 size={16} />
            <span>Export {filteredCalls.length} calls as CSV</span>
          </button>
          <button onClick={handleExportPDF} className="btn-primary flex-1 justify-center py-3">
            <FileText size={16} />
            <span>Export PDF Report</span>
          </button>
        </div>
        <p className="text-[11px] text-white/30 mt-3">
          Exports include: call ID, phone, patient name, date, duration, status, treatment, and appointment details.
        </p>
      </div>
    </div>
  );
}
