# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

# Попытка импортировать NLP-библиотеки (например, transformers)
try:
    from transformers import pipeline
    REAL_NLP_AVAILABLE = True
except ImportError:
    REAL_NLP_AVAILABLE = False
    logger.warning("NLP-библиотеки не найдены, используется fallback-анализ")

class AISentimentLayer:
    def __init__(self, model_name: Optional[str] = None):
        self.sentiment_pipeline = None
        if REAL_NLP_AVAILABLE:
            try:
                model = model_name or "blanchefort/rubert-base-cased-sentiment"
                self.sentiment_pipeline = pipeline("sentiment-analysis", model=model)
                logger.info(f"Загружена модель sentiment: {model}")
            except Exception as e:
                logger.error(f"Ошибка загрузки модели sentiment: {e}")
                self.sentiment_pipeline = None

    def analyze(self, text: str) -> Dict[str, Any]:
        """Анализ тональности с fallback."""
        if self.sentiment_pipeline is not None:
            try:
                result = self.sentiment_pipeline(text[:512])[0]
                return {
                    "label": result["label"],
                    "score": result["score"],
                    "method": "nlp_model"
                }
            except Exception as e:
                logger.error(f"Ошибка NLP-анализа: {e}")
        # Fallback: простая эвристика на основе ключевых слов
        return self._heuristic_sentiment(text)

    def _heuristic_sentiment(self, text: str) -> Dict[str, Any]:
        """Очень простой анализатор на основе позитивных/негативных слов."""
        text_lower = text.lower()
        positive_words = ["хорошо", "отлично", "победа", "win", "good", "great"]
        negative_words = ["плохо", "поражение", "проигрыш", "lose", "bad", "awful"]
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            label = "POSITIVE"
            score = 0.7 + (pos_count / (pos_count + neg_count + 1)) * 0.3
        elif neg_count > pos_count:
            label = "NEGATIVE"
            score = 0.7 + (neg_count / (pos_count + neg_count + 1)) * 0.3
        else:
            label = "NEUTRAL"
            score = 0.5
        return {"label": label, "score": min(score, 1.0), "method": "heuristic_fallback"}
