# ============================================
# Prizolov Sports AI - Discovery Engine
# Version: 1.0
# Purpose: Получение текущих матчей и событий для анализа
# ============================================

import logging
import datetime
from typing import List, Dict, Any, Optional
import aiohttp

logger = logging.getLogger("PrizolovSportsAI.DiscoveryEngine")


class DiscoveryEngine:
    """
    Получает текущие события матчей из внешних источников.
    В боевом режиме подключается к реальным API.
    В демо режиме возвращает тестовые данные.
    """

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.events: Dict[str, Dict[str, Any]] = {}
        self._initialize_demo_events()

    def _initialize_demo_events(self):
        """Инициализация тестовых событий для демонстрации"""
        now = datetime.datetime.utcnow()
        
        self.events = {
            "match_1": {
                "match_id": "match_1",
                "sport": "football",
                "league": "РПЛ",
                "home_team": "Зенит",
                "away_team": "Спартак",
                "status": "LIVE",
                "kickoff": now.isoformat(),
                "interest_level": 0.95,
                "last_update": now.isoformat(),
            },
            "match_2": {
                "match_id": "match_2",
                "sport": "football",
                "league": "La Liga",
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "status": "PREMATCH",
                "kickoff": (now + datetime.timedelta(hours=2)).isoformat(),
                "interest_level": 0.92,
                "last_update": now.isoformat(),
            },
            "match_3": {
                "match_id": "match_3",
                "sport": "football",
                "league": "Premier League",
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "status": "LIVE",
                "kickoff": (now - datetime.timedelta(minutes=45)).isoformat(),
                "interest_level": 0.88,
                "last_update": now.isoformat(),
            },
            "match_4": {
                "match_id": "match_4",
                "sport": "basketball",
                "league": "NBA",
                "home_team": "Lakers",
                "away_team": "Celtics",
                "status": "PREMATCH",
                "kickoff": (now + datetime.timedelta(hours=5)).isoformat(),
                "interest_level": 0.75,
                "last_update": now.isoformat(),
            },
        }

    def get_events_for_analysis(
        self,
        hours_ahead: int = 12,
        min_interest: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Получить события для анализа

        Args:
            hours_ahead: Сколько часов вперед смотреть
            min_interest: Минимальный уровень интереса (0-1)
            limit: Максимум событий

        Returns:
            Список событий для анализа
        """
        result = []
        now = datetime.datetime.utcnow()
        cutoff = now + datetime.timedelta(hours=hours_ahead)

        for event in self.events.values():
            try:
                kickoff = datetime.datetime.fromisoformat(event["kickoff"])
                interest = event.get("interest_level", 0)

                if kickoff <= cutoff and interest >= min_interest:
                    result.append(event)
            except (ValueError, KeyError):
                continue

            if len(result) >= limit:
                break

        logger.debug(f"📅 Found {len(result)} events for analysis")
        return result

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Получить все известные события"""
        return list(self.events.values())

    def get_live_events(self) -> List[Dict[str, Any]]:
        """Получить только текущие LIVE события"""
        return [e for e in self.events.values() if e.get("status") == "LIVE"]

    def add_event(self, event: Dict[str, Any]) -> bool:
        """Добавить событие"""
        match_id = event.get("match_id")
        if not match_id:
            return False
        self.events[match_id] = event
        logger.info(f"✅ Event added: {match_id}")
        return True

    def remove_event(self, match_id: str) -> bool:
        """Удалить событие"""
        if match_id in self.events:
            del self.events[match_id]
            logger.info(f"🗑️ Event removed: {match_id}")
            return True
        return False

    def update_event_status(self, match_id: str, status: str) -> bool:
        """Обновить статус события"""
        if match_id in self.events:
            self.events[match_id]["status"] = status
            self.events[match_id]["last_update"] = datetime.datetime.utcnow().isoformat()
            return True
        return False

    async def sync_from_external_api(self, api_key: Optional[str] = None):
        """
        Синхронизация с внешним API (когда будет готов)
        """
        if self.demo_mode:
            logger.debug("ℹ️ Demo mode: skipping external API sync")
            return

        # TODO: Реальная интеграция с sports API
        logger.info("🔄 Syncing from external API...")
        pass
