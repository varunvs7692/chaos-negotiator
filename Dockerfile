# Multi-stage Dockerfile for Chaos Negotiator

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Copy project files
COPY pyproject.toml .
COPY chaos_negotiator ./chaos_negotiator
COPY README.md .
COPY LICENSE .

# Build wheels
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -e .

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels

# Install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache /wheels/*

# Copy application code
COPY chaos_negotiator /app/chaos_negotiator
COPY LICENSE /app/
COPY README.md /app/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import chaos_negotiator; print('healthy')" || exit 1

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command - run FastAPI server
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["chaos_negotiator.server:app", "--host", "0.0.0.0", "--port", "8000"]
