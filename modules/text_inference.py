# ============================================
# Prizolov Sports AI - Live Text-Inference Core
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production NLP Live Event Extraction
# ============================================

import sys
import os
import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import httpx

logger = logging.getLogger("PrizolovSportsAI.TextInference")

class LiveTextInferenceEngine:
    """Асинхронный воркер текстовых трансляций для извлечения скрытых live-событий методами NLP"""

    def __init__(self, match_id: str, feed_url: Optional[str] = None):
        self.match_id = match_id
        # Целевой URL фида текстовой трансляции платформы prizolov.ru
        self.feed_url = feed_url if feed_url else f"https://prizolov.ru{match_id}/text-stream"
        self.last_processed_timestamp = 0
        self.is_active = True

    async def poll_live_text_feed(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Сканирует live-текст фид, очищает логи и выявляет критические аномалии"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"User-Agent": "PrizolovSportsAI-NLP-Worker/5.01"}
                response = await client.get(self.feed_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    if not events:
                        return None
                        
                    latest_event = events[-1] # Берем последнее текстовое сообщение
                    event_ts = latest_event.get("timestamp", 0)
                    
                    if event_ts > self.last_processed_timestamp:
                        self.last_processed_timestamp = event_ts
                        raw_text = latest_event.get("text", "")
                        
                        # NLP-парсинг намерения сообщения
                        intent, impact = self._classify_text_intent(raw_text)
                        if intent != "NORMAL":
                            return intent, {"text": raw_text, "impact_factor": impact}
        except Exception as e:
            logger.error(f"Ошибка чтения текстового NLP фида: {e}")
            
        return None

    def _classify_text_intent(self, text: str) -> Tuple[str, float]:
        """Анализирует текст на маркеры травм, удалений и грубых остановок игры"""
        cleaned_text = text.lower()
        
        # Регулярные выражения и триггер-карты
        if any(w in cleaned_text for w in ["травма", "носилки", "повреждение", "врач", "медицинская"]):
            return "INJURY", 0.85  # Множитель падения интенсивности атак (игра замерла)
            
        if any(w in cleaned_text for w in ["удаление", "красная карточка", "пенальти", "драка", "стычка"]):
            return "CRITICAL_DISCIPLINE", 1.25 # Множитель взлета волатильности и маржи
            
        if any(w in cleaned_text for w in ["вар", "var", "повтор", "просмотр видео"]):
            return "VAR_REVIEW", 0.00 # Сигнал полной заморозки линии (Suspended)
            
        return "NORMAL", 1.00
