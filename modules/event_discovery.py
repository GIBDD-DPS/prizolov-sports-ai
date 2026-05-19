# ============================================
# Prizolov Sports AI - Autonomous Event Discovery Engine
# Version: 1.00 (+1.00: Multi-Sport Autonomous Event Scanner & Normalizer)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at cloud.amvera.ru
# ============================================

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx  # Для реальных HTTP-запросов к спортивным API

logger = logging.getLogger("PrizolovSportsAI.EventDiscovery")

# === КОНФИГУРАЦИЯ ПОДДЕРЖИВАЕМЫХ СПОРТОВ ===
# В продакшене каждый ключ маппится на endpoint внешнего API
SUPPORTED_SPORTS = [
    "football", "hockey", "basketball", "tennis", 
    "volleyball", "mma", "esports"
]

class EventDiscoveryEngine:
    """
    Автономный модуль поиска, фильтрации и нормализации спортивных событий.
    Работает в фоне, обновляет пул матчей каждые N секунд, готов к подключению 
    реальных API (API-Football, The Odds API, SportRadar, RapidAPI).
    """
    def __init__(self, refresh_interval: int = 120, api_key: Optional[str] = None):
        self.refresh_interval = refresh_interval
        self.api_key = api_key
        self._events: List[Dict[str, Any]] = []
        self._running = False
        self._last_fetch_time: Optional[datetime] = None

    async def fetch_events(self) -> List[Dict[str, Any]]:
        """
        Основной метод сбора событий. 
        В текущей версии: продвинутый мок с реалистичным распределением.
        В продакшене: заменяется на асинхронные запросы к внешним API.
        """
        new_events = []
        now = datetime.utcnow()
        
        for sport in SUPPORTED_SPORTS:
            # Имитация получения данных от провайдера
            sport_data = await self._fetch_sport_data(sport, now)
            new_events.extend(sport_data)
            
        # Сортировка по времени начала, фильтрация прошедших
        self._events = sorted(
            [e for e in new_events if e["status"] in ("upcoming", "live")],
            key=lambda x: x["start_time"]
        )
        self._last_fetch_time = now
        logger.info(f"🔍 Discovered {len(self._events)} active events across {len(SUPPORTED_SPORTS)} sports")
        return self._events

    async def _fetch_sport_data(self, sport: str, now: datetime) -> List[Dict[str, Any]]:
        """
        Генератор/заглушка событий по виду спорта.
        Готов к замене на: async with httpx.AsyncClient() as client: resp = await client.get(...)
        """
        count = random.randint(3, 8)
        events = []
        for i in range(count):
            # Случайное время старта в диапазоне [-1 час (LIVE) ... +24 часа]
            offset_minutes = random.randint(-60, 1440)
            start_time = now + timedelta(minutes=offset_minutes)
            status = "live" if offset_minutes <= 0 else "upcoming"
            
            events.append({
                "match_id": f"{sport}_{now.strftime('%Y%m%d%H')}_{random.randint(1000,9999)}",
                "sport": sport,
                "league": self._resolve_league(sport),
                "home_team": self._resolve_team(sport),
                "away_team": self._resolve_team(sport),
                "start_time": start_time.isoformat(),
                "status": status,
                "betting_interest": random.uniform(0.4, 0.95)  # Скор для фильтрации интересных матчей
            })
        return events

    def _resolve_league(self, sport: str) -> str:
        """Маппинг лиг по видам спорта (расширяемый)"""
        pools = {
            "football": ["РПЛ", "АПЛ", "Ла Лига", "Серия А", "Бундеслига", "Бразилия Серия А", "Лига Чемпионов"],
            "hockey": ["КХЛ", "НХЛ", "Швеция SHL", "Чехия Экстралига", "Германия DEL"],
            "basketball": ["ВТБ", "НБА", "Евролига", "Испания ACB", "Турция BSL"],
            "tennis": ["ATP 250/500/1000", "WTA 250/500/1000", "Челленджеры", "ITF"],
            "volleyball": ["Суперлига (RU)", "Лига Наций", "CEV Champions", "Италия SuperLega"],
            "mma": ["UFC Fight Night", "Bellator", "ONE Championship", "Cage Warriors"],
            "esports": ["CS2 IEM/BLAST", "Dota 2 ESL/RIYADH", "LoL LEC/LCK", "Valorant VCT"]
        }
        return random.choice(pools.get(sport, ["Международный турнир"]))

    def _resolve_team(self, sport: str) -> str:
        """Генератор названий команд/атлетов"""
        pools = {
            "football": ["Спартак", "Зенит", "ЦСКА", "Локомотив", "Реал М", "Барселона", "Ман Сити", "Ливерпуль", "Байер", "Интер"],
            "hockey": ["ЦСКА", "СКА", "Ак Барс", "Металлург", "Динамо Мск", "Авангард", "Тампа", "Колорадо", "Эдмонтон"],
            "basketball": ["ЦСКА", "УНИКС", "Зенит", "Лейкерс", "Бостон", "Реал М", "Панатинаикос", "Олимпиакос"],
            "tennis": ["Медведев", "Алькарас", "Синнер", "Джокович", "Рублев", "Хачанов", "Свентек", "Гауфф", "Соболенко"],
            "volleyball": ["Зенит-Казань", "Динамо Мск", "Локомотив НН", "Белогорье", "Италия", "Польша", "Бразилия"],
            "mma": ["Махачев", "Миочич", "Аспиналл", "Порье", "Адесанья", "Топурия", "Волкановски", "Чимаев"],
            "esports": ["NAVI", "FaZe", "G2", "T1", "Cloud9", "VP", "Team Spirit", "Vitality", "Fnatic"]
        }
        return random.choice(pools.get(sport, ["Участник А", "Участник Б"]))

    def get_events_for_analysis(self, hours_ahead: int = 12, min_interest: float = 0.6, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Фильтр событий для последующего анализа агентом.
        - Только ближайшие N часов
        - Только матчи с высоким betting_interest
        - Лимит на пул для экономии ресурсов
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        
        return [
            e for e in self._events 
            if datetime.fromisoformat(e["start_time"]) <= cutoff 
            and e["betting_interest"] >= min_interest
        ][:limit]

    def get_event_by_id(self, match_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self._events if e["match_id"] == match_id), None)

    def get_all_events(self) -> List[Dict[str, Any]]:
        return self._events.copy()

    async def start_auto_discovery(self):
        """Запуск фонового цикла автономного поиска"""
        self._running = True
        logger.info("🌍 EventDiscoveryEngine: Autonomous scanning started")
        await self.fetch_events()
        
        while self._running:
            await asyncio.sleep(self.refresh_interval)
            try:
                await self.fetch_events()
            except Exception as e:
                logger.error(f"💥 Auto-discovery cycle failed: {e}")
                await asyncio.sleep(10)  # Защита от busy-loop

    def stop(self):
        self._running = False
        logger.info("🛑 EventDiscoveryEngine: Scanning stopped")
