import React, { useState } from 'react';
import {
  CalendarDays, Clock, Phone, User, Send, RefreshCw,
  XCircle, ArrowRightLeft, ChevronRight, Calendar,
  Loader2,
} from 'lucide-react';
import { bookingsAPI, calendarAPI } from '../services/api';
import { useApi } from '../hooks/useApi';
import { useStore } from '../store/useStore';
import type { PendingBooking } from '../types';

// ── Modal: Reschedule ──────────────────────────────────────────────────────────
interface RescheduleModalProps {
  booking: PendingBooking;
  onClose: () => void;
  onSuccess: () => void;
}

function RescheduleModal({ booking, onClose, onSuccess }: RescheduleModalProps) {
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [loading, setLoading] = useState(false);
  const { showToast } = useStore();

  const submit = async () => {
    if (!newDate || !newTime) {
      showToast('Please select both date and time', 'error');
      return;
    }
    setLoading(true);
    try {
      await bookingsAPI.reschedule({
        call_id:  booking.call_id,
        phone:    booking.phone,
        name:     booking.name ?? 'Patient',
        old_date: booking.date,
        new_date: newDate,
        new_time: newTime,
        treatment: booking.treatment,
      });
      showToast('Appointment rescheduled & WhatsApp sent ✓', 'success');
      onSuccess();
      onClose();
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'Reschedule failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div className="glass-card p-6 w-full max-w-md animate-fade-in">
        <div className="flex items-center gap-3 mb-6">
          <div className="icon-wrapper bg-gradient-brand">
            <ArrowRightLeft size={18} className="text-white" />
          </div>
          <div>
            <h2 className="section-title">Reschedule Appointment</h2>
            <p className="text-xs text-white/40 mt-0.5">{booking.name} · {booking.phone}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-white/50 mb-1.5">Current Date</label>
            <div className="input-field text-white/40 cursor-default">{booking.date}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">New Date</label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="input-field"
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">New Time</label>
              <input
                type="time"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                className="input-field"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
          <button onClick={submit} disabled={loading} className="btn-primary flex-1 justify-center">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRightLeft size={14} />}
            Reschedule
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Booking Card ───────────────────────────────────────────────────────────────
interface BookingCardProps {
  booking: PendingBooking;
  onRefetch: () => void;
}

function BookingCard({ booking, onRefetch }: BookingCardProps) {
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const { showToast } = useStore();

  const sendReminder = async () => {
    setSending(true);
    try {
      await bookingsAPI.sendReminder({
        call_id:   booking.call_id,
        phone:     booking.phone,
        name:      booking.name ?? 'Patient',
        date:      booking.date,
        time:      booking.time ?? '',
        treatment: booking.treatment,
        channel:   'whatsapp',
      });
      showToast('Reminder sent via WhatsApp ✓', 'success');
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'Failed to send reminder', 'error');
    } finally {
      setSending(false);
    }
  };

  const cancelBooking = async () => {
    if (!confirm(`Cancel ${booking.name ?? booking.phone}'s appointment on ${booking.date}?`)) return;
    setCancelling(true);
    try {
      await bookingsAPI.cancel({
        call_id: booking.call_id,
        phone:   booking.phone,
        name:    booking.name ?? 'Patient',
        date:    booking.date,
        time:    booking.time ?? '',
        reason:  'Cancelled via admin dashboard',
      });
      showToast('Appointment cancelled ✓', 'success');
      onRefetch();
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : 'Cancel failed', 'error');
    } finally {
      setCancelling(false);
    }
  };

  return (
    <>
      <div className="glass-card p-5 hover:border-indigo-500/30 group">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
              <User size={18} className="text-indigo-400" />
            </div>
            <div>
              <p className="font-semibold text-white text-sm">{booking.name ?? 'Unknown Patient'}</p>
              <div className="flex items-center gap-1.5 text-xs text-white/40 mt-0.5">
                <Phone size={10} />
                <span>{booking.phone}</span>
              </div>
            </div>
          </div>
          <span className={`badge-${booking.booking_status === 'confirmed' ? 'confirmed' : 'pending'}`}>
            {booking.booking_status ?? 'pending'}
          </span>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="flex items-center gap-2 text-xs text-white/50">
            <Calendar size={12} className="text-indigo-400" />
            <span>{booking.date}</span>
          </div>
          {booking.time && (
            <div className="flex items-center gap-2 text-xs text-white/50">
              <Clock size={12} className="text-purple-400" />
              <span>{booking.time}</span>
            </div>
          )}
          {booking.treatment && (
            <div className="flex items-center gap-2 text-xs text-white/50 col-span-2">
              <ChevronRight size={12} className="text-cyan-400" />
              <span>{booking.treatment}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-3 border-t divider">
          <button
            onClick={sendReminder}
            disabled={sending}
            className="btn-secondary flex-1 justify-center text-xs py-2"
          >
            {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
            Remind
          </button>
          <button
            onClick={() => setRescheduleOpen(true)}
            className="btn-secondary flex-1 justify-center text-xs py-2"
          >
            <ArrowRightLeft size={12} />
            Reschedule
          </button>
          <button
            onClick={cancelBooking}
            disabled={cancelling}
            className="btn-danger flex-1 justify-center text-xs py-2"
          >
            {cancelling ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />}
            Cancel
          </button>
        </div>
      </div>

      {rescheduleOpen && (
        <RescheduleModal
          booking={booking}
          onClose={() => setRescheduleOpen(false)}
          onSuccess={onRefetch}
        />
      )}
    </>
  );
}

// ── Today's Schedule ───────────────────────────────────────────────────────────
function TodaySchedule() {
  const { data: schedule, loading } = useApi(() => calendarAPI.getToday(), []);

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <CalendarDays size={16} className="text-indigo-400" />
        <h3 className="section-title text-base">Today's Schedule</h3>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1,2,3].map(i => <div key={i} className="h-10 rounded-lg animate-shimmer" />)}
        </div>
      ) : schedule?.appointments?.length === 0 ? (
        <p className="text-sm text-white/30 text-center py-6">No appointments today</p>
      ) : (
        <div className="space-y-2">
          {schedule?.appointments?.map((appt, idx) => (
            <div key={idx} className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
              <span className="text-xs font-semibold text-indigo-300 w-14">{appt.time}</span>
              <span className="text-xs text-white/70 truncate">{appt.summary}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Bookings Component ─────────────────────────────────────────────────────────
export function Bookings() {
  const { data, loading, refetch } = useApi(() => bookingsAPI.getPending(), []);
  const bookings: PendingBooking[] = data?.bookings ?? [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Bookings</h1>
          <p className="text-sm text-white/40 mt-1">
            {data?.total ?? 0} upcoming appointments
          </p>
        </div>
        <button onClick={refetch} disabled={loading} className="btn-secondary">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-6">
        {/* Booking cards */}
        <div>
          {loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1,2,3,4].map(i => (
                <div key={i} className="glass-card p-5 animate-shimmer h-48" />
              ))}
            </div>
          )}

          {!loading && bookings.length === 0 && (
            <div className="glass-card flex flex-col items-center justify-center py-20 text-white/30">
              <CalendarDays size={40} className="mb-3 opacity-40" />
              <p className="text-sm font-medium">No pending bookings</p>
              <p className="text-xs mt-1">New bookings will appear here</p>
            </div>
          )}

          {!loading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {bookings.map((booking) => (
                <BookingCard key={booking.call_id} booking={booking} onRefetch={refetch} />
              ))}
            </div>
          )}
        </div>

        {/* Today's schedule sidebar */}
        <div className="flex flex-col gap-4">
          <TodaySchedule />

          {/* Quick stats */}
          <div className="glass-card p-5">
            <h3 className="section-title text-base mb-4">Quick Stats</h3>
            <div className="space-y-3">
              {[
                { label: 'Total Pending', value: data?.total ?? 0, color: 'text-yellow-400' },
                { label: 'Confirmed', value: bookings.filter(b => b.booking_status === 'confirmed').length, color: 'text-emerald-400' },
                { label: 'Needs Attention', value: bookings.filter(b => b.booking_status !== 'confirmed').length, color: 'text-orange-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex items-center justify-between text-sm">
                  <span className="text-white/50">{label}</span>
                  <span className={`font-bold ${color}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
