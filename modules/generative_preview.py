# ============================================
# Prizolov Sports AI - Generative Preview Engine
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Automated SEO Content & Prediction Generation
# ============================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.GenerativePreview")

class GenerativePreviewEngine:
    """Генеративный NLP-модуль для автоматического создания экспертных текстовых превью и прогнозов на prizolov.ru"""

    def __init__(self):
        pass

    def generate_match_preview_text(self, 
                                    match_id: str, 
                                    team_a: str, 
                                    team_b: str, 
                                    sport: str, 
                                    lambda_a: float, 
                                    lambda_b: float,
                                    capper_sentiment_trend: str = "over") -> str:
        """
        Генерирует развернутый аналитический разбор матча на основе математических весов ИИ-ядра.
        """
        logger.info(f"[Generative AI] Сборка текстового превью для матча {match_id} ({team_a} vs {team_b})...")
        
        # Определяем фаворита встречи на основе Пуассоновских интенсивностей
        if abs(lambda_a - lambda_b) < 0.25:
            strength_analysis = f"Обе команды подходят к live-встрече в сопоставимой форме. Математическая модель ИИ Prizolov Lab фиксирует паритет сил."
            prediction_tip = "Наиболее безопасным выбором здесь выглядит ставка на обоюдную результативность (Обе забьют - Да) или плюсовые форы аутсайдера."
        elif lambda_a > lambda_b:
            strength_analysis = f"Аналитическое ядро Prizolov AI выделяет {team_a} в качестве явного фаворита данного противостояния. Интенсивность их атакующих действий значительно превосходит оборонительный потенциал оппонента."
            prediction_tip = f"Рекомендуется присмотреться к чистой победе {team_a} или аккуратной минусовой форе (-1)."
        else:
            strength_analysis = f"Команда {team_b} имеет выраженное преимущество по ключевым метрикам предматчевого контекста. Вероятность их доминирования на чужой половине поля оценивается экспертной системой как повышенная."
            prediction_tip = f"Логичным решением для купона будет фора (0) на {team_b} или их индивидуальный тотал больше."

        # Интегрируем тренды капперского сентимента из кэш-базы
        if capper_sentiment_trend == "over":
            sentiment_paragraph = "Экспертное сообщество верификаторов и капперов платформы prizolov.ru единогласно ожидает открытый, атакующий футбол с обилием опасных моментов. Тренды сентимент-анализа указывают на перегруз верховых маркетов."
        else:
            sentiment_paragraph = "Большинство профессиональных live-аналитиков склоняются к прагматичному, закрытому сценарию матча. Защитные редуты обеих сторон будут превалировать над созиданием."

        # Сборка финального текстового обзора
        preview_article = [
            f"=== АНАЛИТИЧЕСКИЙ ПРЕВЬЮ-ОБЗОР МАТЧА: {team_a.upper()} ПРОТИВ {team_b.upper()} ===",
            f"В рамках текущего live-сезона по виду спорта {sport} нас ожидает интригующее противостояние.",
            strength_analysis,
            sentiment_paragraph,
            "--- ИИ-ПРОГНОЗ ОТ ЛАБОРАТОРИИ PRIZOLOV SPORTS ---",
            prediction_tip,
            "================================================"
        ]

        generated_text = "\n\n".join(preview_article)
        logger.info(f"[Generative AI] Текстовый обзор успешно скомпилирован. Длина: {len(generated_text)} символов.")
        return generated_text
