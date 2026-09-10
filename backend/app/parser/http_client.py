# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Shared HTTP client headers for parser sources.

ПРИМЕЧАНИЕ: изначальный User-Agent (PRIZOLOV-Sports-AI/...) честно
идентифицировал парсер как бота — некоторые источники (например Forebet)
блокируют такие запросы на уровне WAF (403 Forbidden), независимо от
частоты запросов. Ниже — браузероподобные заголовки, снижающие вероятность
блокировки. Это не гарантирует обход более серьёзной защиты
(Cloudflare challenge, капчи, антибот-JS) — если 403/challenge вернётся
после этого фикса, дальше нужно либо получать данные через официальный
API источника (если он есть), либо пересматривать источник данных.
"""

from app.core.config import settings

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Оригинальный самоидентифицирующийся UA сохранён отдельно — можно
# переключиться обратно одной строкой, если источник это не блокирует
# (например, для собственных/партнёрских API, где представляться ботом
# — это норма и хорошая практика).
IDENTIFYING_USER_AGENT = settings.parser_user_agent