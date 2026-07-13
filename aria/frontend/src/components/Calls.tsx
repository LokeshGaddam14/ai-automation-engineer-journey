import React, { useState } from 'react';
import {
  Phone, Calendar, Clock, Search, Eye, EyeOff,
  User, Mic, MessageSquare, RefreshCw, X, Download, Table2,
} from 'lucide-react';
import { analyticsAPI, callsAPI } from '../services/api';
import { useApi } from '../hooks/useApi';
import { useStore } from '../store/useStore';
import { exportCallsToCSV, exportCallsToPDF } from '../utils/export';
import type { Call } from '../types';


// ── Status badge ───────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    confirmed: 'badge-confirmed',
    pending:   'badge-pending',
    active:    'badge-active',
    cancelled: 'badge-cancelled',
  };
  return (
    <span className={map[status] ?? 'badge-pending'}>
      {status}
    </span>
  );
}

// ── Format duration ────────────────────────────────────────────────────────────
function fmtDuration(seconds?: number) {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// ── Transcript Panel ───────────────────────────────────────────────────────────
function TranscriptPanel({ callId, onClose }: { callId: string; onClose: () => void }) {
  const { data: transcript, loading } = useApi(
    () => callsAPI.getTranscript(callId),
    [callId]
  );

  return (
    <div className="glass-card p-5 flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="section-title text-base">Transcript</h3>
          <p className="text-[11px] text-white/40 mt-0.5 font-mono truncate max-w-[160px]">{callId}</p>
        </div>
        <button onClick={onClose} className="btn-secondary p-2 rounded-lg">
          <X size={14} />
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {transcript?.turns?.length === 0 && (
            <p className="text-sm text-white/30 text-center py-8">No transcript available</p>
          )}
          {transcript?.turns?.map((turn, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-xl text-xs ${
                turn.role === 'agent'
                  ? 'bg-indigo-500/10 border border-indigo-500/20'
                  : turn.role === 'system'
                  ? 'bg-white/5 border border-white/10'
                  : 'bg-white/[0.06] border border-white/10'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                {turn.role === 'agent' ? (
                  <Mic size={10} className="text-indigo-400" />
                ) : (
                  <User size={10} className="text-white/50" />
                )}
                <span className="font-semibold uppercase tracking-wide text-[10px] text-white/50">
                  {turn.role}
                </span>
                {turn.timestamp && (
                  <span className="ml-auto text-[10px] text-white/25">
                    {new Date(turn.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
              <p className="text-white/80 leading-relaxed">{turn.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Calls Component ────────────────────────────────────────────────────────────
export function Calls() {
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { showToast } = useStore();

  const { data: results, loading, refetch } = useApi(
    () => analyticsAPI.search(query, 30),
    [query]
  );

  const calls: Call[] = (results?.results ?? []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    refetch();
  };

  const copyId = (id: string) => {
    navigator.clipboard.writeText(id).then(() => showToast('Call ID copied', 'success'));
  };

  const handleExportCSV = () => {
    if (calls.length === 0) { showToast('No data to export', 'error'); return; }
    exportCallsToCSV(calls, 'aria-calls.csv');
    showToast('CSV exported', 'success');
  };

  const handleExportPDF = () => {
    if (calls.length === 0) { showToast('No data to export', 'error'); return; }
    exportCallsToPDF(calls);
    showToast('PDF exported', 'success');
  };

  return (
    <div className="p-6 h-full flex flex-col gap-4 min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="page-title">Calls</h1>
          <p className="text-sm text-white/40 mt-1">
            {results?.total ?? 0} records found
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExportCSV} className="btn-secondary">
            <Table2 size={14} /> CSV
          </button>
          <button onClick={handleExportPDF} className="btn-secondary">
            <Download size={14} /> PDF
          </button>
          <button onClick={refetch} disabled={loading} className="btn-secondary">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3 flex-shrink-0">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by phone number or patient name…"
            className="input-field pl-9"
          />
        </div>
        <button type="submit" className="btn-primary">
          <Search size={14} />
          Search
        </button>
      </form>

      {/* Content */}
      <div className={`flex-1 grid gap-4 min-h-0 ${selectedId ? 'grid-cols-[1fr_360px]' : 'grid-cols-1'}`}>
        {/* Call list */}
        <div className="glass-card flex flex-col min-h-0">
          {/* Table header */}
          <div
            className="grid grid-cols-[1fr_120px_80px_80px_40px] gap-4 px-5 py-3 border-b text-[11px] font-semibold uppercase tracking-wider text-white/30 flex-shrink-0"
            style={{ borderColor: 'rgba(99,102,241,0.1)' }}
          >
            <span>Patient / Call ID</span>
            <span>Date</span>
            <span>Duration</span>
            <span>Status</span>
            <span></span>
          </div>

          {/* Table body */}
          <div className="flex-1 overflow-y-auto divide-y" style={{ borderColor: 'rgba(99,102,241,0.08)' }}>
            {loading && (
              <div className="flex items-center justify-center py-16">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {!loading && calls.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-white/30">
                <MessageSquare size={32} className="mb-3 opacity-50" />
                <p className="text-sm">No calls found</p>
                <p className="text-xs mt-1">Try a different search query</p>
              </div>
            )}

            {!loading && calls.map((call) => (
              <div
                key={call.call_id}
                className={`
                  grid grid-cols-[1fr_120px_80px_80px_40px] gap-4 px-5 py-4 items-center
                  cursor-pointer transition-colors duration-150
                  ${selectedId === call.call_id
                    ? 'bg-indigo-500/10 border-l-2 border-indigo-500'
                    : 'hover:bg-white/[0.03] border-l-2 border-transparent'
                  }
                `}
                onClick={() => setSelectedId(selectedId === call.call_id ? null : call.call_id)}
              >
                {/* Patient info */}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
                      <Phone size={12} className="text-indigo-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white/90 truncate">{call.patient_phone}</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); copyId(call.call_id); }}
                        className="text-[11px] text-white/30 font-mono truncate hover:text-indigo-400 transition-colors"
                      >
                        {call.call_id.slice(0, 20)}…
                      </button>
                    </div>
                  </div>
                </div>

                {/* Date */}
                <div className="flex items-center gap-1.5 text-xs text-white/50">
                  <Calendar size={12} />
                  {call.started_at
                    ? new Date(call.started_at).toLocaleDateString('en', { month: 'short', day: 'numeric' })
                    : '—'}
                </div>

                {/* Duration */}
                <div className="flex items-center gap-1.5 text-xs text-white/50">
                  <Clock size={12} />
                  {fmtDuration(call.duration_seconds)}
                </div>

                {/* Status */}
                <StatusBadge status={call.booking_status ?? 'pending'} />

                {/* Eye toggle */}
                <button className="text-white/30 hover:text-indigo-400 transition-colors">
                  {selectedId === call.call_id ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Transcript panel */}
        {selectedId && (
          <TranscriptPanel callId={selectedId} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  );
}
