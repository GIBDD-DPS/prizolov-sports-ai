# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import re
import structlog
from typing import Dict, Any, List

log = structlog.get_logger()

class SentimentAnalyzer:
    """
    NLP-анализатор тональности для спортивных событий.
    В версии 4.01 использует эвристическую модель на ключевых словах.
    В продакшене заменяется на загрузку RuBERT / DeepPavlov / custom LLM.
    """
    def __init__(self):
        self.positive_keywords = {
            "победа", "выиграет", "фаворит", "уверенно", "сильнее", "топ", 
            "в форме", "разгром", "дубль", "хет-трик", "проход", "win"
        }
        self.negative_keywords = {
            "проиграет", "слабее", "травмы", "дисквалификация", "спад", 
            "усталость", "мотивации нет", "слабая оборона", "потеря", "lose"
        }

    async def analyze_text_batch(self, texts: List[str], team_a: str, team_b: str) -> float:
        """
        Анализирует пакет текстовых сообщений.
        Возвращает bias_score от -1.0 (сильно в пользу команды B) до +1.0 (сильно в пользу команды A).
        0.0 означает нейтральный фон.
        """
        if not texts:
            return 0.0

        score_a = 0.0
        score_b = 0.0
        pattern_a = re.compile(re.escape(team_a), re.IGNORECASE)
        pattern_b = re.compile(re.escape(team_b), re.IGNORECASE)

        for txt in texts:
            txt_lower = txt.lower()
            if pattern_a.search(txt_lower):
                score_a += sum(1 for kw in self.positive_keywords if kw in txt_lower)
                score_a -= sum(1 for kw in self.negative_keywords if kw in txt_lower)
            if pattern_b.search(txt_lower):
                score_b += sum(1 for kw in self.positive_keywords if kw in txt_lower)
                score_b -= sum(1 for kw in self.negative_keywords if kw in txt_lower)

        total = max(abs(score_a) + abs(score_b), 1.0)
        bias = (score_a - score_b) / total
        return max(-1.0, min(1.0, bias))

analyzer = SentimentAnalyzer()

async def analyze_sentiment(match_data: Dict[str, Any]) -> Dict[str, float]:
    """
    AI/Sentiment слой.
    Принимает собранные тексты (Telegram, новости, соцсети) и корректирует
    вероятности исходов на основе общественной тональности.
    """
    match_id = match_data.get("match_id", "unknown")
    home = match_data.get("home_team", "")
    away = match_data.get("away_team", "")
    # Тексты передаются из scheduler.py после парсинга
    texts = match_data.get("raw_texts", [])

    log.debug("AI Sentiment layer: analyzing", match_id=match_id, text_count=len(texts))

    if not texts:
        log.info("No sentiment data available, returning neutral baseline")
        return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}

    bias_score = await analyzer.analyze_text_batch(texts, home, away)

    # Конвертация bias в корректировку вероятности
    # Максимальный сдвиг тональности: ±20%
    adjustment = bias_score * 0.20
    base_home = 0.33
    adjusted_home = max(0.05, min(0.90, base_home + adjustment))

    # Перераспределение оставшейся массы между ничьей и гостями
    remaining = 1.0 - adjusted_home
    
    # Если тонус за хозяев -> снижаем долю ничьей/гостей пропорционально
    # Если тонус нейтральный/за гостей -> равное распределение остатка
    if bias_score > 0.1:
        return {
            "home_win": round(adjusted_home, 4),
            "draw": round(remaining * 0.40, 4),
            "away_win": round(remaining * 0.60, 4)
        }
    else:
        return {
            "home_win": round(adjusted_home, 4),
            "draw": round(remaining * 0.50, 4),
            "away_win": round(remaining * 0.50, 4)
        }
