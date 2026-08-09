# Backend Dockerfile for FastAPI + DuckDB
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies directly
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    duckdb \
    polars \
    scikit-learn \
    sqlalchemy \
    aiosqlite \
    pydantic \
    pydantic-settings \
    python-multipart \
    google-generativeai \
    loguru \
    python-dotenv \
    pandas \
    numpy \
    pytest \
    "passlib[argon2]" \
    pyjwt


# Copy application backend code
COPY backend /app/backend

# Create uploads directory
RUN mkdir -p /app/backend/data/uploads

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["python", "backend/start_server.py"]

