# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Типизированная конфигурация приложения.
    Загружает значения из .env файла или переменных окружения (Amvera CI/CD).
    """
    
    # 🟢 Основное приложение
    APP_NAME: str = "Prizolov Sports AI"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # 🟢 База данных и кэш
    DATABASE_URL: str = "postgresql+asyncpg://app_user:secure_pass@db:5432/sports_ai"
    REDIS_URL: str = "redis://redis:6379/0"

    # 🟢 Мониторинг и ошибки
    SENTRY_DSN: Optional[str] = None

    # 🟢 Внешние API (Коэффициенты и События)
    API_KEYS_ODDS: Optional[str] = None
    API_KEYS_SPORTS: Optional[str] = None

    # 🟢 Telegram (для парсинга каналов/чатов)
    TELEGRAM_API_ID: Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_SESSION: Optional[str] = None
    TELEGRAM_CHANNELS: Optional[str] = None  # Список каналов через запятую: "channel1,channel2"

    # 🟢 Интервалы планировщика (в секундах)
    LIVE_INTERVAL: int = 30
    PREMATCH_INTERVAL: int = 300
    ODDS_INTERVAL: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

# Глобальный синглтон конфигурации
settings = Settings()
