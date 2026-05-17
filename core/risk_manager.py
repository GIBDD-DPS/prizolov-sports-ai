# ============================================
# Prizolov Sports AI - Risk Management Engine
# Version: 4.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import logging
from typing import Dict, Any, List

logger = logging.getLogger("PrizolovSportsAI.RiskManager")

class RiskManagementEngine:
    """Модуль защиты от финансовых рисков, балансировки маржи и анти-вилочного контроля"""

    def __init__(self, base_margin: float = 1.05):
        """
        Args:
            base_margin: Базовая маржа букмекера (1.05 = 5%)
        """
        self.base_margin = base_margin
        self.current_margin = base_margin

    def adjust_margin_by_volatility(self, live_xg_speed: float, is_critical_moment: bool) -> float:
        """
        Динамически увеличивает маржу во время сверхопасных моментов матча.
        Это защищает сайт от игроков, использующих сверхбыстрые стримы (когда гол уже забит).
        """
        self.current_margin = self.base_margin
        
        # Если скорость нарастания xG высокая (идет затяжная атака)
        if live_xg_speed > 0.15:
            self.current_margin += 0.03  # Добавляем +3% к марже
            
        # Если зафиксирован критический live-момент (пенальти, удаление, опасный штрафной)
        if is_critical_moment:
            self.current_margin += 0.07  # Добавляем +7% к марже (итоговая маржа до 15%)
            
        return round(self.current_margin, 3)

    def apply_anti_arbitrage_filter(self, 
                                    our_line: Dict[str, List[Dict[str, Any]]], 
                                    market_feed_odds: Dict[str, float]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Сопоставляет сгенерированные ИИ коэффициенты с рыночным фидом конкурентов (Betradar).
        Корректирует котировки в случае возникновения вилок, защищая баланс платформы.
        """
        if not market_feed_odds:
            return our_line

        # Пример валидации для рынка 1Х2
        if "main_outcomes" in our_line:
            for outcome in our_line["main_outcomes"]:
                market_name = outcome["market_name"]
                # Ищем этот же исход в фиде конкурентов (например, "CSKA_Win" или "1")
                competitor_odds = market_feed_odds.get(market_name, None)
                
                if competitor_odds:
                    # Рассчитываем арбитражный индекс (если сумма инверсий < 1.0 — это вилка)
                    arbitrage_index = (1.0 / outcome["odds"]) + (1.0 / competitor_odds)
                    
                    if arbitrage_index < 1.005:  # Обнаружена потенциальная уязвимость для арбитража
                        logger.warning(f"[Risk Warning] Обнаружена вилка на рынке {market_name}. Наш кэф: {outcome['odds']}, Рынок: {competitor_odds}")
                        # Искусственно занижаем наш коэффициент для ликвидации вилки
                        adjusted_odds = round(1.0 / ((1.03 / competitor_odds) - 1.0), 2)
                        outcome["odds"] = max(min(adjusted_odds, outcome["odds"] - 0.1), 1.01)

        return our_line
