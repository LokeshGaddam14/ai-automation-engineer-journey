import React, { useState } from 'react';
import {
  Building2, Phone, MapPin, Globe, Activity,
  Key, Bell, Calendar, Users, ChevronRight,
  CheckCircle2, XCircle, Loader2, RefreshCw,
  Wifi,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { healthAPI } from '../services/api';
import { useApi } from '../hooks/useApi';

// ── Setting Section ────────────────────────────────────────────────────────────
function SettingSection({ title, icon: Icon, children }: {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="icon-wrapper bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/20">
          <Icon size={18} className="text-indigo-400" />
        </div>
        <h2 className="section-title">{title}</h2>
      </div>
      {children}
    </div>
  );
}

// ── Info Row ───────────────────────────────────────────────────────────────────
function InfoRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between py-3 border-b divider last:border-0">
      <span className="text-sm text-white/50">{label}</span>
      <span className={`text-sm text-white/80 font-medium text-right max-w-[240px] truncate ${mono ? 'font-mono text-xs' : ''}`}>
        {value}
      </span>
    </div>
  );
}

// ── API Health Widget ──────────────────────────────────────────────────────────
function ApiHealthWidget() {
  const { data: health, loading, error, refetch } = useApi(() => healthAPI.check(), []);

  return (
    <SettingSection title="API Health" icon={Activity}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {loading ? (
            <Loader2 size={16} className="animate-spin text-indigo-400" />
          ) : error ? (
            <XCircle size={16} className="text-red-400" />
          ) : (
            <CheckCircle2 size={16} className="text-emerald-400" />
          )}
          <span className={`text-sm font-semibold ${error ? 'text-red-400' : loading ? 'text-white/40' : 'text-emerald-400'}`}>
            {loading ? 'Checking…' : error ? 'Unreachable' : health?.status ?? 'Healthy'}
          </span>
        </div>
        <button onClick={refetch} className="btn-secondary py-1.5 px-3 text-xs">
          <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          Re-check
        </button>
      </div>

      {health && (
        <div className="space-y-0">
          <InfoRow label="Service"   value={health.service} />
          <InfoRow label="Version"   value={health.version} />
          <InfoRow label="Timestamp" value={new Date(health.timestamp).toLocaleString()} />
          {Object.entries(health.components).map(([key, val]) => (
            <InfoRow key={key} label={key.charAt(0).toUpperCase() + key.slice(1)} value={val} mono />
          ))}
        </div>
      )}

      {error && (
        <div className="glass-card-flat border border-red-500/20 px-4 py-3 rounded-xl text-sm text-red-400">
          <p>Cannot reach FastAPI at <code className="font-mono text-xs">localhost:8000</code></p>
          <p className="text-xs text-red-400/70 mt-1">Make sure the backend is running: <code className="font-mono">uvicorn aria.main:app --reload</code></p>
        </div>
      )}
    </SettingSection>
  );
}

// ── Toggle Setting ─────────────────────────────────────────────────────────────
function ToggleSetting({ label, description, checked, onChange }: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b divider last:border-0">
      <div>
        <p className="text-sm font-medium text-white/80">{label}</p>
        {description && <p className="text-xs text-white/40 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors duration-200 flex-shrink-0 ${
          checked ? 'bg-indigo-600' : 'bg-white/10'
        }`}
      >
        <span
          className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? 'translate-x-5' : 'translate-x-0.5'
          }`}
        />
      </button>
    </div>
  );
}

// ── Settings Component ─────────────────────────────────────────────────────────
export function Settings() {
  const [notifications, setNotifications] = useState({
    whatsapp:     true,
    sms:          false,
    email:        false,
    callAlerts:   true,
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Settings</h1>
        <p className="text-sm text-white/40 mt-1">Dashboard and system configuration</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Clinic Info */}
        <SettingSection title="Clinic Information" icon={Building2}>
          <div className="space-y-0">
            <InfoRow label="Clinic Name" value="Naveen Advanced Dental Clinic" />
            <InfoRow label="Location"    value="Hyderabad, Telangana" />
            <InfoRow label="Timezone"    value="Asia/Kolkata (IST UTC+5:30)" />
            <InfoRow label="Language"    value="English, Hindi, Telugu" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {[
              { icon: Phone, text: '+91-XXXXXXXXXX' },
              { icon: MapPin, text: 'Hyderabad' },
              { icon: Globe, text: 'naveen-dental.in' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.08] text-xs text-white/50">
                <Icon size={11} className="text-indigo-400" />
                {text}
              </div>
            ))}
          </div>
        </SettingSection>

        {/* API Health */}
        <ApiHealthWidget />

        {/* Twilio Config */}
        <SettingSection title="Twilio Configuration" icon={Key}>
          <div className="space-y-0">
            <InfoRow label="Account SID"   value="AC••••••••••••••••••••••••••••••••" mono />
            <InfoRow label="Phone Number"  value="From .env file" />
            <InfoRow label="WhatsApp"      value="Enabled (Sandbox)" />
            <InfoRow label="SMS"           value="Enabled" />
          </div>
          <div className="mt-4 glass-card-flat border border-yellow-500/20 px-3 py-2.5 rounded-xl text-xs text-yellow-400/80">
            <p className="flex items-center gap-2">
              <ChevronRight size={12} />
              Credentials loaded from <code className="font-mono">.env</code> — edit there to update
            </p>
          </div>
        </SettingSection>

        {/* Calendar */}
        <SettingSection title="Google Calendar Sync" icon={Calendar}>
          <div className="space-y-0">
            <InfoRow label="Calendar ID" value="primary" mono />
            <InfoRow label="Sync Status" value="Active" />
            <InfoRow label="Auth Method" value="OAuth 2.0 token.json" />
            <InfoRow label="Timezone"    value="Asia/Kolkata" />
          </div>
          <div className="mt-4 flex items-center gap-2 px-3 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400">
            <CheckCircle2 size={13} />
            Calendar integration active
          </div>
        </SettingSection>

        {/* Notification Preferences */}
        <SettingSection title="Notification Preferences" icon={Bell}>
          <div>
            <ToggleSetting
              label="WhatsApp Reminders"
              description="Send appointment reminders via WhatsApp"
              checked={notifications.whatsapp}
              onChange={(v) => setNotifications((s) => ({ ...s, whatsapp: v }))}
            />
            <ToggleSetting
              label="SMS Notifications"
              description="Fallback SMS for patients without WhatsApp"
              checked={notifications.sms}
              onChange={(v) => setNotifications((s) => ({ ...s, sms: v }))}
            />
            <ToggleSetting
              label="Email Alerts"
              description="Email summary reports"
              checked={notifications.email}
              onChange={(v) => setNotifications((s) => ({ ...s, email: v }))}
            />
            <ToggleSetting
              label="Live Call Alerts"
              description="Show badge when active calls are running"
              checked={notifications.callAlerts}
              onChange={(v) => setNotifications((s) => ({ ...s, callAlerts: v }))}
            />
          </div>
        </SettingSection>

        {/* Stack Info */}
        <SettingSection title="Tech Stack" icon={Wifi}>
          <div className="space-y-0">
            <InfoRow label="AI Agent"  value="LangGraph + OpenAI GPT-4o" />
            <InfoRow label="Voice"     value="Bolna AI" />
            <InfoRow label="Memory"    value="Redis (session) + PostgreSQL" />
            <InfoRow label="Phone"     value="Twilio" />
            <InfoRow label="Calendar"  value="Google Calendar API" />
            <InfoRow label="Frontend"  value="React + TypeScript + Vite" />
            <InfoRow label="Backend"   value="FastAPI + Uvicorn" />
          </div>
        </SettingSection>

        {/* User Management placeholder */}
        <SettingSection title="User Management" icon={Users}>
          <div className="text-center py-8 text-white/30">
            <Users size={32} className="mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium">Single-user mode</p>
            <p className="text-xs mt-1.5">Multi-user support coming in Day 20</p>
          </div>
        </SettingSection>
      </div>
    </div>
  );
}
