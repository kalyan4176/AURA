from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import time
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import settings
from app.core.database import engine, Base
from app.presentation.api import auth, datasets, query, analytics, reports, knowledge, notifications, system

app = FastAPI(
    title="AURA (Autonomous Unified Reasoning Analytics)",
    description="Production-grade enterprise Decision Intelligence API.",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to trusted origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_init():
    """Initializes tables on startup if in development to speed up developer setup."""
    logger.info("AURA Platform starting up...")
    if settings.ENVIRONMENT == "development":
        logger.info("Development environment detected. Auto-creating database tables if missing.")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Observability: Instruments request duration and log headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    # Track latency in SystemMonitor
    from app.core.observability import system_monitor
    system_monitor.record_api_call(process_time)
    
    # Structured logging of API latency
    logger.info(
        f"API Request: {request.method} {request.url.path} "
        f"| Status: {response.status_code} | Duration: {process_time:.4f}s"
    )
    return response


# Register APIs
app.include_router(auth.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(system.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Centralized exception controller preventing server details leak in production."""
    logger.error(f"Global unhandled exception occurred: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system support."}
    )


@app.get("/health", tags=["System Controls"])
async def health_check():
    """Liveness probe indicator for Docker/Kubernetes container scheduling."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "service": "aura-backend-monolith"
    }
