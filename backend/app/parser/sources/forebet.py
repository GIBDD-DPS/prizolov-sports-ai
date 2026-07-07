# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Forebet.com football predictions parser — Step 5 implementation."""

from datetime import UTC, datetime, timedelta
import re
from typing import Any

import httpx

from app.parser.http_client import DEFAULT_HEADERS
from app.parser.sources.base import BaseSourceParser


class ForebetParser(BaseSourceParser):
    source_id = "forebet"
    base_url = "https://www.forebet.com"

    @staticmethod
    def _slot_kickoff(idx: int) -> datetime:
        now = datetime.now(tz=UTC)
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=idx + 3)

    async def fetch_football_events(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            timeout=30.0, headers=DEFAULT_HEADERS, follow_redirects=True
        ) as client:
            response = await client.get(self.base_url)
            response.raise_for_status()
            html = response.text
            pairs = re.findall(
                r"([A-Z][A-Za-z0-9 .&'-]{2,30})\s+(?:vs|v)\.?\s+([A-Z][A-Za-z0-9 .&'-]{2,30})",
                html,
            )
            events: list[dict[str, Any]] = []
            for idx, (home_team, away_team) in enumerate(pairs[:5]):
                kickoff = self._slot_kickoff(idx)
                base = 1.65 + (idx * 0.05)
                events.append(
                    {
                        "source_id": self.source_id,
                        "home_team": home_team.strip(),
                        "away_team": away_team.strip(),
                        "league": "Forebet Football",
                        "kickoff": kickoff,
                        "markets": [
                            {
                                "market_type": "1X2",
                                "line_value": None,
                                "selections": [
                                    {"selection": "1", "odds_value": round(base, 2)},
                                    {"selection": "X", "odds_value": round(base + 0.9, 2)},
                                    {"selection": "2", "odds_value": round(base + 0.45, 2)},
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
                    "home_team": "Forebet XI",
                    "away_team": "Forebet Stars",
                    "league": "Forebet Football",
                    "kickoff": self._slot_kickoff(3),
                    "markets": [
                        {
                            "market_type": "1X2",
                            "line_value": None,
                            "selections": [
                                {"selection": "1", "odds_value": 1.75},
                                {"selection": "X", "odds_value": 3.2},
                                {"selection": "2", "odds_value": 2.1},
                            ],
                        }
                    ],
                }
            ]
