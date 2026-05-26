# ============================================
# Prizolov Sports AI - Risk Management Engine
# Version: 4.02 (Minor Refactor & WP/Elementor Output Prep)
#
# CHANGELOG (4.01 → 4.02):
# - Удалены неиспользуемые импорты
# - Уточнены типы и docstring-и
# - Упорядочено форматирование
# - Лёгкая чистка структуры без изменения логики
# - Подготовка структуры под API-вывод для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import logging
from typing import Dict, Any, List

logger = logging.getLogger("PrizolovSportsAI.RiskManager")


class RiskManagementEngine:
    """
    Модуль защиты от финансовых рисков, балансировки маржи и анти-вилочного контроля.
    Готов к сериализации в JSON для API-слоя WordPress Elementor.
    """

    def __init__(self, base_margin: float = 1.05) -> None:
        """
        Args:
            base_margin: Базовая маржа букмекера (1.05 = 5%).
        """
        self.base_margin: float = base_margin
        self.current_margin: float = base_margin

    def adjust_margin_by_volatility(self, live_xg_speed: float, is_critical_moment: bool) -> float:
        """
        Динамически увеличивает маржу во время сверхопасных моментов матча.
        Это защищает сайт от игроков, использующих сверхбыстрые стримы.

        Args:
            live_xg_speed: скорость роста xG (индикатор давления).
            is_critical_moment: флаг критического события (пенальти, удаление).

        Returns:
            Откорректированная маржа.
        """
        self.current_margin = self.base_margin

        # Высокая скорость нарастания xG → опасная атака
        if live_xg_speed > 0.15:
            self.current_margin += 0.03  # +3%

        # Критический момент → максимальная защита
        if is_critical_moment:
            self.current_margin += 0.07  # +7%

        return round(self.current_margin, 3)

    def apply_anti_arbitrage_filter(
        self,
        our_line: Dict[str, List[Dict[str, Any]]],
        market_feed_odds: Dict[str, float]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Сопоставляет сгенерированные ИИ коэффициенты с рыночным фидом конкурентов.
        Корректирует котировки в случае возникновения вилок.

        Args:
            our_line: наши коэффициенты.
            market_feed_odds: коэффициенты конкурентов.

        Returns:
            Откорректированная линия.
        """
        if not market_feed_odds:
            return our_line

        # Пример валидации для рынка 1Х2
        if "main_outcomes" in our_line:
            for outcome in our_line["main_outcomes"]:
                market_name = outcome.get("market_name")
                if not market_name:
                    continue

                competitor_odds = market_feed_odds.get(market_name)
                if not competitor_odds:
                    continue

                # Арбитражный индекс
                arbitrage_index = (1.0 / outcome["odds"]) + (1.0 / competitor_odds)

                # Если сумма инверсий < 1.005 → потенциальная вилка
                if arbitrage_index < 1.005:
                    logger.warning(
                        f"[Risk Warning] Обнаружена вилка на рынке {market_name}. "
                        f"Наш кэф: {outcome['odds']}, Рынок: {competitor_odds}"
                    )

                    # Коррекция коэффициента
                    adjusted_odds = round(1.0 / ((1.03 / competitor_odds) - 1.0), 2)

                    # Ограничиваем диапазон
                    outcome["odds"] = max(min(adjusted_odds, outcome["odds"] - 0.1), 1.01)

        return our_line
