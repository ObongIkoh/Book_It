# =========================
#  Builder stage
# =========================
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =========================
#  Final stage
# =========================
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user (security best practice)
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . /app

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check (use curl instead of python+requests)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with Gunicorn + Uvicorn workers for production
CMD ["/opt/venv/bin/gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "1"]

