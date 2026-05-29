# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import sentry_sdk
import structlog
from app.config import settings
from app.database import engine, AsyncSession
from app.models import Base
from app.scheduler import start_scheduler, stop_scheduler
from app.api.router import router as api_router

# Базовая настройка логирования (JSON для продакшена, Console для dev)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog, settings.LOG_LEVEL.upper(), structlog.INFO)
    ),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 Prizolov Sports AI starting up", version="4.01")
    
    # 1. Инициализация Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment="production" if not settings.DEBUG else "development"
        )
        log.info("Sentry monitoring initialized")

    # 2. Проверка/создание таблиц БД (в продакшене рекомендуется Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database schema validated")

    # 3. Запуск фоновых пайплайнов (APScheduler)
    asyncio.create_task(start_scheduler())
    log.info("Async scheduler started")

    yield  # Приложение обрабатывает запросы

    # 4. Корректное завершение
    await stop_scheduler()
    await engine.dispose()
    log.info("🛑 Prizolov Sports AI shut down cleanly")

# Инициализация FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version="4.01",
    description="AI-powered sports prediction engine with social sentiment & global data aggregation",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Подключение маршрутов
app.include_router(api_router, prefix="/api/v1")

# Healthcheck эндпоинты для Amvera Cloud / Kubernetes
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "4.01", "service": settings.APP_NAME}

@app.get("/ready")
async def readiness_check():
    # В будущем можно добавить проверку подключения к БД/Redis
    return {"status": "ready"}
