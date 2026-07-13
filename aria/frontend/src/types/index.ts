// ── Core Domain Types ──────────────────────────────────────────────────────────

export interface Turn {
  role: 'agent' | 'patient' | 'system';
  content: string;
  timestamp: string;
  extracted_data?: Record<string, unknown>;
}

export interface Call {
  call_id: string;
  patient_phone: string;
  started_at: string;
  ended_at?: string;
  duration_seconds?: number;
  extracted_data: Record<string, unknown>;
  turns: Turn[];
  booking_status: 'confirmed' | 'pending' | 'cancelled' | 'none';
  state?: string;
  name?: string;
}

export interface Patient {
  phone: string;
  name?: string;
  total_calls: number;
  last_call?: string;
  last_treatment?: string;
}

export interface PatientHistory {
  phone: string;
  calls: PatientCall[];
  total: number;
}

export interface PatientCall {
  call_id: string;
  date: string;
  treatment?: string;
  name?: string;
  booking_status?: string;
  duration_seconds?: number;
}

export interface Analytics {
  total_calls: number;
  total_duration_seconds: number;
  avg_duration_seconds: number;
  confirmed_bookings: number;
  unique_patients: number;
  booking_rate?: number;
  // Additional backend fields
  completed_calls?: number;
  active_calls?: number;
  languages?: Record<string, number>;
  by_date?: Array<{ date: string; count: number }>;
}

export interface PendingBooking {
  call_id: string;
  phone: string;
  name?: string;
  date: string;
  time?: string;
  treatment?: string;
  booking_status?: string;
}

export interface SearchResult {
  query: string;
  results: Call[];
  total: number;
}

export interface CalendarSlot {
  time: string;
  available: boolean;
}

export interface TodaySchedule {
  date: string;
  appointments: CalendarAppointment[];
}

export interface CalendarAppointment {
  time: string;
  summary: string;
  duration?: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'error';
  service: string;
  version: string;
  timestamp: string;
  components: Record<string, string>;
}

// ── UI State Types ─────────────────────────────────────────────────────────────

export type Page = 'dashboard' | 'calls' | 'bookings' | 'patients' | 'settings' | 'live-calls' | 'reports';

export type StatusBadge = 'confirmed' | 'pending' | 'active' | 'cancelled' | 'none';

// ── Bolna / Live Call Types ────────────────────────────────────────────────────

export interface TranscriptTurn {
  role: 'agent' | 'patient';
  text: string;
  timestamp: string;
}

export interface QualityMetrics {
  audio_quality: 'good' | 'fair' | 'poor' | 'unknown';
  latency_ms: number;
  bandwidth_mbps: number;
}

export interface LiveCall {
  call_id: string;
  patient_phone: string;
  started_at: string;
  duration: number;          // seconds elapsed
  status: 'ringing' | 'active' | 'ended';
  transcript: TranscriptTurn[];
  quality: QualityMetrics;
  recording_url?: string;
}
