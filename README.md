# AURA — Autonomous Unified Reasoning Analytics

AURA is a production-grade, enterprise-ready **Decision Intelligence Platform** built using a Python FastAPI modular monolith architecture and a React JS frontend. 

It enables organizations to ingest datasets, analyze data quality, run heavy statistical/ML calculations asynchronously, and build collaborative analytical reports backed by cost-optimized AI narration gateway decisions.

---

## 🚀 Architecture Overview

AURA enforces **Clean Architecture** patterns separating the domain layer, application services, infrastructure adapters, and presentation endpoints.

```
                  +-----------------------------------+
                  |        React JS Frontend          |
                  |  (Tailwind + ECharts + AG Grid)   |
                  +-----------------------------------+
                                    |
                            (REST HTTP / JSON)
                                    v
                  +-----------------------------------+
                  |          FastAPI Backend          |
                  |     (Uvicorn HTTP Web Nodes)      |
                  +-----------------------------------+
                    /        |              |        \
                   /         |              |         \
                  v          v              v          v
   +--------------+  +---------------+  +-------+  +---------------+
   | PostgreSQL   |  | In-Memory     |  | Redis |  | Local Ollama  |
   | (Metadata /  |  | DuckDB &      |  | Cache |  | / Cloud LLM   |
   | Workspace DB)|  | Polars Engine)|  | Broker|  | (Gemini) API  |
   +--------------+  +---------------+  +-------+  +---------------+
                                            |
                                            v
                                    +---------------+
                                    | Celery Worker |
                                    | (heavy stats /|
                                    | ML forecasting|
                                    +---------------+
```

---

## 🛠️ The 15 Core Engines Built

1. **Authentication Engine**: Secure registration and sessions using Argon2 hashing and JWT configurations.
2. **Workspace Engine**: Handles organizational boundaries and workspaces.
3. **Dataset Engine**: Manages uploads and converts CSV data to optimized Parquet.
4. **Metadata Engine**: Generates and stores column types, ranges, and structures.
5. **Data Quality Intelligence Engine**: Profiles missing columns, nulls, and duplicate values via Polars.
6. **Analytics Engine**: Direct SQL and analytics queries against Parquet files via in-memory DuckDB connections.
7. **Statistics Engine**: Async Celery tasks calculating Pearson/Spearman correlations and ANOVA/Welch T-Tests.
8. **Machine Learning Engine**: Outlier detection via Isolation Forests and time-series forecasting via Holt-Winters.
9. **Evidence Engine**: Formulates pre-computed numerical data into structured context JSON inputs.
10. **Knowledge Engine**: Hybrid context retrieval using keyword Jaccard overlap and local Ollama semantic embeddings.
11. **Interactive Report Engine**: Collaborative JSON document layouts mapping annotations and chat comments.
12. **Dashboard Engine**: Glowing dark-mode user interface utilizing virtualized AG Grid lists and Apache ECharts.
13. **AI Narrative Engine**: Automatic natural language chart summaries and report briefing narrations.
14. **Notification Engine**: Pushes data quality warnings when a dataset profiles below a 80% health rating.
15. **Monitoring Engine**: Displays real-time CPU/Memory usage, HTTP request latency averages, and cache hit metrics.

---

## 📦 Prerequisites

Ensure you have the following installed on your machine:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* [Node.js](https://nodejs.org/) (v18 or higher)
* [Python 3.10+](https://www.python.org/downloads/) (if running manually without Docker)
* [Ollama](https://ollama.com/) (optional, for local embedding models)

---

## ⚡ Quick Start (Docker Sandbox)

1. Double-click the launcher script in the project root:
   ```bash
   run_platform.bat
   ```
2. This starts all database containers, caching nodes, Celery brokers, background workers, and the Uvicorn web server in Docker.
3. It boots the React Vite portal on `http://localhost:5173`.
4. Open `http://localhost:5173` to register your first account and upload a dataset!

---

## 🔧 Manual Local Development

If you prefer to run the components manually without Docker:

### 1. Start Redis & PostgreSQL
Ensure you have active local instances of PostgreSQL and Redis running on their standard ports (`5432` and `6379`).

### 2. Configure and Run Backend
```bash
cd backend
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations / start Uvicorn
uvicorn app.presentation.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Run Celery Worker
In a separate terminal with active virtual environment:
```bash
cd backend
celery -A app.infrastructure.tasks.worker worker --loglevel=info
```

### 4. Run Frontend Portal
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing

To run the complete suite of 11 integration, unit, and performance tests:
```bash
cd backend
..\venv\Scripts\activate
python -m pytest tests
```

---

## ☁️ Production Cloud-Scale Variables

To scale past the free sandbox limits, duplicate `backend/.env` and update the following settings:
* **`DATABASE_URL`**: Point to a cloud PostgreSQL database (like **Supabase** Pro).
* **`REDIS_URL`**: Point to a serverless Redis database (like **Upstash**).
* **`GEMINI_API_KEY`**: Provide your cloud API key from **Google AI Studio** to run narration models.
* **`UPLOAD_DIR`**: Swap local folders for S3-compatible endpoints (like **Cloudflare R2**).
