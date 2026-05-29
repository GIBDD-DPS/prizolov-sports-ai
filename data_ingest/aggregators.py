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

class AggregatorsCollector:
    def __init__(self):
        self.the_odds_api_key = os.getenv("THE_ODDS_API_KEY")
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _odds_api_request(self, sport: str = "soccer") -> Optional[List[Dict]]:
        if not self.the_odds_api_key:
            logger.debug("THE_ODDS_API_KEY не задан")
            return None
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
        params = {
            "apiKey": self.the_odds_api_key,
            "regions": "eu,ru",
            "markets": "h2h,totals,spreads",
            "oddsFormat": "decimal"
        }
        session = await self._get_session()
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    logger.warning(f"The Odds API статус {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка запроса к The Odds API: {e}")
            return None

    async def fetch_odds(self, sport: str = "soccer") -> List[Dict[str, Any]]:
        raw = await self._odds_api_request(sport)
        if not raw:
            return []
        results = []
        for event in raw:
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") in ["h2h", "totals", "spreads"]:
                        for outcome in market.get("outcomes", []):
                            results.append({
                                "sport": sport,
                                "home": home_team,
                                "away": away_team,
                                "bookmaker": bookmaker.get("title"),
                                "market_type": market.get("key"),
                                "line": outcome.get("point", None),
                                "outcome": outcome.get("name"),
                                "price": outcome.get("price"),
                                "timestamp": event.get("commence_time")
                            })
        return results

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

async def fetch_aggregators() -> List[Dict]:
    collector = AggregatorsCollector()
    try:
        odds = await collector.fetch_odds("soccer")
        logger.info(f"Aggregators: получено {len(odds)} коэффициентов")
        return odds
    finally:
        await collector.close()
