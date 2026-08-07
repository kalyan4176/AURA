# --- Build Stage ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runtime Stage ---
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user and group for security
RUN groupadd -g 10001 aura && \
    useradd -u 10001 -g aura -d /app -s /sbin/nologin -c "AURA system user" aura

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/aura/.local
ENV PATH=/home/aura/.local/bin:$PATH
ENV PYTHONPATH=/app

# Setup directories with appropriate ownership
RUN mkdir -p /app/data /app/data/duckdb /app/data/uploads && \
    chown -R aura:aura /app

USER aura

# Copy code
COPY --chown=aura:aura . /app

EXPOSE 8000

CMD ["uvicorn", "app.presentation.main:app", "--host", "0.0.0.0", "--port", "8000"]
