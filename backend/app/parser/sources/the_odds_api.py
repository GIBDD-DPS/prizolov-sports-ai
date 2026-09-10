# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""The Odds API (the-odds-api.com) — официальный REST API с реальными
коэффициентами букмекеров. Как и api_football.py: без regex по HTML,
без синтетических чисел, без анти-бот блокировок — доступ по apiKey.

КОНСЕНСУС ПО БУКМЕКЕРАМ: ответ обычно содержит 5-15 букмекеров на один матч.
Вместо использования первого попавшегося (что делало прогноз зависимым от
случайного порядка в JSON-ответе), здесь по каждому букмекеру убирается
маржа (де-виг — implied probability нормализуется так, чтобы 1+X+2 = 100%),
а затем результаты усредняются по всем букмекерам. Это даёт более
устойчивую и представительную оценку рынка, чем мнение одного букмекера.

ВАЖНО ПРО КВОТУ: бесплатный тариф — небольшая месячная квота кредитов.
Каждый вызов этого источника тратит реальные кредиты аккаунта. Не гоняй
это чаще, чем нужно, пока не свериться с остатком на
dashboard.the-odds-api.com.

ВАЖНО ПРО ОХВАТ: в отличие от Forebet/Predictz (весь футбол одним фидом),
здесь один запрос = одна лига (`ODDS_API_SPORT_KEY`, например "soccer_epl").
Полный список доступных лиг — GET /v4/sports с твоим ключом.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.parser.sources.base import BaseSourceParser
from app.parser.validation import is_valid_odds

BASE_URL = "https://api.the-odds-api.com"

logger = logging.getLogger("prizolov.parser.the_odds_api")


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

            if not isinstance(data, list):
                raise RuntimeError(f"Неожиданный ответ The Odds API: {data}")

            events: list[dict[str, Any]] = []
            for item in data:
                home_team = str(item.get("home_team", "")).strip()
                away_team = str(item.get("away_team", "")).strip()
                if not home_team or not away_team:
                    continue

                markets = self._extract_consensus_market(item, home_team, away_team)
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
    def _devig_bookmaker(
        bookmaker: dict[str, Any], home_team: str, away_team: str
    ) -> dict[str, float] | None:
        """Возвращает {"1": p, "X": p, "2": p} для одного букмекера, без маржи."""
        h2h_market = next(
            (m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None
        )
        if not h2h_market:
            return None

        raw_probs: dict[str, float] = {}
        for outcome in h2h_market.get("outcomes", []):
            name = outcome.get("name")
            price = outcome.get("price")
            if not is_valid_odds(price):
                continue
            if name == home_team:
                selection = "1"
            elif name == away_team:
                selection = "2"
            elif name == "Draw":
                selection = "X"
            else:
                continue
            raw_probs[selection] = 1.0 / float(price)

        if len(raw_probs) < 2:  # меньше двух исходов — от букмекера толку нет
            return None

        total = sum(raw_probs.values())
        if total <= 0:
            return None

        # Де-виг: нормализуем так, чтобы сумма стала ровно 1.0 (убираем маржу букмекера)
        return {selection: prob / total for selection, prob in raw_probs.items()}

    def _extract_consensus_market(
        self, item: dict[str, Any], home_team: str, away_team: str
    ) -> list[dict[str, Any]]:
        bookmakers = item.get("bookmakers") or []
        per_bookmaker_probs: list[dict[str, float]] = []

        for bookmaker in bookmakers:
            devigged = self._devig_bookmaker(bookmaker, home_team, away_team)
            if devigged:
                per_bookmaker_probs.append(devigged)

        if not per_bookmaker_probs:
            return []

        logger.debug(
            "%s vs %s: consensus из %d букмекер(ов)",
            home_team, away_team, len(per_bookmaker_probs),
        )

        consensus: dict[str, float] = {}
        for selection in ("1", "X", "2"):
            values = [p[selection] for p in per_bookmaker_probs if selection in p]
            if values:
                consensus[selection] = sum(values) / len(values)

        selections: list[dict[str, Any]] = []
        for selection, prob in consensus.items():
            if prob <= 0:
                continue
            # Обратно в псевдо-коэффициент — так downstream (Odds.implied_prob,
            # predictor.py) продолжают работать без изменений: implied_prob
            # пересчитывается как 1/odds_value и снова даст ровно этот prob.
            selections.append({"selection": selection, "odds_value": round(1.0 / prob, 4)})

        if not selections:
            return []

        return [{"market_type": "1X2", "line_value": None, "selections": selections}]
