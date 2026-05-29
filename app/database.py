# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
import structlog

log = structlog.get_logger()

# Асинхронный движок (настройки пула оптимизированы под PostgreSQL/Amvera)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """
    FastAPI Dependency: открытие и безопасное закрытие сессии БД.
    Автоматически выполняет rollback при исключениях.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            log.error("DB transaction failed, rolled back")
            raise
        finally:
            await session.close()
