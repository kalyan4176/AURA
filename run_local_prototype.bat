@echo off
title AURA Platform Local Sandbox (Offline Prototype)
echo =================================================================
echo  AURA Platform Local Launcher (Self-Healing Zero-Dependency Mode)
echo =================================================================
echo.
echo [1/2] Launching self-healing FastAPI backend (using SQLite and in-memory cache)...
start "AURA Backend Service" cmd /k "cd backend && call venv\Scripts\activate && uvicorn app.presentation.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Bootstrapping React JS Frontend Portal...
start "AURA Frontend Portal" cmd /k "cd frontend && npm run dev"

echo.
echo =================================================================
echo  AURA services are booting up in separate terminal windows.
echo  - REST API Swagger Docs: http://localhost:8000/docs
echo  - React Frontend Portal: http://localhost:5173
echo =================================================================
echo.
pause
