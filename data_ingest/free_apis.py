# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import os
import aiohttp
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class FreeAPIsCollector:
    def __init__(self):
        self.api_football_key = os.getenv("API_FOOTBALL_KEY")
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _api_football_request(self, endpoint: str, params: Dict) -> Optional[List[Dict]]:
        if not self.api_football_key:
            logger.debug("API_FOOTBALL_KEY не задан")
            return None
        url = f"https://api-football-v1.p.rapidapi.com/v3/{endpoint}"
        headers = {
            "X-RapidAPI-Key": self.api_football_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        session = await self._get_session()
        try:
            async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", [])
                else:
                    logger.warning(f"API-Football {endpoint} статус {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка запроса к API-Football: {e}")
            return None

    async def fetch_live_scores(self) -> List[Dict[str, Any]]:
        params = {"live": "all", "timezone": "Europe/Moscow"}
        data = await self._api_football_request("fixtures", params)
        if not data:
            return []
        results = []
        for f in data:
            results.append({
                "league": f["league"]["name"],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "status": f["fixture"]["status"]["short"],
                "timestamp": f["fixture"]["timestamp"],
                "score_home": f["goals"]["home"],
                "score_away": f["goals"]["away"],
            })
        return results

    async def fetch_upcoming_fixtures(self, days: int = 3) -> List[Dict]:
        from datetime import datetime, timedelta
        today = datetime.now().date()
        end_date = today + timedelta(days=days)
        params = {
            "date": f"{today.isoformat()}-{end_date.isoformat()}",
            "timezone": "Europe/Moscow"
        }
        data = await self._api_football_request("fixtures", params)
        if not data:
            return []
        results = []
        for f in data:
            results.append({
                "league": f["league"]["name"],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "date": f["fixture"]["date"],
                "timestamp": f["fixture"]["timestamp"],
            })
        return results

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

async def fetch_free_apis() -> Dict[str, List]:
    collector = FreeAPIsCollector()
    try:
        live = await collector.fetch_live_scores()
        upcoming = await collector.fetch_upcoming_fixtures()
        logger.info(f"FreeAPIs: live={len(live)}, upcoming={len(upcoming)}")
        return {"live": live, "upcoming": upcoming}
    finally:
        await collector.close()
