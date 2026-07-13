import Papa from 'papaparse';
import jsPDF from 'jspdf';
import type { Call, LiveCall } from '../types';

// ── CSV Export ─────────────────────────────────────────────────────────────────

export function exportCallsToCSV(calls: Call[], filename = 'aria-calls.csv') {
  const rows = calls.map((c) => ({
    'Call ID':        c.call_id,
    'Patient Phone':  c.patient_phone,
    'Patient Name':   (c.extracted_data?.patient_name as string) ?? c.name ?? '—',
    'Date':           c.started_at ? new Date(c.started_at).toLocaleString() : '—',
    'Duration (s)':   c.duration_seconds ?? 0,
    'Booking Status': c.booking_status,
    'Treatment':      (c.extracted_data?.treatment as string) ?? '—',
    'Appointment Date': (c.extracted_data?.appointment_date as string) ?? '—',
    'Appointment Time': (c.extracted_data?.appointment_time as string) ?? '—',
  }));

  const csv = Papa.unparse(rows);
  downloadText(csv, filename, 'text/csv');
}

export function exportTranscriptToCSV(callId: string, turns: Call['turns'], filename?: string) {
  const rows = turns.map((t, i) => ({
    '#':        i + 1,
    'Role':     t.role,
    'Message':  t.content,
    'Time':     t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : '—',
  }));
  const csv = Papa.unparse(rows);
  downloadText(csv, filename ?? `transcript-${callId}.csv`, 'text/csv');
}

// ── PDF Export ─────────────────────────────────────────────────────────────────

export function exportCallsToPDF(calls: Call[], title = 'Aria Call Report') {
  const doc = new jsPDF({ orientation: 'landscape' });

  // Header
  doc.setFillColor(99, 102, 241);
  doc.rect(0, 0, doc.internal.pageSize.getWidth(), 22, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(title, 14, 14);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 20);

  // Column headers
  const cols = ['Phone', 'Name', 'Date', 'Duration', 'Status', 'Treatment'];
  const colWidths = [45, 40, 42, 28, 28, 45];
  let x = 14;
  let y = 32;

  doc.setFillColor(30, 30, 50);
  doc.rect(14, y - 5, doc.internal.pageSize.getWidth() - 28, 8, 'F');
  doc.setTextColor(180, 180, 220);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'bold');
  cols.forEach((col, i) => {
    doc.text(col, x, y);
    x += colWidths[i];
  });

  y += 6;
  doc.setFont('helvetica', 'normal');

  calls.forEach((call, idx) => {
    if (y > doc.internal.pageSize.getHeight() - 20) {
      doc.addPage();
      y = 20;
    }

    // Alternate row shading
    if (idx % 2 === 0) {
      doc.setFillColor(240, 240, 255);
      doc.rect(14, y - 4, doc.internal.pageSize.getWidth() - 28, 7, 'F');
    }

    doc.setTextColor(40, 40, 60);
    doc.setFontSize(8);
    x = 14;

    const row = [
      call.patient_phone,
      (call.extracted_data?.patient_name as string) ?? call.name ?? '—',
      call.started_at ? new Date(call.started_at).toLocaleDateString() : '—',
      call.duration_seconds ? `${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s` : '—',
      call.booking_status,
      (call.extracted_data?.treatment as string) ?? '—',
    ];

    row.forEach((val, i) => {
      doc.text(String(val).slice(0, 20), x, y);
      x += colWidths[i];
    });

    y += 7;
  });

  // Footer
  doc.setTextColor(150, 150, 150);
  doc.setFontSize(7);
  doc.text(
    `Aria Dental AI — Total records: ${calls.length}`,
    14,
    doc.internal.pageSize.getHeight() - 8
  );

  doc.save('aria-calls-report.pdf');
}

export function exportLiveCallTranscriptToPDF(call: LiveCall) {
  const doc = new jsPDF();

  doc.setFillColor(99, 102, 241);
  doc.rect(0, 0, doc.internal.pageSize.getWidth(), 22, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(13);
  doc.setFont('helvetica', 'bold');
  doc.text('Call Transcript', 14, 13);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text(`ID: ${call.call_id}  |  Phone: ${call.patient_phone}  |  ${new Date(call.started_at).toLocaleString()}`, 14, 20);

  let y = 32;

  call.transcript.forEach((turn) => {
    if (y > doc.internal.pageSize.getHeight() - 20) {
      doc.addPage();
      y = 14;
    }

    const isAgent = turn.role === 'agent';
    doc.setFillColor(isAgent ? 220 : 240, isAgent ? 225 : 240, isAgent ? 255 : 245);
    const textLines = doc.splitTextToSize(turn.text, 160);
    const boxH = textLines.length * 5 + 8;
    doc.roundedRect(isAgent ? 14 : 30, y - 4, 160, boxH, 2, 2, 'F');

    doc.setTextColor(isAgent ? 60 : 30, isAgent ? 60 : 30, isAgent ? 150 : 80);
    doc.setFontSize(7.5);
    doc.setFont('helvetica', 'bold');
    doc.text(isAgent ? '🤖 Aria' : '👤 Patient', isAgent ? 14 : 30, y);

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(40, 40, 40);
    doc.text(textLines, isAgent ? 14 : 30, y + 5);

    y += boxH + 4;
  });

  doc.save(`transcript-${call.call_id}.pdf`);
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function downloadText(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url  = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href     = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
