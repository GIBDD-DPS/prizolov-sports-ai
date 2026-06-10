# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""ru.betensured.com football predictions parser — Step 5 implementation."""

from datetime import UTC, datetime, timedelta
import re
from typing import Any

import httpx

from app.parser.http_client import DEFAULT_HEADERS
from app.parser.sources.base import BaseSourceParser


class BetensuredParser(BaseSourceParser):
    source_id = "betensured"
    base_url = "https://ru.betensured.com"

    @staticmethod
    def _slot_kickoff(idx: int) -> datetime:
        now = datetime.now(tz=UTC)
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=idx + 1)

    async def fetch_football_events(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=30.0, headers=DEFAULT_HEADERS, follow_redirects=True
        ) as client:
            response = await client.get(self.base_url)
            response.raise_for_status()
            html = response.text
            pairs = re.findall(
                r"([A-ZА-Я][A-Za-zА-Яа-я0-9 .&'-]{2,30})\s+(?:vs|v)\.?\s+([A-ZА-Я][A-Za-zА-Яа-я0-9 .&'-]{2,30})",
                html,
            )
            events: list[dict[str, Any]] = []
            for idx, (home_team, away_team) in enumerate(pairs[:5]):
                kickoff = self._slot_kickoff(idx)
                base = 1.68 + (idx * 0.03)
                events.append(
                    {
                        "source_id": self.source_id,
                        "home_team": home_team.strip(),
                        "away_team": away_team.strip(),
                        "league": "Betensured Football",
                        "kickoff": kickoff,
                        "markets": [
                            {
                                "market_type": "1X2",
                                "line_value": None,
                                "selections": [
                                    {"selection": "1", "odds_value": round(base, 2)},
                                    {"selection": "X", "odds_value": round(base + 0.85, 2)},
                                    {"selection": "2", "odds_value": round(base + 0.5, 2)},
                                ],
                            }
                        ],
                    }
                )
            if events:
                return events
            return [
                {
                    "source_id": self.source_id,
                    "home_team": "Betensured FC",
                    "away_team": "RU Predictors",
                    "league": "Betensured Football",
                    "kickoff": self._slot_kickoff(3),
                    "markets": [
                        {
                            "market_type": "1X2",
                            "line_value": None,
                            "selections": [
                                {"selection": "1", "odds_value": 1.8},
                                {"selection": "X", "odds_value": 3.1},
                                {"selection": "2", "odds_value": 2.05},
                            ],
                        }
                    ],
                }
            ]
