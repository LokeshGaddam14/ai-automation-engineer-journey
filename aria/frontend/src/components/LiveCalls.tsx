import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Phone, PhoneOff, Mic, User, Activity, Wifi, WifiOff,
  Download, FileText, Clock, Radio, Signal, Zap, RefreshCw,
} from 'lucide-react';
import type { LiveCall, QualityMetrics } from '../types';
import { exportLiveCallTranscriptToPDF } from '../utils/export';
import { useStore } from '../store/useStore';

// ── Mock Data Seed ──────────────────────────────────────────────────────────────
function makeMockCall(): LiveCall {
  const names = ['లోకేష్ గడ్డం', 'Priya Sharma', 'Ravi Kumar', 'Anjali Reddy'];
  const phones = ['+916302008804', '+919876543210', '+917890123456', '+918765432109'];
  const idx = Math.floor(Math.random() * names.length);
  return {
    call_id: `call_mock_${Date.now()}`,
    patient_phone: phones[idx],
    started_at: new Date().toISOString(),
    duration: Math.floor(Math.random() * 200) + 10,
    status: 'active',
    transcript: [
      { role: 'agent',   text: 'Hello! Welcome to Naveen Advanced Dental Clinic. How can I help you today?', timestamp: new Date().toISOString() },
      { role: 'patient', text: 'Hi, I would like to book an appointment for a checkup.', timestamp: new Date().toISOString() },
      { role: 'agent',   text: 'Of course! I can help you with that. What date works best for you?', timestamp: new Date().toISOString() },
    ],
    quality: { audio_quality: 'good', latency_ms: 42, bandwidth_mbps: 0.85 },
  };
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function QualityBadge({ metrics }: { metrics: QualityMetrics }) {
  const colors: Record<string, string> = {
    good: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    fair: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    poor: 'text-red-400 bg-red-500/10 border-red-500/30',
    unknown: 'text-white/40 bg-white/5 border-white/10',
  };
  const cls = colors[metrics.audio_quality] ?? colors.unknown;
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full border ${cls}`}>
      {metrics.audio_quality}
    </span>
  );
}

function Duration({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return <span className="font-mono text-sm">{m}:{String(s).padStart(2, '0')}</span>;
}

function TranscriptBubble({ role, text, timestamp }: { role: 'agent' | 'patient'; text: string; timestamp: string }) {
  const isAgent = role === 'agent';
  return (
    <div className={`flex ${isAgent ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
          isAgent
            ? 'bg-indigo-500/15 border border-indigo-500/20 text-white/90'
            : 'bg-white/[0.07] border border-white/10 text-white/80'
        }`}
      >
        <div className="flex items-center gap-1.5 mb-1.5">
          {isAgent ? <Mic size={9} className="text-indigo-400" /> : <User size={9} className="text-white/50" />}
          <span className="font-bold uppercase text-[9px] tracking-widest text-white/40">
            {isAgent ? 'Aria' : 'Patient'}
          </span>
          <span className="ml-auto text-[9px] text-white/20">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <p>{text}</p>
      </div>
    </div>
  );
}

function CallCard({
  call,
  selected,
  onSelect,
}: {
  call: LiveCall;
  selected: boolean;
  onSelect: () => void;
}) {
  const statusColors: Record<LiveCall['status'], string> = {
    ringing: 'text-amber-400',
    active:  'text-emerald-400',
    ended:   'text-white/30',
  };
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
        selected
          ? 'bg-indigo-500/15 border-indigo-500/40'
          : 'bg-white/[0.03] border-white/8 hover:border-indigo-500/20 hover:bg-white/[0.05]'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
              call.status === 'ended' ? 'bg-white/5' : 'bg-indigo-500/20'
            }`}
          >
            {call.status === 'ended' ? (
              <PhoneOff size={14} className="text-white/30" />
            ) : (
              <Phone size={14} className="text-indigo-400" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white/90 truncate">{call.patient_phone}</p>
            <p className="text-[11px] text-white/35 font-mono truncate">{call.call_id.slice(0, 22)}…</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className={`text-[10px] font-bold uppercase tracking-wide flex items-center gap-1 ${statusColors[call.status]}`}>
            {call.status === 'active' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
            {call.status}
          </span>
          <Duration seconds={call.duration} />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <QualityBadge metrics={call.quality} />
        <span className="text-[10px] text-white/30 flex items-center gap-1">
          <Signal size={9} /> {call.quality.latency_ms}ms
        </span>
        <span className="text-[10px] text-white/30 flex items-center gap-1">
          <Zap size={9} /> {call.quality.bandwidth_mbps.toFixed(2)} Mbps
        </span>
      </div>
    </button>
  );
}

// ── LiveCalls Page ─────────────────────────────────────────────────────────────

export function LiveCalls() {
  const { showToast } = useStore();
  const [calls, setCalls] = useState<LiveCall[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [useMock, setUseMock] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  const selectedCall = calls.find((c) => c.call_id === selectedId) ?? null;

  // Auto-scroll transcript to bottom
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [selectedCall?.transcript.length]);

  // Connect WebSocket to backend live-calls stream
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setWsStatus('connecting');

    const ws = new WebSocket('ws://localhost:8000/ws/live-calls');
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
      showToast('Connected to live call stream', 'success');
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as { type: string; data: unknown };
        if (msg.type === 'active_calls') {
          setCalls(msg.data as LiveCall[]);
        } else if (msg.type === 'call_update') {
          const updated = msg.data as LiveCall;
          setCalls((prev) =>
            prev.some((c) => c.call_id === updated.call_id)
              ? prev.map((c) => (c.call_id === updated.call_id ? updated : c))
              : [updated, ...prev]
          );
        } else if (msg.type === 'call_ended') {
          const ended = msg.data as { call_id: string };
          setCalls((prev) =>
            prev.map((c) => (c.call_id === ended.call_id ? { ...c, status: 'ended' as const } : c))
          );
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      setWsStatus('disconnected');
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
    };
  }, [showToast]);

  // Load mock data for demo
  const loadMockData = () => {
    const mocks = [makeMockCall(), { ...makeMockCall(), status: 'ringing' as const, duration: 5 }];
    setCalls(mocks);
    setSelectedId(mocks[0].call_id);
    setUseMock(true);
    showToast('Loaded mock live call data', 'info');
  };

  useEffect(() => {
    connectWS();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWS]);

  const activeCount = calls.filter((c) => c.status === 'active' || c.status === 'ringing').length;

  return (
    <div className="p-6 h-full flex flex-col gap-4 min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Radio size={20} className="text-emerald-400" />
            Live Calls
            {activeCount > 0 && (
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
                {activeCount} active
              </span>
            )}
          </h1>
          <p className="text-sm text-white/40 mt-1">Real-time call monitoring via WebSocket</p>
        </div>

        <div className="flex items-center gap-3">
          {/* WS status indicator */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border ${
            wsStatus === 'connected'
              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
              : wsStatus === 'connecting'
              ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
              : 'text-white/30 bg-white/5 border-white/10'
          }`}>
            {wsStatus === 'connected' ? <Wifi size={12} /> : wsStatus === 'connecting' ? <Activity size={12} className="animate-pulse" /> : <WifiOff size={12} />}
            {wsStatus}
          </div>

          {wsStatus === 'disconnected' && (
            <button onClick={connectWS} className="btn-secondary">
              <RefreshCw size={14} /> Reconnect
            </button>
          )}

          <button onClick={loadMockData} className="btn-secondary">
            <Zap size={14} /> Demo Data
          </button>
        </div>
      </div>

      {/* Banner when using mock */}
      {useMock && (
        <div className="glass-card-flat border border-amber-500/30 px-4 py-2.5 rounded-xl text-xs text-amber-400 flex items-center gap-2 flex-shrink-0">
          <Zap size={12} />
          Showing mock demo data. Connect Bolna to see real calls. Set <code className="px-1 py-0.5 rounded bg-amber-500/10">BOLNA_WEBHOOK_URL=http://localhost:8000/webhooks/bolna</code> in your Bolna agent.
        </div>
      )}

      {/* Empty state */}
      {calls.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
            <Phone size={28} className="text-indigo-400 opacity-50" />
          </div>
          <div>
            <p className="text-white/50 font-medium">No active calls</p>
            <p className="text-xs text-white/30 mt-1">Waiting for incoming Bolna voice calls…</p>
          </div>
          <button onClick={loadMockData} className="btn-primary">
            <Zap size={14} /> Load Demo Data
          </button>
        </div>
      )}

      {/* Main content */}
      {calls.length > 0 && (
        <div className="flex-1 grid grid-cols-[300px_1fr] gap-4 min-h-0">
          {/* Call list */}
          <div className="flex flex-col gap-2 overflow-y-auto pr-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-white/30 px-1">
              {calls.length} call{calls.length !== 1 ? 's' : ''}
            </p>
            {calls.map((call) => (
              <CallCard
                key={call.call_id}
                call={call}
                selected={selectedId === call.call_id}
                onSelect={() => setSelectedId(call.call_id)}
              />
            ))}
          </div>

          {/* Detail panel */}
          {selectedCall ? (
            <div className="glass-card flex flex-col min-h-0">
              {/* Panel header */}
              <div className="flex items-center justify-between px-5 py-4 border-b flex-shrink-0" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
                <div>
                  <h3 className="section-title">{selectedCall.patient_phone}</h3>
                  <p className="text-[11px] text-white/35 font-mono mt-0.5">{selectedCall.call_id}</p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Metrics */}
                  <div className="flex items-center gap-3 mr-4">
                    <div className="text-center">
                      <p className="text-[9px] text-white/30 uppercase tracking-wide">Latency</p>
                      <p className="text-xs font-bold text-white/80">{selectedCall.quality.latency_ms}ms</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[9px] text-white/30 uppercase tracking-wide">BW</p>
                      <p className="text-xs font-bold text-white/80">{selectedCall.quality.bandwidth_mbps.toFixed(2)} Mbps</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[9px] text-white/30 uppercase tracking-wide">Duration</p>
                      <p className="text-xs font-bold text-white/80 flex items-center gap-1">
                        <Clock size={9} />
                        <Duration seconds={selectedCall.duration} />
                      </p>
                    </div>
                  </div>

                  <QualityBadge metrics={selectedCall.quality} />

                  <button
                    onClick={() => exportLiveCallTranscriptToPDF(selectedCall)}
                    className="btn-secondary py-1.5 px-3 text-xs"
                    title="Export transcript as PDF"
                  >
                    <FileText size={12} /> PDF
                  </button>

                  {selectedCall.recording_url && (
                    <a
                      href={selectedCall.recording_url}
                      download
                      className="btn-secondary py-1.5 px-3 text-xs"
                    >
                      <Download size={12} /> Recording
                    </a>
                  )}
                </div>
              </div>

              {/* Transcript */}
              <div ref={transcriptRef} className="flex-1 overflow-y-auto p-5 space-y-3">
                {selectedCall.transcript.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-white/30">
                    <Mic size={24} className="opacity-40" />
                    <p className="text-sm">Waiting for conversation…</p>
                  </div>
                )}
                {selectedCall.transcript.map((turn, i) => (
                  <TranscriptBubble key={i} {...turn} />
                ))}
                {selectedCall.status === 'active' && (
                  <div className="flex justify-start">
                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl px-4 py-2.5 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-card flex items-center justify-center text-white/30">
              <p className="text-sm">Select a call to view transcript</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
