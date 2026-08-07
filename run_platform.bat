@echo off
title AURA Platform Orchestrator
echo =================================================================
echo  AURA (Autonomous Unified Reasoning Analytics) Platform Launcher
echo =================================================================
echo.

echo [1/2] Spinning up Postgres, Redis, Celery, and Uvicorn in Docker...
start "AURA Backend Services" cmd /k "cd backend && docker compose up --build"

echo.
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
