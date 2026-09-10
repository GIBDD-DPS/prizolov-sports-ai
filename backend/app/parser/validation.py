# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Общие проверки на аномалии во входящих данных парсеров.

Один источник с ошибкой (сбойный API-ответ, опечатка в парсинге, битая
строка) может испортить весь прогноз — особенно пока в системе активен
только один источник. Эти функции — простой защитный барьер перед тем,
как данные попадут в БД и агрегацию.
"""

from __future__ import annotations

# Коэффициент 1.0 или ниже означает "проигрыша не будет" — то есть на 100%
# уверенно неверная строка/шум в ответе API. Коэффициент выше 50 практически
# никогда не встречается в реальных линиях 1X2 даже для дичайших андердогов —
# такое значение почти наверняка означает битые данные, а не реальную ставку.
MIN_PLAUSIBLE_ODDS = 1.01
MAX_PLAUSIBLE_ODDS = 50.0


def is_valid_odds(value: float | int | None) -> bool:
    """True, если коэффициент похож на реальный, а не на мусор/аномалию."""
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    if numeric != numeric:  # NaN
        return False
    return MIN_PLAUSIBLE_ODDS <= numeric <= MAX_PLAUSIBLE_ODDS
