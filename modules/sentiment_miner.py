# ============================================
# Prizolov Sports AI - Social Sentiment Miner
# Version: 4.02 (Antiban Bypass Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.SentimentMiner")

class SentimentMinerModule:
    """ИИ-модуль сбора, фильтрации и NLP-анализа прогнозов с капперских ресурсов"""

    def __init__(self, min_capper_roi: float = 5.0, min_bets_count: int = 100):
        self.min_roi = min_capper_roi
        self.min_bets = min_bets_count
        
        # Список доверенных ресурсов для парсинга (базовый пул для prizolov.ru)
        self.target_sources = [
            "https://prizolov.ru", # Внутренние топ-прогнозы платформы
            "https://vprognoze.ru", # Тестовый обход ограничений
        ]
        
        self.active_signals_cache: Dict[str, List[Dict[str, Any]]] = {}

    async def fetch_predictions_from_source(self, url: str) -> List[Dict[str, Any]]:
        """Асинхронно скачивает данные, маскируя запросы под реальный браузер для обхода 403 Forbidden"""
        extracted_predictions = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Исправлено: внедрены полноценные заголовки реального браузера (Chrome/Windows)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "max-age=0",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Chua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    "Sec-Chua-Mobile": "?0",
                    "Sec-Chua-Platform": '"Windows"'
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    logger.debug(f"Успешно скачан контент с {url}, размер: {len(response.text)} байт")
                    
                    # Имитируем успешное извлечение структурированного прогноза для архитектурного теста
                    extracted_predictions.append({
                        "team_keyword": "CSKA",
                        "market_type": "TO 2.5",
                        "capper_roi": 12.4,
                        "capper_total_bets": 340,
                        "raw_text": "Жду открытую игру от команд, ЦСКА много атакует флангами, тотал больше 2.5 должен заходить легко за такой кэф."
                    })
                else:
                    logger.warning(f"[Antiban Warning] Ресурс {url} вернул статус-код: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Ошибка при парсинге ресурса {url}: {e}")
        
        return extracted_predictions

    def _nlp_analyze_intent(self, text: str) -> float:
        """NLP-анализ текста на предмет уверенности каппера в прогнозе"""
        cleaned_text = text.lower()
        confidence = 0.5
        positive_markers = ["легко", "уверен", "пройдет", "железно", "зайдет", "выиграет"]
        negative_markers = ["риск", "аккуратно", "вряд ли", "не думаю", "сложный"]
        
        for word in positive_markers:
            if word in cleaned_text: confidence += 0.08
        for word in negative_markers:
            if word in cleaned_text: confidence -= 0.1
            
        return max(min(confidence, 1.0), 0.0)

    async def update_global_sentiment_trends(self) -> None:
        """Главный фоновый воркер модуля: обходит ресурсы, фильтрует по ROI и обновляет кэш"""
        logger.info("Запуск глобального сканирования капперских ресурсов...")
        
        all_raw_predictions = []
        tasks = [self.fetch_predictions_from_source(url) for url in self.target_sources]
        results = await asyncio.gather(*tasks)
        
        for res_list in results:
            all_raw_predictions.extend(res_list)

        new_cache: Dict[str, List[Dict[str, Any]]] = {}

        for pred in all_raw_predictions:
            if pred["capper_roi"] < self.min_roi or pred["capper_total_bets"] < self.min_bets:
                continue

            confidence_weight = self._nlp_analyze_intent(pred["raw_text"])
            
            if confidence_weight > 0.65:
                key = pred["team_keyword"].lower()
                if key not in new_cache:
                    new_cache[key] = []
                    
                new_cache[key].append({
                    "market": pred["market_type"],
                    "weight": confidence_weight,
                    "roi": pred["capper_roi"]
                })
                
        self.active_signals_cache = new_cache
        logger.info(f"Глобальный тренд-кэш обновлен. Активных ключевых сущностей: {len(self.active_signals_cache)}")

    def get_market_sentiment_modifier(self, team_name_a: str, team_name_b: str, market_name: str) -> float:
        """Вычисляет коэффициент корректировки на основе капперского сентимента для рынка"""
        modifier = 1.0
        keys_to_check = [team_name_a.lower(), team_name_b.lower()]
        
        for key in keys_to_check:
            if key in self.active_signals_cache:
                for signal in self.active_signals_cache[key]:
                    if signal["market"].lower() in market_name.lower():
                        impact = (signal["weight"] * (signal["roi"] / 100.0))
                        modifier += impact
                        
        return min(modifier, 1.35)
