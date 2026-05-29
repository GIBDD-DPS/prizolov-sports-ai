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
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from datetime import datetime
import re

log = structlog.get_logger()

class AggregatorCollector:
    """
    Асинхронный парсер спортивных агрегаторов.
    Источники: FlashScore, Livescore, OddsPortal.
    Извлекает: live-матчи, счёт, минуту, статус, базовые коэффициенты.
    Примечание: CSS-селекторы могут требовать адаптации при обновлении вёрстки сайтов.
    """

    SOURCES = {
        "flashscore": {"base": "https://www.flashscore.com", "live_path": "/live/"},
        "livescore": {"base": "https://www.livescore.com", "live_path": "/live/"},
        "oddsportal": {"base": "https://www.oddsportal.com", "live_path": "/live/"}
    }

    def __init__(
        self, 
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", 
        proxy: Optional[str] = None, 
        timeout: int = 30
    ):
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/"
        }
        self.proxy = proxy
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers, 
            timeout=self.timeout, 
            cookie_jar=aiohttp.CookieJar()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_live_matches(self, source: str = "flashscore", sport: str = "football") -> List[Dict]:
        """Парсинг live-матчей с выбранного агрегатора"""
        if source not in self.SOURCES:
            log.warning("Unsupported aggregator", source=source)
            return []

        base = self.SOURCES[source]["base"]
        path = self.SOURCES[source]["live_path"]
        url = f"{base}/{sport}{path}"

        try:
            async with self.session.get(url, proxy=self.proxy) as resp:
                if resp.status != 200:
                    log.warning(f"{source} fetch failed", status=resp.status, url=url)
                    return []
                html = await resp.text()
                return self._parse_html(source, html, sport)
        except Exception as e:
            log.error(f"{source} fetch error", error=str(e))
            return []

    def _parse_html(self, source: str, html: str, sport: str) -> List[Dict]:
        """Распарсить HTML в зависимости от источника"""
        soup = BeautifulSoup(html, "lxml")
        
        if source == "flashscore":
            return self._parse_flashscore(soup, sport)
        elif source == "livescore":
            return self._parse_livescore(soup, sport)
        elif source == "oddsportal":
            return self._parse_oddsportal(soup, sport)
        return []

    def _parse_flashscore(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        rows = soup.select("div.event__match, tr.table-main__event")
        events = []
        for row in rows:
            try:
                home_el = row.select_one(".event__participant--home, .table-main__participant--home")
                away_el = row.select_one(".event__participant--away, .table-main__participant--away")
                score_el = row.select_one(".event__scores, .table-main__score")
                time_el = row.select_one(".event__time, .table-main__time")

                if home_el and away_el:
                    minute = self._extract_minute(time_el.text.strip() if time_el else "")
                    events.append({
                        "match_id": f"{sport}_{row.get('id', row.get('data-match-id', '')).strip()}",
                        "sport_type": sport,
                        "home_team": home_el.text.strip(),
                        "away_team": away_el.text.strip(),
                        "score": score_el.text.strip() if score_el else None,
                        "current_minute": minute,
                        "status": "live" if minute and minute > 0 else "upcoming",
                        "source": "flashscore",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                log.debug("FlashScore row parse skipped", error=str(e))
        return events

    def _parse_livescore(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        rows = soup.select(".match-container, .js-match-event")
        events = []
        for row in rows:
            try:
                home = row.select_one(".home-team, .team-home").text.strip()
                away = row.select_one(".away-team, .team-away").text.strip()
                score = row.select_one(".score, .match-score").text.strip()
                time_str = row.select_one(".time, .match-time").text.strip()
                events.append({
                    "match_id": f"{sport}_{row.get('data-id', '')}",
                    "sport_type": sport,
                    "home_team": home,
                    "away_team": away,
                    "score": score,
                    "current_minute": self._extract_minute(time_str),
                    "status": "live",
                    "source": "livescore",
                    "fetched_at": datetime.utcnow().isoformat()
                })
            except Exception as e:
                log.debug("Livescore row parse skipped", error=str(e))
        return events

    def _parse_oddsportal(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        rows = soup.select("tr.deactivate, .deactivate")
        events = []
        for row in rows:
            try:
                cells = row.select("td")
                if len(cells) >= 4:
                    time_str = cells[0].text.strip()
                    home = cells[1].select_one("a").text.strip()
                    away = cells[2].select_one("a").text.strip()
                    odds_1 = self._safe_float(cells[3].select_one(".odds-nowrp").text.strip())
                    events.append({
                        "match_id": f"{sport}_{row.get('data-fixture-id', '')}",
                        "sport_type": sport,
                        "home_team": home,
                        "away_team": away,
                        "score": None,
                        "current_minute": self._extract_minute(time_str),
                        "status": "live" if self._extract_minute(time_str) else "upcoming",
                        "odds_basic": {"1": odds_1},
                        "source": "oddsportal",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                log.debug("OddsPortal row parse skipped", error=str(e))
        return events

    def _extract_minute(self, time_str: str) -> Optional[int]:
        """Извлечение минуты матча из строки типа '45'' или '2-й тайм 12:'"""
        match = re.search(r"(\d+)", time_str)
        return int(match.group(1)) if match else None

    def _safe_float(self, val: str) -> Optional[float]:
        """Безопасное преобразование строки в float"""
        try:
            return float(val.replace(",", "."))
        except (ValueError, AttributeError):
            return None
