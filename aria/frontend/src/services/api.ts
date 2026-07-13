import axios from 'axios';
import type {
  Call,
  Analytics,
  Patient,
  PatientHistory,
  PendingBooking,
  SearchResult,
  TodaySchedule,
  HealthStatus,
} from '../types';

// ── Axios Instance ─────────────────────────────────────────────────────────────
// Uses the Vite proxy: /api → http://localhost:8000
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

// Request interceptor — log in dev
api.interceptors.request.use((config) => {
  if (import.meta.env.DEV) {
    console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  }
  return config;
});

// Response interceptor — normalize errors
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail || err.message || 'Unknown error';
    console.error(`[API Error] ${message}`);
    return Promise.reject(new Error(message));
  }
);

// ── Calls API ──────────────────────────────────────────────────────────────────
export const callsAPI = {
  getCall: async (callId: string): Promise<Call> => {
    const res = await api.get(`/calls/${callId}`);
    return res.data;
  },

  getTranscript: async (callId: string): Promise<{ call_id: string; status: string; turns: Call['turns'] }> => {
    const res = await api.get(`/calls/${callId}/transcript`);
    return res.data;
  },

  endCall: async (callId: string): Promise<unknown> => {
    const res = await api.post('/calls/end', { call_id: callId });
    return res.data;
  },
};

// ── Patients API ───────────────────────────────────────────────────────────────
export const patientsAPI = {
  getPatient: async (phone: string): Promise<Patient> => {
    const res = await api.get(`/patients/${encodeURIComponent(phone)}`);
    return res.data;
  },

  getHistory: async (phone: string, limit = 10): Promise<PatientHistory> => {
    const res = await api.get(`/patients/${encodeURIComponent(phone)}/history`, {
      params: { limit },
    });
    return res.data;
  },
};

// ── Bookings API ───────────────────────────────────────────────────────────────
export interface ReminderPayload {
  call_id: string;
  phone: string;
  name: string;
  date: string;
  time: string;
  treatment?: string;
  channel?: string;
}

export interface ReschedulePayload {
  call_id: string;
  phone: string;
  name: string;
  old_date: string;
  new_date: string;
  new_time: string;
  treatment?: string;
}

export interface CancelPayload {
  call_id: string;
  phone: string;
  name: string;
  date: string;
  time: string;
  reason?: string;
}

export const bookingsAPI = {
  getPending: async (): Promise<{ bookings: PendingBooking[]; total: number }> => {
    const res = await api.get('/bookings/pending');
    return res.data;
  },

  sendReminder: async (payload: ReminderPayload): Promise<unknown> => {
    const res = await api.post('/bookings/remind', payload);
    return res.data;
  },

  reschedule: async (payload: ReschedulePayload): Promise<unknown> => {
    const res = await api.post('/bookings/reschedule', payload);
    return res.data;
  },

  cancel: async (payload: CancelPayload): Promise<unknown> => {
    const res = await api.post('/bookings/cancel', payload);
    return res.data;
  },
};

// ── Analytics API ──────────────────────────────────────────────────────────────
export const analyticsAPI = {
  getStats: async (): Promise<Analytics> => {
    const res = await api.get('/analytics/stats');
    return res.data;
  },

  // Backend: GET /analytics/search?q=<query>&limit=<n>
  search: async (q = '', limit = 20): Promise<SearchResult> => {
    const res = await api.get('/analytics/search', { params: { q, limit } });
    return res.data;
  },
};

// ── Calendar API ───────────────────────────────────────────────────────────────
export const calendarAPI = {
  getToday: async (): Promise<TodaySchedule> => {
    const res = await api.get('/calendar/today');
    return res.data;
  },

  getSlots: async (date: string): Promise<{ date: string; available_slots: string[]; count: number }> => {
    const res = await api.post('/calendar/slots', { date });
    return res.data;
  },
};

// ── Health API ─────────────────────────────────────────────────────────────────
export const healthAPI = {
  check: async (): Promise<HealthStatus> => {
    const res = await api.get('/health');
    return res.data;
  },
};

export default api;
