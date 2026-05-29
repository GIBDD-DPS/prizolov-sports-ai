# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import aiohttp
import structlog
from typing import Optional, List, Dict
from datetime import datetime

log = structlog.get_logger()

class FreeAPICollector:
    """
    Модуль сбора данных из бесплатных спортивных API.
    Поддерживает: The Odds API (коэффициенты), API-Sports (события/результаты).
    Реализует async-контекстный менеджер для корректного управления сессией.
    """
    
    API_ENDPOINTS = {
        "api-sports": "https://v3.football.api-sports.io",
        "the-odds": "https://api.the-odds-api.com/v4/sports",
        "sportdb": "https://api.sportdb.dev/v1"
    }
    
    def __init__(self, api_keys: Dict[str, str], timeout: int = 30):
        self.api_keys = api_keys
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_odds(self, sport: str = "soccer", region: str = "eu") -> List[Dict]:
        """Получение коэффициентов через The Odds API"""
        if not self.api_keys.get("the-odds"):
            log.warning("The Odds API key not configured, skipping odds fetch")
            return []
            
        url = f"{self.API_ENDPOINTS['the-odds']}/{sport}/odds"
        params = {
            "api_key": self.api_keys["the-odds"],
            "regions": region,
            "markets": "h2h,spreads,totals",
            "dateFormat": "iso"
        }
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    log.info("Fetched odds batch", sport=sport, count=len(data))
                    return data
                log.warning("Odds API returned non-200", status=resp.status, url=url)
        except Exception as e:
            log.error("Odds fetch failed", error=str(e), sport=sport)
        return []
    
    async def fetch_events(self, sport: str = "football", league_id: Optional[int] = None) -> List[Dict]:
        """Получение матчей и событий через API-Sports"""
        if not self.api_keys.get("api-sports"):
            log.warning("API-Sports key not configured, skipping events fetch")
            return []
            
        url = f"{self.API_ENDPOINTS['api-sports']}/fixtures"
        headers = {
            "x-rapidapi-key": self.api_keys["api-sports"],
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        params = {"league": league_id} if league_id else {"season": datetime.now().year}
        
        try:
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    raw = await resp.json()
                    events = raw.get("response", [])
                    log.info("Fetched events batch", sport=sport, count=len(events))
                    return self._normalize_events(events, sport)
                log.warning("API-Sports returned non-200", status=resp.status, url=url)
        except Exception as e:
            log.error("Events fetch failed", error=str(e), sport=sport)
        return []
    
    def _normalize_events(self, raw_events: List[Dict], sport: str) -> List[Dict]:
        """Приведение сырых данных API-Sports к единой внутренней схеме"""
        normalized = []
        for evt in raw_events:
            fixture = evt.get("fixture", {})
            teams = evt.get("teams", {})
            goals = evt.get("goals", {})
            league = evt.get("league", {})
            
            normalized.append({
                "match_id": f"{sport}_{fixture.get('id')}",
                "sport_type": sport,
                "league_name": league.get("name"),
                "home_team": teams.get("home", {}).get("name"),
                "away_team": teams.get("away", {}).get("name"),
                "start_time": fixture.get("date"),
                "status": fixture.get("status", {}).get("long"),
                "current_minute": fixture.get("elapsed"),
                "score": {"home": goals.get("home"), "away": goals.get("away")},
                "source": "api-sports",
                "fetched_at": datetime.utcnow().isoformat()
            })
        return normalized
    
    async def collect_batch(self, tasks_config: List[Dict]) -> List[Dict]:
        """
        Параллельный запуск сбора по списку задач.
        tasks_config: [{"type": "odds", "sport": "soccer"}, {"type": "events", "sport": "football"}]
        """
        async def _run_task(cfg: Dict):
            if cfg["type"] == "odds":
                return await self.fetch_odds(cfg.get("sport", "soccer"), cfg.get("region", "eu"))
            elif cfg["type"] == "events":
                return await self.fetch_events(cfg.get("sport", "football"), cfg.get("league_id"))
            return []

        coros = [_run_task(cfg) for cfg in tasks_config]
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        merged = []
        for res in results:
            if isinstance(res, list):
                merged.extend(res)
            elif isinstance(res, Exception):
                log.error("Batch collection error", error=str(res))
                
        log.info("Batch collection completed", total_items=len(merged))
        return merged
