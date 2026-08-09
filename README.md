# ⚡ AURA — Enterprise Decision Intelligence & Privacy-First Analytics Platform

> **AURA** (Autonomous RAG Analytics) is a high-performance decision intelligence platform engineered for zero-trust enterprise environments. It combines **local DuckDB SQL execution**, **privacy-shielded RAG architecture**, **persistent multi-turn AI chat**, and **intelligent dynamic visualization engines**.

---

## 🌟 Unique Selling Propositions (USPs)

### 1. 🔒 Zero-Leak Privacy Shield (Zero LLM Training Guarantee)
* **100% Local Data Isolation**: Raw dataset rows (CSVs / Parquet files) are saved in private binary storage on your machine and are **NEVER transmitted to external LLMs** or used for AI foundation model training.
* **Ephemeral RAG Metadata Architecture**: AURA executes heavy calculations locally via DuckDB. Only small, aggregated numerical summaries (e.g., `"Average Amount = $122.21"`) or sampled coordinate vectors (up to 400 points) are passed as prompt context.

### 2. ⚡ Millisecond Local Text-to-SQL Engine (DuckDB + Polars)
* **Instant Sub-10ms Queries**: Translates natural language questions into optimized DuckDB SQL queries.
* **Scales to Millions of Rows**: Process massive datasets (such as the 284,807-row Kaggle Credit Card Fraud dataset) without hitting API token rate limits, token cost bloat, or memory crashes.

### 3. 📊 Attribute-Type Smart Visualizer
* **Intelligent Chart Selection**: Automatically inspects column cardinality and data types before rendering to prevent squished visualizations.
* **Categorical vs Continuous Pairings**: Converts categorical pairings (e.g. `Class` vs `Amount`) into clean grouped **Bar Charts**, while continuous metrics (`Amount` vs `Time`) render high-density **Scatter Plots** using ECharts.
* **AI Suggested Visualizations**: Features one-click recommendation chips for instant high-impact chart generation.

### 4. 💬 Persistent Multi-Turn AI Chat & Exportable Reports
* **Multi-Turn Conversation Threads**: Ask follow-up questions, run iterative analysis, and review persistent chat history per workspace or dataset.
* **One-Click Markdown Exporter**: Download any AI analysis report, SQL query breakdown, or executive decision impact summary directly as a formatted `.md` file.

### 5. 🤖 Multi-Algorithm Machine Learning Outlier Detection
* **Integrated ML Suite**: Built-in **Isolation Forest**, **Local Outlier Factor (LOF)**, and **One-Class SVM** spatial tree algorithms.
* **Smart Fallback Engine**: Automatically switch to local statistical summaries if network rate limits occur.

### 6. 🌐 Relational Multi-Dataset Workspace Joins
* **Cross-Dataset Relational SQL**: Connect multiple files (`customers.parquet` + `transactions.parquet`) and perform relational SQL joins via natural language.

---

## 🛠️ Technology Stack

* **Frontend**: React 18, Vite, ECharts (`echarts-for-react`), TailwindCSS, Lucide Icons, TanStack React Query.
* **Backend**: FastAPI, Python 3.13, DuckDB, Polars, Scikit-learn, SQLAlchemy, Uvicorn.
* **AI / RAG Layer**: Google Gemini API (Ephemeral RAG Context Mode), Text-to-SQL Compiler Engine.
* **Database**: SQLite (Local Prototype) / PostgreSQL (Neon Enterprise).

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* Python 3.10+
* Node.js 18+

### 2. Backend Setup
```bash
# Navigate to project root
cd "AURA"

# Activate virtual environment
venv\Scripts\activate

# Start FastAPI backend server
python backend/start_server.py
```
*Backend runs on `http://127.0.0.1:8000`.*

### 3. Frontend Setup
```bash
# Navigate to frontend folder
cd frontend

# Install dependencies & start Vite dev server
npm install
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## 🧪 Running Automated Tests

AURA includes unit and integration tests covering telemetry, budget manager, data ingestion, and alerting pipelines:

```bash
# Run pytest suite
venv\Scripts\pytest backend/tests/
```

---

## 📄 License

Internal Enterprise Proprietary & Academic Project — Built with Google Antigravity & DeepMind Agentic Coding Architecture.
