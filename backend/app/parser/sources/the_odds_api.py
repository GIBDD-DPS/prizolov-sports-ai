# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""The Odds API (the-odds-api.com) — официальный REST API с реальными
коэффициентами букмекеров. Как и api_football.py: без regex по HTML,
без синтетических чисел, без анти-бот блокировок — доступ по apiKey.

ВАЖНО ПРО КВОТУ: бесплатный тариф — небольшая месячная квота кредитов.
Каждый вызов этого источника тратит реальные кредиты аккаунта. Не гоняй
это чаще, чем нужно, пока не свериться с остатком на
dashboard.the-odds-api.com.

ВАЖНО ПРО ОХВАТ: в отличие от Forebet/Predictz (весь футбол одним фидом),
здесь один запрос = одна лига (`ODDS_API_SPORT_KEY`, например "soccer_epl").
Полный список доступных лиг — GET /v4/sports с твоим ключом.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.parser.sources.base import BaseSourceParser
from app.parser.validation import is_valid_odds

BASE_URL = "https://api.the-odds-api.com"


class TheOddsApiParser(BaseSourceParser):
    source_id = "the_odds_api"
    base_url = BASE_URL

    async def fetch_football_events(self) -> list[dict[str, Any]]:
        if not settings.odds_api_key:
            raise RuntimeError("ODDS_API_KEY не задан в .env")

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get(
                f"/v4/sports/{settings.odds_api_sport_key}/odds",
                params={
                    "apiKey": settings.odds_api_key,
                    "regions": settings.odds_api_region,
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                },
            )
            response.raise_for_status()
            data = response.json()

            # В отличие от API-Football, при реальных ошибках (неверный ключ,
            # неизвестная лига, исчерпанная квота) The Odds API отдаёт
            # соответствующий HTTP-статус (401/404/429), так что raise_for_status()
            # выше их уже ловит. Доп. проверка — на случай нестандартного тела.
            if not isinstance(data, list):
                raise RuntimeError(f"Неожиданный ответ The Odds API: {data}")

            events: list[dict[str, Any]] = []
            for item in data:
                home_team = str(item.get("home_team", "")).strip()
                away_team = str(item.get("away_team", "")).strip()
                if not home_team or not away_team:
                    continue

                markets = self._extract_h2h_market(item, home_team, away_team)
                events.append(
                    {
                        "source_id": self.source_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "league": str(item.get("sport_title", "")).strip(),
                        "kickoff": item.get("commence_time"),
                        "markets": markets,
                    }
                )
            return events

    @staticmethod
    def _extract_h2h_market(
        item: dict[str, Any], home_team: str, away_team: str
    ) -> list[dict[str, Any]]:
        bookmakers = item.get("bookmakers") or []
        for bookmaker in bookmakers:
            h2h_market = next(
                (m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None
            )
            if not h2h_market:
                continue

            selections: list[dict[str, Any]] = []
            for outcome in h2h_market.get("outcomes", []):
                name = outcome.get("name")
                price = outcome.get("price")
                if price is None or not is_valid_odds(price):
                    continue
                if name == home_team:
                    selection = "1"
                elif name == away_team:
                    selection = "2"
                elif name == "Draw":
                    selection = "X"
                else:
                    continue
                selections.append({"selection": selection, "odds_value": float(price)})

            if selections:
                return [{"market_type": "1X2", "line_value": None, "selections": selections}]

        return []
