# ── Aria Voice Receptionist — Dockerfile ──────────────────────────────────────
# Multi-stage build for minimal production image.
#
# Build: docker build -t aria-api .
# Run:   docker run -p 8000:8000 --env-file .env aria-api

FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (Docker layer cache optimization)
COPY aria/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY aria/ ./aria/

# Create non-root user for security
RUN addgroup --system aria && adduser --system --group aria
RUN chown -R aria:aria /app
USER aria

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["python", "-m", "uvicorn", "aria.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
