# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import logging
import sys
import structlog
from app.config import settings

def setup_logging():
    """
    Инициализация структурированного логирования.
    Продакшен: JSON-формат (для Amvera, Sentry, ELK-стека).
    Разработка: Цветной консольный вывод с трассировкой.
    Автоматически интегрируется с Uvicorn и стандартным logging.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Базовая настройка стандартного logging (перехват логов Uvicorn/Starlette)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Общие процессоры для structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if not settings.DEBUG:
        # 🟢 Продакшен: JSON рендеринг
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        # 🟡 Разработка: Консольный вывод
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )

    # Финальная конфигурация structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Применяем форматтер ко всем хендлерам корневого логгера
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

    # Возвращаем преднастроенный логгер для удобства
    return structlog.get_logger()
