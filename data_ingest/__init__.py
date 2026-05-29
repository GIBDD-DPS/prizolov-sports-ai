# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

"""
Пакет data_ingest: модули сбора и нормализации данных из внешних источников.
Включает: бесплатные API, агрегаторы, Telegram-парсинг, букмекерские линии.
"""

__all__ = [
    "FreeAPICollector",
    "AggregatorCollector", 
    "TelegramCollector",
    "BookmakerCollector"
]
