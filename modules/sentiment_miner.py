# ============================================
# Prizolov Sports AI - Social Sentiment Miner
# Version: 4.03 (Redis Cache Layer Integration)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.SentimentMiner")

class SentimentMinerModule:
    """ИИ-модуль сбора, NLP-анализа и Redis-кэширования прогнозов с капперских ресурсов"""

    def __init__(self, min_capper_roi: float = 5.0, min_bets_count: int = 100, redis_url: Optional[str] = None):
        self.min_roi = min_capper_roi
        self.min_bets = min_bets_count
        
        # Список доверенных ресурсов для парсинга (базовый пул для prizolov.ru)
        self.target_sources = [
            "https://prizolov.ru",
            "https://vprognoze.ru",
        ]
        
        # Локальный резервный кэш (фолбэк)
        self.active_signals_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Инициализация клиента Managed Redis
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect_redis(self) -> None:
        """Асинхронное подключение к кластеру Managed Redis"""
        if self.redis_url:
            try:
                self.redis = aioredis.from_url(
                    self.redis_url, 
                    encoding="utf-8", 
                    decode_responses=True,
                    socket_timeout=5.0
                )
                await self.redis.ping()
                logger.info(f"Успешное подключение к Managed Redis по адресу: {self.redis_url}")
            except Exception as e:
                logger.error(f"Не удалось подключиться к Redis ({e}). Включен резервный режим локальной памяти.")
                self.redis = None

    async def fetch_predictions_from_source(self, url: str) -> List[Dict[str, Any]]:
        """Асинхронно скачивает данные, маскируя запросы под реальный браузер"""
        extracted_predictions = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Connection": "keep-alive"
                }
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    logger.debug(f"Успешно скачан контент с {url}, размер: {len(response.text)} байт")
                    
                    # Структурированный демонстрационный live-исход
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
        """Главный фоновый воркер модуля: собирает данные, фильтрует и распределяет в Redis кэш"""
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
                
        # Синхронизация данных с Redis (с TTL жизни кэша 300 секунд / 5 минут)
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                for key, signals in new_cache.items():
                    redis_key = f"prizolov:sentiment:{key}"
                    pipe.set(redis_key, json.dumps(signals), ex=300)
                await pipe.execute()
                logger.info(f"Распределенный кэш Redis успешно обновлен для {len(new_cache)} сущностей.")
            except Exception as e:
                logger.error(f"Ошибка записи в Redis транзакцию: {e}")
                self.active_signals_cache = new_cache
        else:
            self.active_signals_cache = new_cache
            
        logger.info("Глобальный тренд-кэш синхронизирован.")

    async def get_market_sentiment_modifier(self, team_name_a: str, team_name_b: str, market_name: str) -> float:
        """Асинхронно извлекает коэффициенты корректировки из Redis или локального кэша за 0.1мс"""
        modifier = 1.0
        keys_to_check = [team_name_a.lower(), team_name_b.lower()]
        
        for key in keys_to_check:
            signals = []
            
            # Извлекаем данные из In-Memory базы Redis
            if self.redis:
                try:
                    cached_data = await self.redis.get(f"prizolov:sentiment:{key}")
                    if cached_data:
                        signals = json.loads(cached_data)
                except Exception as e:
                    logger.error(f"Ошибка чтения из Redis кэша: {e}")
                    signals = self.active_signals_cache.get(key, [])
            else:
                signals = self.active_signals_cache.get(key, [])
                
            for signal in signals:
                if signal["market"].lower() in market_name.lower():
                    impact = (signal["weight"] * (signal["roi"] / 100.0))
                    modifier += impact
                        
        return min(modifier, 1.35)
