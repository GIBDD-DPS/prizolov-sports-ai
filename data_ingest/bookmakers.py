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

class BookmakerCollector:
    """
    Асинхронный сборщик коэффициентов и линий букмекерских контор.
    Поддерживает базовый HTTP-парсинг 1xStavka, Fonbet.
    ⚠️ Примечание для продакшена: большинство БК используют Cloudflare/JS-рендеринг.
    Для стабильной работы рекомендуется подключать Playwright/Selenium или использовать
    официальные/партнёрские API букмекеров. Данный модуль служит архитектурным фундаментом.
    """

    BOOKMAKERS = {
        "1xstavka": {"base": "https://1xstavka.ru", "live_path": "/line/Football/Live/"},
        "fonbet": {"base": "https://fonbet.ru", "live_path": "/live/football"},
        "bet365": {"base": "https://www.bet365.com", "live_path": "/#/AC/B1/C1/"}
    }

    def __init__(
        self, 
        user_agent: str, 
        proxy: Optional[str] = None, 
        timeout: int = 30,
        request_delay: float = 1.0
    ):
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/"
        }
        self.proxy = proxy
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.request_delay = request_delay
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

    async def fetch_odds(self, bk_name: str, sport: str = "football") -> List[Dict]:
        """Загрузка страницы БК и извлечение базовых коэффициентов"""
        if bk_name not in self.BOOKMAKERS:
            log.warning("Unsupported bookmaker", bk=bk_name)
            return []

        url = f"{self.BOOKMAKERS[bk_name]['base']}{self.BOOKMAKERS[bk_name]['live_path']}"
        try:
            await asyncio.sleep(self.request_delay)  # Анти-спам задержка
            async with self.session.get(url, proxy=self.proxy) as resp:
                if resp.status != 200:
                    log.warning(f"{bk_name} fetch failed", status=resp.status, url=url)
                    return []
                html = await resp.text()
                return self._parse_odds(bk_name, html, sport)
        except Exception as e:
            log.error(f"{bk_name} fetch error", error=str(e))
            return []

    def _parse_odds(self, bk: str, html: str, sport: str) -> List[Dict]:
        """Диспетчер парсинга по конкретному букмекеру"""
        soup = BeautifulSoup(html, "lxml")
        
        if bk == "1xstavka":
            return self._parse_1xstavka(soup, sport)
        elif bk == "fonbet":
            return self._parse_fonbet(soup, sport)
        elif bk == "bet365":
            log.info("Bet365 detected. Skipping HTTP parse (requires headless browser)")
            return []
        return []

    def _parse_1xstavka(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        """Парсинг 1xStavka (базовая структура, селекторы требуют периодической актуализации)"""
        rows = soup.select("div.c-events__item, tr.event-row, .event-block")
        events = []
        for row in rows:
            try:
                home_el = row.select_one(".c-events__team--left, .team-name--home")
                away_el = row.select_one(".c-events__team--right, .team-name--away")
                
                odds_1 = self._safe_float(row.select_one(".coef-1, .odds-1")?.get_text(strip=True))
                odds_X = self._safe_float(row.select_one(".coef-X, .odds-X")?.get_text(strip=True))
                odds_2 = self._safe_float(row.select_one(".coef-2, .odds-2")?.get_text(strip=True))

                if home_el and away_el:
                    events.append({
                        "match_id": f"{sport}_{row.get('data-event-id', row.get('id', '')).strip()}",
                        "sport_type": sport,
                        "home_team": home_el.get_text(strip=True),
                        "away_team": away_el.get_text(strip=True),
                        "odds": {"1": odds_1, "X": odds_X, "2": odds_2},
                        "source": "1xstavka",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                log.debug("1xStavka row parse skipped", error=str(e))
        return events

    def _parse_fonbet(self, soup: BeautifulSoup, sport: str) -> List[Dict]:
        """Парсинг Fonbet (базовая структура)"""
        rows = soup.select(".live-event, .row-event, .match-card")
        events = []
        for row in rows:
            try:
                home_el = row.select_one(".team-home, .participant-home")
                away_el = row.select_one(".team-away, .participant-away")
                odds_container = row.select_one(".coefs, .odds-grid")
                
                odds = {}
                if odds_container:
                    coef_els = odds_container.select(".coef")
                    if len(coef_els) >= 3:
                        odds = {
                            "1": self._safe_float(coef_els[0].get_text(strip=True)),
                            "X": self._safe_float(coef_els[1].get_text(strip=True)),
                            "2": self._safe_float(coef_els[2].get_text(strip=True))
                        }

                if home_el and away_el:
                    events.append({
                        "match_id": f"{sport}_{row.get('data-match-id', row.get('id', '')).strip()}",
                        "sport_type": sport,
                        "home_team": home_el.get_text(strip=True),
                        "away_team": away_el.get_text(strip=True),
                        "odds": odds,
                        "source": "fonbet",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                log.debug("Fonbet row parse skipped", error=str(e))
        return events

    def _safe_float(self, val: Optional[str]) -> Optional[float]:
        """Безопасное преобразование коэффициента в float"""
        if not val:
            return None
        try:
            return float(val.replace(",", ".").strip())
        except (ValueError, AttributeError):
            return None

    async def collect_all_bk(self, bookmakers: List[str] = ["1xstavka", "fonbet"], sport: str = "football") -> List[Dict]:
        """Параллельный сбор коэффициентов со списка БК с учётом задержек"""
        tasks = [self.fetch_odds(bk, sport) for bk in bookmakers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        merged = []
        for res in results:
            if isinstance(res, list):
                merged.extend(res)
            elif isinstance(res, Exception):
                log.error("Bookmaker batch error", error=str(res))
                
        log.info("Bookmaker odds collection batch completed", total_events=len(merged))
        return merged
