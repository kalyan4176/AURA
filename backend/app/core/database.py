from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

import socket
from loguru import logger

db_url = settings.DATABASE_URL
is_postgres = "postgresql" in db_url
postgres_offline = False

if is_postgres:
    host = "localhost"
    port = 5432
    try:
        # Parse connection host
        if "@" in db_url:
            authority = db_url.split("@")[1].split("/")[0]
            if ":" in authority:
                host, port_str = authority.split(":")
                port = int(port_str)
            else:
                host = authority
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((host, port))
        s.close()
    except Exception:
        postgres_offline = True
        logger.warning(f"PostgreSQL target ({host}:{port}) is offline. Falling back to local SQLite: sqlite+aiosqlite:///./data/aura_prototype.db")
        db_url = "sqlite+aiosqlite:///./data/aura_prototype.db"

# Create asynchronous engine
connect_args = {}
if "postgresql" in db_url:
    import ssl
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    connect_args=connect_args,
    **({} if "sqlite" in db_url else {"pool_size": 20, "max_overflow": 10})
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide a transactional SQLAlchemy async session.

    Ensures that session is properly disposed and commits are rolled back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
