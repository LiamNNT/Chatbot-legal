# Orchestrator Service Dockerfile
# Multi-stage build for smaller production image
#
# BUILD CONTEXT must be  backend/  (not backend/orchestrator/)
#   docker build -f orchestrator/Dockerfile -t orchestrator .
# This way both orchestrator/ and shared/ are available at build time.

# ── Build stage ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1) Install shared package first (rarely changes → good cache layer)
COPY shared/ /build/shared/
RUN pip install --no-cache-dir --user /build/shared

# 2) Install orchestrator requirements (without the `-e ../shared` line)
COPY orchestrator/requirements.txt /build/requirements.txt
RUN grep -v '^\-e' /build/requirements.txt | pip install --no-cache-dir --user -r /dev/stdin

# ── Production stage ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy orchestrator application code only
COPY orchestrator/app ./app
COPY orchestrator/config ./app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/api/v1/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
