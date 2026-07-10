$json = '{
  "call_status": "completed",
  "execution_id": "TEST-002",
  "agent_id": "agent-123",
  "to_number": "+91-9999999999",
  "conversation_time": 180,
  "summary": "Patient Rahul Kumar confirmed appointment for teeth cleaning on Monday July 14 at 10 AM. Booking confirmed successfully.",
  "transcript": "Hi my name is Rahul Kumar. I would like to book an appointment for teeth cleaning. Certainly! I have scheduled you for Monday July 14th at 10 AM. Your appointment is confirmed. Your booking ID is BLN1234567.",
  "created_at": "2026-07-10T09:00:00Z",
  "extraction_details": {
    "patient_name": "Rahul Kumar",
    "appointment_date": "Monday July 14",
    "appointment_time": "10:00 AM",
    "treatment": "Teeth Cleaning",
    "email": "lokeshgaddam2514@gmail.com",
    "booking_id": "BLN1234567"
  }
}'

Write-Host "Sending test payload to n8n webhook..." -ForegroundColor Cyan

try {
  $response = Invoke-RestMethod -Uri "https://arjintina.app.n8n.cloud/webhook-test/bolna-dental-webhook" -Method POST -ContentType "application/json" -Body $json
  Write-Host "SUCCESS! Response:" -ForegroundColor Green
  $response | ConvertTo-Json
} catch {
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Make sure you clicked 'Execute Workflow' in n8n first!" -ForegroundColor Yellow
}
