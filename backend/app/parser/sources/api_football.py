# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""API-Football (api-football.com, прямая регистрация) — официальный REST API.

В отличие от forebet.py/predictz.py/betensured.py:
  - никакого regex по HTML и никаких синтетических коэффициентов;
  - доступ авторизован ключом (заголовок x-apisports-key), поэтому 403
    от анти-бот защиты в принципе не возникает — это не скрапинг;
  - если коэффициенты недоступны на твоём тарифе (бесплатный план часто
    отдаёт odds с задержкой или не по всем лигам) — событие всё равно
    сохраняется, просто с пустым списком markets, БЕЗ фейковых чисел.

ВАЖНО ПРО ЛИМИТЫ: бесплатный тариф — как правило 100 запросов/день.
Поэтому здесь ровно 2 запроса за один прогон парсера:
  1) GET /fixtures?date=YYYY-MM-DD — матчи на сегодня
  2) GET /odds?date=YYYY-MM-DD     — коэффициенты одним пакетом на дату
а не по одному /odds на каждый матч (это истощило бы лимит за один прогон
при PARSER_INTERVAL_MINUTES=30).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.parser.sources.base import BaseSourceParser

BASE_URL = "https://v3.football.api-sports.io"

MATCH_WINNER_BET_ID = 1
_VALUE_TO_SELECTION = {"Home": "1", "Draw": "X", "Away": "2"}


class ApiFootballParser(BaseSourceParser):
    source_id = "api_football"
    base_url = BASE_URL

    def _headers(self) -> dict[str, str]:
        return {"x-apisports-key": settings.api_football_key}

    async def fetch_football_events(self) -> list[dict[str, Any]]:
        if not settings.api_football_key:
            raise RuntimeError("API_FOOTBALL_KEY не задан в .env")

        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self._headers(), timeout=30.0
        ) as client:
            fixtures = await self._fetch_fixtures(client)
            if not fixtures:
                return []

            odds_by_fixture = await self._fetch_odds_bulk(client)

            events: list[dict[str, Any]] = []
            for fx in fixtures:
                fixture_id = fx.get("fixture", {}).get("id")
                events.append(
                    {
                        "source_id": self.source_id,
                        "home_team": fx.get("teams", {}).get("home", {}).get("name", "").strip(),
                        "away_team": fx.get("teams", {}).get("away", {}).get("name", "").strip(),
                        "league": fx.get("league", {}).get("name", "").strip(),
                        "kickoff": fx.get("fixture", {}).get("date"),
                        "markets": odds_by_fixture.get(fixture_id, []),
                    }
                )
            return events

    async def _fetch_fixtures(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        response = await client.get("/fixtures", params={"date": today})
        response.raise_for_status()
        data = response.json()

        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-Football вернул ошибку: {errors}")

        return data.get("response", [])

    async def _fetch_odds_bulk(self, client: httpx.AsyncClient) -> dict[int, list[dict[str, Any]]]:
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        response = await client.get("/odds", params={"date": today})

        if response.status_code == 403 or response.status_code == 499:
            return {}
        response.raise_for_status()

        data = response.json()
        if data.get("errors"):
            return {}

        result: dict[int, list[dict[str, Any]]] = {}

        for item in data.get("response", []):
            fixture_id = item.get("fixture", {}).get("id")
            bookmakers = item.get("bookmakers") or []
            if not fixture_id or not bookmakers:
                continue

            selections: list[dict[str, Any]] = []
            for bookmaker in bookmakers:
                match_winner_bet = next(
                    (b for b in bookmaker.get("bets", []) if b.get("id") == MATCH_WINNER_BET_ID),
                    None,
                )
                if not match_winner_bet:
                    continue
                for value in match_winner_bet.get("values", []):
                    selection = _VALUE_TO_SELECTION.get(value.get("value"))
                    odd_raw = value.get("odd")
                    if not selection or odd_raw is None:
                        continue
                    try:
                        selections.append({"selection": selection, "odds_value": float(odd_raw)})
                    except (TypeError, ValueError):
                        continue
                if selections:
                    break

            if selections:
                result[fixture_id] = [
                    {"market_type": "1X2", "line_value": None, "selections": selections}
                ]

        return result