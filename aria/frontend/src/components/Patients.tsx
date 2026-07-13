import React, { useState } from 'react';
import {
  Search, User, Phone, Calendar, Clock,
  Activity, ChevronRight, Loader2, Users,
} from 'lucide-react';
import { patientsAPI } from '../services/api';
import type { Patient, PatientHistory } from '../types';

// ── Patient Info Card ──────────────────────────────────────────────────────────
function PatientInfoCard({ patient }: { patient: Patient }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-4 mb-6">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)' }}
        >
          <User size={28} className="text-white" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{patient.name ?? 'Unknown Patient'}</h2>
          <div className="flex items-center gap-1.5 text-sm text-white/40 mt-1">
            <Phone size={12} />
            <span className="font-mono">{patient.phone}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="text-center p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <p className="text-2xl font-extrabold text-white">{patient.total_calls}</p>
          <p className="text-[11px] text-white/40 mt-0.5">Total Calls</p>
        </div>
        <div className="text-center p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <p className="text-sm font-bold text-white truncate">
            {patient.last_call
              ? new Date(patient.last_call).toLocaleDateString('en', { month: 'short', day: 'numeric' })
              : '—'}
          </p>
          <p className="text-[11px] text-white/40 mt-0.5">Last Call</p>
        </div>
        <div className="text-center p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <p className="text-sm font-bold text-white truncate">{patient.last_treatment ?? '—'}</p>
          <p className="text-[11px] text-white/40 mt-0.5">Last Treatment</p>
        </div>
      </div>
    </div>
  );
}

// ── Patient History Table ──────────────────────────────────────────────────────
function PatientHistoryTable({ history }: { history: PatientHistory }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
        <h3 className="section-title text-base">Call History ({history.total})</h3>
      </div>

      {history.calls.length === 0 ? (
        <div className="text-center py-10 text-white/30">
          <Activity size={24} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">No call history</p>
        </div>
      ) : (
        <div className="divide-y" style={{ borderColor: 'rgba(99,102,241,0.08)' }}>
          {history.calls.map((call, idx) => (
            <div key={idx} className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.03] transition-colors">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
                <Phone size={13} className="text-indigo-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white/80 truncate">{call.treatment ?? 'General Inquiry'}</p>
                <p className="text-[11px] font-mono text-white/30 truncate">{call.call_id}</p>
              </div>
              <div className="flex items-center gap-4 text-xs text-white/40 flex-shrink-0">
                <span className="flex items-center gap-1">
                  <Calendar size={10} />
                  {call.date
                    ? new Date(call.date).toLocaleDateString('en', { month: 'short', day: 'numeric', year: '2-digit' })
                    : '—'}
                </span>
                {call.duration_seconds && (
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {Math.round(call.duration_seconds)}s
                  </span>
                )}
                <span className={`badge-${call.booking_status === 'confirmed' ? 'confirmed' : 'pending'}`}>
                  {call.booking_status ?? 'pending'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Patients Component ─────────────────────────────────────────────────────────
export function Patients() {
  const [phone, setPhone] = useState('');
  const [searchedPhone, setSearchedPhone] = useState('');
  const [patient, setPatient] = useState<Patient | null>(null);
  const [history, setHistory] = useState<PatientHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;

    setLoading(true);
    setError(null);
    setPatient(null);
    setHistory(null);
    setSearchedPhone(phone.trim());

    try {
      const [p, h] = await Promise.all([
        patientsAPI.getPatient(phone.trim()),
        patientsAPI.getHistory(phone.trim(), 20),
      ]);
      setPatient(p);
      setHistory(h);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Patient not found');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Patients</h1>
        <p className="text-sm text-white/40 mt-1">Search patient records by phone number</p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="flex gap-3 max-w-lg">
        <div className="relative flex-1">
          <Phone size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+91 XXXXXXXXXX or local number…"
            className="input-field pl-9"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Search
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="max-w-lg glass-card-flat border border-red-500/30 px-4 py-3 rounded-xl text-sm text-red-400 flex items-center gap-2">
          <ChevronRight size={14} />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4">
          <div className="glass-card p-6 animate-shimmer h-36" />
          <div className="glass-card animate-shimmer h-64" />
        </div>
      )}

      {/* Patient data */}
      {!loading && patient && (
        <div className="space-y-4 animate-fade-in">
          <PatientInfoCard patient={patient} />
          {history && <PatientHistoryTable history={history} />}
        </div>
      )}

      {/* Empty state */}
      {!loading && !patient && !error && (
        <div className="glass-card flex flex-col items-center justify-center py-20 text-white/20">
          <Users size={48} className="mb-4 opacity-40" />
          <p className="text-lg font-medium">Patient Directory</p>
          <p className="text-sm mt-1.5">Enter a phone number above to search patient records</p>
        </div>
      )}
    </div>
  );
}
