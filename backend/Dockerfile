# Backend Dockerfile for FastAPI + DuckDB
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# Copy application backend code
COPY backend /app/backend

# Create uploads directory
RUN mkdir -p /app/backend/data/uploads

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["python", "backend/start_server.py"]

