# Aria — Deployment Guide

> Production deployment options for the Aria Voice Receptionist API

---

## Option 1: Railway (Recommended — Free Tier Available)

Railway gives you Redis + Postgres + FastAPI all in one platform.

### Steps

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project (from ai-automation root)
railway init

# 4. Deploy
railway up

# 5. Add environment variables in Railway dashboard
#    → Settings → Variables → Add all from .env.example

# 6. Verify
railway logs
curl https://your-app.railway.app/health
```

### Railway Services to Add
1. **Redis** → Add Redis plugin from Railway dashboard
2. **PostgreSQL** → Add Postgres plugin from Railway dashboard
3. **FastAPI** → Deployed automatically from your repo

### Environment Variables in Railway
Set these in Railway Dashboard → Project → Variables:
```
OPENAI_API_KEY=...
GROQ_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
GOOGLE_CALENDAR_ID=primary
CLINIC_NAME=Naveen Advanced Dental Clinic
```

Railway automatically injects `REDIS_URL` and `DATABASE_URL` from its plugins.

---

## Option 2: Render (Free Tier)

### Steps

```bash
# 1. Push to GitHub first
git push origin main

# 2. Go to render.com → New → Web Service
# 3. Connect your GitHub repo
# 4. Set build command: pip install -r aria/requirements.txt
# 5. Set start command: uvicorn aria.main:app --host 0.0.0.0 --port $PORT
# 6. Add environment variables in Render dashboard
# 7. Add Redis: Render Dashboard → New → Redis
# 8. Add Postgres: Render Dashboard → New → PostgreSQL
```

---

## Option 3: Docker (Self-Hosted / VPS)

### Prerequisites
- Docker + Docker Compose installed
- VPS with 1GB+ RAM (DigitalOcean, Hetzner, etc.)

### Deploy

```bash
# 1. SSH into your VPS
ssh user@your-vps-ip

# 2. Clone your repo
git clone https://github.com/LokeshGaddam14/ai-automation-engineer-journey
cd ai-automation/aria

# 3. Create .env from template
cp .env.example .env
nano .env    # Fill in your credentials

# 4. Build and start
docker-compose up -d

# 5. Check status
docker-compose ps
docker-compose logs -f aria-api

# 6. Verify
curl http://localhost:8000/health
```

### Expose with Nginx (Optional)

```nginx
# /etc/nginx/sites-available/aria
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/aria /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## Option 4: Local Development (ngrok tunnel)

For testing with Bolna webhooks on your laptop:

```bash
# Terminal 1: Start Aria API
cd ai-automation
uvicorn aria.main:app --reload --port 8000

# Terminal 2: Start ngrok tunnel
ngrok http 8000

# Copy the ngrok URL: https://xxxxx.ngrok-free.app
# Add to Bolna agent webhook settings: https://xxxxx.ngrok-free.app/webhook/bolna
```

---

## Post-Deployment Verification

```bash
# Health check
curl https://your-app.railway.app/health

# Expected response:
# {"status":"healthy","service":"Aria Voice Receptionist API",...}

# Test start call
curl -X POST https://your-app.railway.app/calls/start \
  -H "Content-Type: application/json" \
  -d '{"call_id":"test001","patient_phone":"+916302008804"}'

# Get available calendar slots
curl -X POST https://your-app.railway.app/calendar/slots \
  -H "Content-Type: application/json" \
  -d '{"date":"tomorrow"}'

# View analytics
curl https://your-app.railway.app/analytics/stats

# Check API docs
open https://your-app.railway.app/docs
```

---

## Bolna Integration

1. Deploy Aria API (any option above)
2. Copy your deployed URL
3. Go to [Bolna Dashboard](https://app.bolna.dev)
4. Open your agent settings
5. Set webhook URL: `https://your-app.com/webhook/bolna`
6. Configure post-call webhook to fire on call end
7. Test with a real call!

---

## Monitoring

### Docker Health Checks

```bash
docker-compose ps          # Service status
docker stats               # CPU/memory usage
docker-compose logs -f     # Live logs
```

### API Monitoring

```bash
# Install httpie for cleaner output
pip install httpie

# Check all endpoints
http GET https://your-app.com/health
http GET https://your-app.com/analytics/stats
http GET https://your-app.com/bookings/pending
```

---

## Troubleshooting

### Redis Connection Failed
```bash
# Check if Redis is running
docker-compose ps redis
docker-compose logs redis

# Test connection
redis-cli -h localhost ping
```

### Postgres Connection Failed
```bash
# Check Postgres
docker-compose ps postgres
docker-compose logs postgres

# Connect manually
psql postgresql://aria:ariapass123@localhost:5432/aria_db
```

### Twilio Not Sending
```bash
# Verify credentials
python -c "
from aria.integrations.twilio_client import TwilioNotifier
n = TwilioNotifier()
print('Mock mode:', n._mock_mode)
"
```

### Google Calendar Not Working
```bash
# Check credentials
ls aria/integrations/credentials.json   # Should exist
ls aria/integrations/token.json         # Created on first auth
```
