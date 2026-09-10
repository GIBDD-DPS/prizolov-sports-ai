# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser source adapters.

Forebet/Betensured убраны: 403, анти-бот защита не пробивается заголовками.
Predictz убран: при недоступности сайта отдаёт фейковую заглушку
("Predictz XI vs Predictz Stars") — не источник реальных данных.
API-Football временно отключён: аккаунт периодически уходит в suspended
(похоже на антифлуд после серии тестовых запросов) — верни его в PARSERS,
когда статус на dashboard.api-football.com стабилизируется:

    from app.parser.sources.api_football import ApiFootballParser
    PARSERS = [ApiFootballParser(), TheOddsApiParser()]
"""

from app.parser.sources.the_odds_api import TheOddsApiParser

PARSERS = [
    TheOddsApiParser(),
]