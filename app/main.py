# ============================================
# Prizolov Sports AI - Setup
# Version: 4.02 (CORS & Startup Diagnostics Hotfix)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    """Управление жизненным циклом приложения: старт → работа → остановка"""
    log.info("🚀 Prizolov Sports AI starting up", version="4.02")
    
    # 1. Инициализация Sentry (мониторинг ошибок)
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment="production" if not settings.DEBUG else "development"
        )
        log.info("🔍 Sentry monitoring initialized")

    # 2. Проверка/создание таблиц БД с детальным логированием ошибок
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Маскируем чувствительные данные в логе
        safe_url = settings.DATABASE_URL
        if "@" in safe_url:
            safe_url = safe_url.split("@")[0].split(":")[0] + ":***@" + safe_url.split("@")[1]
        log.info("✅ Database schema validated", url=safe_url)
    except Exception as e:
        log.error("❌ Database connection failed", error=str(e), url=safe_url)
        raise  # Позволит Amvera увидеть ошибку и не переводить статус в Running

    # 3. Запуск фоновых пайплайнов (APScheduler)
    asyncio.create_task(start_scheduler())
    log.info("📅 Async scheduler started")

    yield  # Приложение обрабатывает запросы

    # 4. Корректное завершение работы
    await stop_scheduler()
    await engine.dispose()
    log.info("🛑 Prizolov Sports AI shut down cleanly")

# Инициализация FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version="4.02",
    description="AI-powered sports prediction engine with social sentiment & global data aggregation",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# 🔐 CORS Middleware — разрешает запросы с фронтенда prizolov.ru и Amvera-домена
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://prizolov.ru",
        "https://*.prizolov.ru",
        "https://prizolov-sports-dmandreyanov.amvera.io",  # Ваш Amvera-домен
        "http://localhost:3000",   # Локальная разработка фронтенда
        "http://localhost:8000",   # Локальный запуск API
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],      # Разрешаем GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],      # Разрешаем любые заголовки
    expose_headers=["*"],     # Позволяем фронтенду читать ответы
)

# Подключение маршрутов API v1
app.include_router(api_router, prefix="/api/v1")

# 🔗 Эндпоинт для совместимости с существующим фронтендом (POST /api/state)
@app.post("/api/state")
async def frontend_state():
    """
    Эндпоинт для интеграции с текущим фронтендом prizolov.ru.
    Возвращает структуру, ожидаемую скриптом loadPrizolovLivePost().
    """
    return {
        "match_info": None,  # Заполняется планировщиком при наличии live-матчей
        "recommendations": [],  # Список прогнозов (заполняется из БД)
        "timestamp": asyncio.get_event_loop().time()
    }

# Healthcheck эндпоинты для Amvera Cloud / Kubernetes
@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса (для оркестратора)"""
    return {"status": "healthy", "version": "4.02", "service": settings.APP_NAME}

@app.get("/ready")
async def readiness_check():
    """Проверка готовности обрабатывать трафик"""
    # В будущем можно добавить проверку подключения к БД/Redis
    return {"status": "ready"}
