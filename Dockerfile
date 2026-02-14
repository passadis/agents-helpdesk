# ============================================================
# Multi-target Dockerfile for agents-helpdesk
#
# Build the web app:   docker build --target web -t helpdesk-web .
# Build the worker:    docker build --target worker -t helpdesk-worker .
# ============================================================

# ---------- common base ----------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# ---------- web (FastAPI + uvicorn) ----------
FROM base AS web

EXPOSE 8000

# Health-check: Container Apps / load-balancers will probe this
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- worker (Service Bus listener) ----------
FROM base AS worker

# No port exposed — the worker only polls Service Bus
CMD ["python", "-m", "app.worker"]
